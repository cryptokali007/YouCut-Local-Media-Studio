[CmdletBinding()]
param([switch]$Offline, [switch]$CoreOnly, [switch]$NoPause)
# Reinstall packages and verify/download managed assets. Never delete user files.
$setup = Join-Path $PSScriptRoot '..\setup\setup.ps1'
& $setup -Repair -Offline:$Offline -CoreOnly:$CoreOnly -NoPause:$NoPause
exit $LASTEXITCODE
