[CmdletBinding()]
param([switch]$CoreOnly, [switch]$Offline, [switch]$NoPause, [switch]$Repair)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$appRoot = Join-Path $projectRoot 'app'
$cacheRoot = Join-Path $appRoot 'cache\downloads'
$runtimeRoot = Join-Path $appRoot 'runtime'
$pythonExe = Join-Path $runtimeRoot 'python.exe'

function Get-Sha256([string]$path) {
    $stream = [IO.File]::OpenRead($path)
    $algorithm = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($algorithm.ComputeHash($stream))).Replace('-', '').ToLowerInvariant() }
    finally { $algorithm.Dispose(); $stream.Dispose() }
}

function Expand-Runtime([string]$archivePath, [string]$destination) {
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $destinationPrefix = [IO.Path]::GetFullPath($destination).TrimEnd('\') + '\'
    $archive = [IO.Compression.ZipFile]::OpenRead($archivePath)
    try {
        foreach ($entry in $archive.Entries) {
            $entryPath = [IO.Path]::GetFullPath((Join-Path $destination $entry.FullName))
            if (-not $entryPath.StartsWith($destinationPrefix, [StringComparison]::OrdinalIgnoreCase)) { throw 'Unsafe archive path.' }
            if ($entry.FullName.EndsWith('/')) { [IO.Directory]::CreateDirectory($entryPath) | Out-Null; continue }
            [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($entryPath)) | Out-Null
            [IO.Compression.ZipFileExtensions]::ExtractToFile($entry, $entryPath, $true)
        }
    } finally { $archive.Dispose() }
}

function Get-VerifiedDownload($asset, [string]$destination) {
    if (Test-Path -LiteralPath $destination) {
        if ((Get-Sha256 $destination) -eq $asset.sha256) { return }
        if ($Offline) { throw "Cached file is damaged: $destination" }
    }
    if ($Offline) { throw "Offline setup needs this cached file: $destination. Run Install.bat while connected first." }
    $partial = $destination + '.partial'
    for ($attempt = 1; $attempt -le 3; $attempt++) {
        try {
            Write-Host "Downloading $($asset.filename) (attempt $attempt/3)..."
            $client = New-Object Net.WebClient
            try { $client.DownloadFile($asset.url, $partial) } finally { $client.Dispose() }
            if ((Get-Sha256 $partial) -ne $asset.sha256) { throw 'SHA-256 verification failed.' }
            Move-Item -LiteralPath $partial -Destination $destination -Force
            return
        } catch {
            if (Test-Path -LiteralPath $partial) { Remove-Item -LiteralPath $partial -Force }
            if ($attempt -eq 3) { throw }
            Write-Host $_.Exception.Message
            Start-Sleep -Seconds $attempt
        }
    }
}

try {
    if (-not [Environment]::Is64BitOperatingSystem -or $env:PROCESSOR_ARCHITECTURE -eq 'ARM64') { throw 'This release supports Windows x64. Windows ARM64 and 32-bit systems are not supported.' }
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    New-Item -ItemType Directory -Path $cacheRoot,$runtimeRoot,(Join-Path $appRoot 'logs') -Force | Out-Null
    $assets = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'assets.json') -Raw | ConvertFrom-Json
    Write-Host "`nYouCutOwn Studio - automatic local setup"
    Write-Host 'Your media. Your machine. No subscription.'
    Write-Host "[1/5] Private Python $($assets.python.version)"
    if (-not (Test-Path -LiteralPath $pythonExe)) {
        $archive = Join-Path $cacheRoot $assets.python.filename
        Get-VerifiedDownload $assets.python $archive
        Expand-Runtime $archive $runtimeRoot
    }
    $version = & $pythonExe -c 'import platform; print(platform.python_version())'
    if ($LASTEXITCODE -ne 0 -or $version.Trim() -ne $assets.python.version) { throw "Private Python is incomplete or has the wrong version. Remove only app/runtime and rerun Install.bat. Expected $($assets.python.version)." }
    $pth = Join-Path $runtimeRoot 'python313._pth'
    "python313.zip`n.`nLib/site-packages`n..`n" | Set-Content -LiteralPath $pth -Encoding ASCII
    $sitePackages = Join-Path $runtimeRoot 'Lib\site-packages'
    New-Item -ItemType Directory -Path $sitePackages -Force | Out-Null
    $missingRuntimeDlls = @('vcruntime140.dll','vcruntime140_1.dll','msvcp140.dll') | Where-Object { -not [IO.File]::Exists((Join-Path ([Environment]::GetFolderPath('System')) $_)) }
    if (@($missingRuntimeDlls).Count -gt 0) {
        Write-Host 'Microsoft Visual C++ x64 runtime is needed. Windows may ask for permission to install it.'
        $redistributable = Join-Path $cacheRoot $assets.vc_runtime.filename
        Get-VerifiedDownload $assets.vc_runtime $redistributable
        $runtimeInstaller = Start-Process -FilePath $redistributable -ArgumentList '/install','/passive','/norestart' -Verb RunAs -Wait -PassThru -WindowStyle Hidden
        if ($runtimeInstaller.ExitCode -notin @(0,1638,3010)) { throw "Microsoft runtime installation failed: $($runtimeInstaller.ExitCode)." }
    }
    Write-Host '[2/5] Pinned Python package installer'
    $pipWheel = Join-Path $cacheRoot $assets.pip.filename
    Get-VerifiedDownload $assets.pip $pipWheel
    & $pythonExe -c 'import sys,zipfile; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])' $pipWheel $sitePackages
    if ($LASTEXITCODE -ne 0) { throw 'Could not prepare pip.' }
    $setupArgs = @((Join-Path $PSScriptRoot 'setup.py'))
    if ($CoreOnly) { $setupArgs += '--core-only' }
    if ($Offline) { $setupArgs += '--offline' }
    if ($Repair) { $setupArgs += '--repair' }
    & $pythonExe @setupArgs
    if ($LASTEXITCODE -ne 0) { throw "Setup failed with exit code $LASTEXITCODE. See app/logs/setup.log." }
    Write-Host "`nReady. Double-click windows.bat to open YouCutOwn Studio." -ForegroundColor Green
    if (-not $NoPause) { Read-Host 'Press Enter to close' | Out-Null }
    exit 0
} catch {
    Write-Host "`nSETUP FAILED: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host 'Your source media, saved models and outputs have not been removed.'
    if (-not $NoPause) { Read-Host 'Press Enter to close' | Out-Null }
    exit 1
}
