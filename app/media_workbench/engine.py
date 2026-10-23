"""FFmpeg jobs. No shell commands, network access, or source-file mutation."""
from pathlib import Path
import json
import math
import os
import shutil
import subprocess
import threading
import time
import uuid

from .captions import make_ass, parse_srt, to_srt

ROOT = Path(__file__).resolve().parents[1]
NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)


class Cancelled(Exception):
    pass


def binaries():
    ff = ROOT / 'bin' / 'ffmpeg.exe'
    fp = ROOT / 'bin' / 'ffprobe.exe'
    if not ff.exists() or not fp.exists():
        raise RuntimeError('FFmpeg files are missing. Close the app and run Install.bat in the project folder.')
    return str(ff), str(fp)


def probe(path):
    _, fp = binaries()
    proc = subprocess.run([fp, '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(path)],
                          capture_output=True, encoding='utf-8', errors='replace', creationflags=NO_WINDOW, timeout=30)
    if proc.returncode:
        raise ValueError(f'Cannot read {Path(path).name}: {proc.stderr[-500:]}')
    data = json.loads(proc.stdout)
    streams = data.get('streams', [])
    video = next((s for s in streams if s['codec_type'] == 'video' and not s.get('disposition', {}).get('attached_pic')), None)
    audio = next((s for s in streams if s['codec_type'] == 'audio'), None)
    duration = float(data.get('format', {}).get('duration') or (video or audio or {}).get('duration') or 0)
    suffix = Path(path).suffix.lower()
    image = suffix in {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tif', '.tiff', '.gif', '.avif', '.heic', '.ico', '.jxl'} and not audio
    kind = 'image' if image else 'video' if video else 'audio' if audio else None
    if not kind:
        raise ValueError(f'No supported image, video or audio stream in {Path(path).name}.')
    return dict(path=str(Path(path).resolve()), kind=kind, duration=duration, audio=bool(audio),
                width=int((video or {}).get('width', 0)), height=int((video or {}).get('height', 0)))


def tempo(speed):
    factors = []
    while speed > 2.000001:
        factors.append(2.0)
        speed /= 2
    while speed < 0.499999:
        factors.append(0.5)
        speed /= 0.5
    factors.append(speed)
    return ','.join(f'atempo={x:.9g}' for x in factors)


def dimensions(preset, media):
    sizes = {'1080p': (1920, 1080), '720p': (1280, 720), 'Vertical': (1080, 1920), 'Square': (1080, 1080)}
    if preset in sizes:
        return sizes[preset]
    w, h = media.get('width', 1280) or 1280, media.get('height', 720) or 720
    return max(2, w // 2 * 2), max(2, h // 2 * 2)


def video_filter(w, h, fit='Fit'):
    if fit == 'Fill / crop':
        scale = f'scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}'
    else:
        scale = f'scale={w}:{h}:force_original_aspect_ratio=decrease:force_divisible_by=2,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black'
    return f'{scale},setsar=1,fps=30,format=yuv420p,settb=AVTB'


class Job:
    def __init__(self, spec, progress=None):
        self.spec = spec
        self.progress = progress or (lambda message, percent: None)
        self.cancelled = threading.Event()
        self.process = None
        self.id = time.strftime('%Y%m%d-%H%M%S-') + uuid.uuid4().hex[:6]
        self.work = ROOT / 'work' / self.id
        self.work.mkdir(parents=True)
        (self.work / 'request.json').write_text(json.dumps(spec, indent=2, ensure_ascii=False), encoding='utf-8')
        self.step = 0
        self.steps = 1

    def cancel(self):
        self.cancelled.set()
        process = self.process
        if process and process.poll() is None:
            process.terminate()

    def check(self):
        if self.cancelled.is_set():
            raise Cancelled('Operation cancelled. Original media has not been changed.')

    def ffmpeg(self, args, duration, label):
        self.check()
        ff, _ = binaries()
        log = self.work / f'ffmpeg-{self.step:02}.log'
        command = [ff, '-hide_banner', '-y', '-nostdin', '-threads', '4', '-filter_complex_threads', '1',
                   '-filter_threads', '1', '-progress', 'pipe:1', '-nostats'] + list(map(str, args))
        with log.open('w', encoding='utf-8') as handle:
            handle.write(json.dumps(command, ensure_ascii=False) + '\n')
            handle.flush()
            self.process = subprocess.Popen(command, cwd=self.work, stdout=subprocess.PIPE, stderr=handle,
                                            encoding='utf-8', errors='replace', creationflags=NO_WINDOW)
            for line in self.process.stdout:
                if line.startswith('out_time_us='):
                    try:
                        fraction = min(.99, max(0, float(line.split('=', 1)[1]) / 1e6 / max(duration, .01)))
                        self.progress(label, min(99, int(100 * (self.step + fraction) / self.steps)))
                    except ValueError:
                        pass
                if self.cancelled.is_set():
                    self.process.terminate()
            rc = self.process.wait()
            self.process = None
        self.check()
        if rc:
            tail = '\n'.join(log.read_text(encoding='utf-8', errors='replace').splitlines()[-15:])
            raise RuntimeError(f'{label} failed.\n{tail}\n\nFull log: {log}')
        self.step += 1
        self.progress(label, min(99, int(100 * self.step / self.steps)))

    def encoding(self, intermediate=False):
        if self.spec.get('encoder') == 'NVIDIA' and not intermediate:
            return ['-c:v', 'h264_nvenc', '-preset', 'p4', '-cq', '21', '-b:v', '0']
        return ['-c:v', 'libx264', '-preset', 'veryfast' if intermediate else 'medium', '-crf', '18' if intermediate else '20']

    def export(self):
        operation = self.spec['operation']
        output_dir = Path(self.spec.get('output_dir') or ROOT / 'outputs')
        output_dir.mkdir(parents=True, exist_ok=True)
        extension = '.srt' if operation == 'transcribe' else '.wav' if operation in {'voice', 'extract_audio', 'join_audio', 'normalize_audio'} else '.png' if operation in {'image', 'frame'} else '.mp4'
        if operation == 'image':
            formats = {'PNG': '.png', 'JPEG': '.jpg', 'WebP': '.webp'}
            image_format = self.spec.get('image_format', 'PNG')
            if image_format not in formats:
                raise ValueError('Choose PNG, high-quality JPEG, or lossless WebP.')
            extension = formats[image_format]
        output = output_dir / (operation + '-' + self.id + extension)
        self.output = output
        if shutil.disk_usage(output_dir).free < 250 * 1024 * 1024:
            raise ValueError('Less than 250 MB is free in the output location. Free some space before exporting.')
        try:
            if operation == 'transcribe':
                return self.transcribe(output)
            if operation == 'voice':
                return self.voice(output)
            if operation in {'image', 'frame', 'extract_audio', 'join_audio', 'normalize_audio'}:
                return self.utility(output)
            videos = self.spec.get('videos', [])
            if operation != 'slideshow' and not videos:
                raise ValueError('Add a video to the Videos bucket first.')
            if operation in {'join', 'slideshow'}:
                base = self.assemble(videos, operation == 'slideshow')
            else:
                base = videos[0]
            info = probe(base)
            if operation == 'music':
                audio = self.spec.get('audio', [])
                if not audio:
                    raise ValueError('Add music to the Audio bucket first.')
                target = probe(audio[0])['duration'] if self.spec.get('loop') else info['duration']
                self.render(base, output, 0, target, 1, music=audio[0], loop=self.spec.get('loop', False))
            else:
                start = float(self.spec.get('start', 0)) if operation == 'edit' else 0
                end = float(self.spec.get('end', 0)) if operation == 'edit' else 0
                speed = float(self.spec.get('speed', 1)) if operation == 'edit' else 1
                if not math.isfinite(speed) or not .0625 <= speed <= 4096:
                    raise ValueError('Speed must be between 0.0625x and 4096x.')
                end = min(end or info['duration'], info['duration'])
                if start >= end:
                    raise ValueError('The trim end must come after the start and inside the video.')
                target = (end - start) / speed
                if target < 1 / 30:
                    raise ValueError('That selection would be shorter than one output frame. Select a longer range or lower speed.')
                self.render(base, output, start, target, speed)
            result = probe(output)
            if result['duration'] <= 0:
                raise RuntimeError('Output verification found an empty file.')
            self.progress('Finished', 100)
            return dict(path=str(output), media=result)
        finally:
            # Only temporary files created by this job; keep small logs/request for diagnosis.
            for p in self.work.iterdir():
                if p.suffix.lower() in {'.mp4', '.wav', '.png', '.ass', '.txt'}:
                    p.unlink(missing_ok=True)

    def render(self, source, output, start, duration, speed, music=None, loop=False):
        info = probe(source)
        w, h = dimensions(self.spec.get('size', 'Original'), info)
        args = []
        if loop:
            args += ['-stream_loop', '-1']
        if start:
            args += ['-ss', start]
        args += ['-i', source]
        inputs = 1
        if music:
            args += ['-i', music]
            music_index, inputs = inputs, inputs + 1
        watermark = self.spec.get('watermark')
        if watermark:
            args += ['-i', watermark]
            wm_index = inputs
        vf = f'[0:v]setpts=(PTS-STARTPTS)/{speed:.9g},' + video_filter(w, h, self.spec.get('fit', 'Fit'))
        if self.spec.get('subtitles'):
            segments = parse_srt(self.spec['subtitles'])
            ass = make_ass(segments, w, h, self.spec.get('caption_style', 'Highlight'),
                           self.spec.get('font_size', 48), self.spec.get('caption_position', 'Bottom'), self.spec.get('word_segments'))
            (self.work / 'captions.ass').write_text(ass, encoding='utf-8-sig')
            vf += ',ass=filename=captions.ass'
        vf += '[vbase]'
        graph = [vf]
        video_label = '[vbase]'
        if watermark:
            logo_width = max(16, round(w * float(self.spec.get('watermark_size', .14))))
            logo_height = max(16, round(h * .14))
            opacity = float(self.spec.get('watermark_opacity', .8))
            corner = self.spec.get('corner', 'Bottom right')
            x = '20' if 'left' in corner else 'W-w-20'
            y = '20' if 'Top' in corner else 'H-h-20'
            if self.spec.get('subtitles'):
                caption_position = self.spec.get('caption_position','Bottom')
                if caption_position == 'Bottom' and 'Bottom' in corner:y='H-h-H*0.20'
                if caption_position == 'Top' and 'Top' in corner:y='H*0.24'
            graph += [f'[{wm_index}:v]scale={logo_width}:{logo_height}:force_original_aspect_ratio=decrease,format=rgba,colorchannelmixer=aa={opacity}[logo]',
                      f'[vbase][logo]overlay={x}:{y}:eof_action=repeat[vout]']
            video_label = '[vout]'
        audio_label = None
        keep_audio = self.spec.get('keep_audio', True)
        if music:
            graph += [f'[{music_index}:a]aresample=48000,aformat=channel_layouts=stereo,asetpts=PTS-STARTPTS,volume={self.spec.get("music_volume", 1)},apad,atrim=duration={duration}[music]']
            audio_label = '[music]'
            if self.spec.get('mix') and info['audio']:
                graph += [f'[0:a]aresample=48000,aformat=channel_layouts=stereo,asetpts=PTS-STARTPTS,volume={self.spec.get("original_volume", .4)},apad,atrim=duration={duration}[original]',
                          '[original][music]amix=inputs=2:duration=longest:normalize=0,alimiter=limit=0.95[aout]']
                audio_label = '[aout]'
        elif info['audio'] and keep_audio:
            graph += [f'[0:a]asetpts=PTS-STARTPTS,{tempo(speed)},aresample=48000,apad,atrim=duration={duration}[aout]']
            audio_label = '[aout]'
        args += ['-filter_complex', ';'.join(graph), '-map', video_label]
        args += ['-map', audio_label, '-c:a', 'aac', '-b:a', '192k'] if audio_label else ['-an']
        partial = output.with_name(output.stem + '.partial.mp4')
        try:
            args += self.encoding() + ['-t', duration, '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(partial)]
            self.steps = max(self.steps, self.step + 1)
            self.ffmpeg(args, duration, 'Exporting video')
            self.check()
            os.replace(partial, output)
        finally:
            partial.unlink(missing_ok=True)

    def assemble(self, files, images=False):
        files = self.spec.get('images', []) if images else files
        if not files:
            raise ValueError('Add images first.' if images else 'Add videos first.')
        first = probe(files[0])
        w, h = dimensions(self.spec.get('size', '1080p'), first)
        transition = self.spec.get('transition', 'none')
        self.steps = len(files) + (len(files) - 1 if transition != 'none' else 1) + 1
        parts, durations = [], []
        for i, path in enumerate(files):
            info = probe(path)
            length = float(self.spec.get('slide_duration', 4)) if images else info['duration']
            if length <= .1:
                raise ValueError(f'{Path(path).name} is too short to join.')
            length = max(1, round(length * 30)) / 30
            out = self.work / f'part-{i:04}.mp4'
            args = (['-loop', '1'] if images else []) + ['-i', path]
            if not info['audio'] or images:
                args += ['-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo']
            audio_index = '0:a' if info['audio'] and not images else '1:a'
            args += ['-filter_complex', f'[0:v]setpts=PTS-STARTPTS,{video_filter(w,h,self.spec.get("fit","Fit"))},tpad=stop_mode=clone:stop_duration=1[v];[{audio_index}]aresample=48000,aformat=channel_layouts=stereo,asetpts=PTS-STARTPTS,apad,atrim=duration={length}[a]',
                     '-map', '[v]', '-map', '[a]']
            args += self.encoding(True) + ['-c:a', 'aac', '-b:a', '192k', '-t', length, out]
            self.ffmpeg(args, length, f'Preparing {i+1} of {len(files)}')
            parts.append(out)
            durations.append(length)
        if len(parts) == 1:
            return str(parts[0])
        if transition == 'none':
            (self.work / 'concat.txt').write_text(''.join(f"file '{p.name}'\n" for p in parts), encoding='utf-8')
            out = self.work / 'joined.mp4'
            self.ffmpeg(['-f','concat','-safe','0','-i','concat.txt','-c','copy',out],sum(durations),'Joining clips')
            return str(out)
        overlap = float(self.spec.get('transition_duration', .5))
        if overlap <= 0 or overlap >= min(durations) / 2:
            raise ValueError(f'Transition must be shorter than half of your shortest clip ({min(durations):.2f}s).')
        current, total = parts[0], durations[0]
        for i in range(1, len(parts)):
            out = self.work / f'merged-{i:04}.mp4'
            graph = (f'[0:v]settb=AVTB,setpts=PTS-STARTPTS[a];[1:v]settb=AVTB,setpts=PTS-STARTPTS[b];'
                     f'[a][b]xfade=transition={transition}:duration={overlap}:offset={total-overlap}[v];'
                     f'[0:a][1:a]acrossfade=d={overlap}[audio]')
            total += durations[i] - overlap
            args = ['-i',current,'-i',parts[i],'-filter_complex',graph,'-map','[v]','-map','[audio]']
            self.ffmpeg(args+self.encoding(True)+['-c:a','aac','-t',total,out],total,f'Adding transition {i} of {len(parts)-1}')
            if current.name.startswith('merged-'):
                current.unlink(missing_ok=True)
            current = out
        return str(current)

    def transcribe(self, output):
        from faster_whisper import WhisperModel
        sources = self.spec.get('videos') or self.spec.get('audio')
        if not sources:
            raise ValueError('Select a video or audio file to transcribe.')
        path = sources[0]
        model_name = self.spec.get('model', 'base.en')
        model_path = ROOT / 'models' / ('whisper-' + model_name)
        if not (model_path / 'model.bin').exists():
            raise ValueError(f'The offline {model_name} model is not installed. Close the app and run Install.bat without -CoreOnly to download the speech assets.')
        self.progress('Loading offline speech model (CPU)', 1)
        model = WhisperModel(str(model_path), device='cpu', compute_type='int8', cpu_threads=4, local_files_only=True)
        duration = probe(path)['duration']
        iterator, info = model.transcribe(path, language='en' if model_name.endswith('.en') else None,
                                         word_timestamps=True, vad_filter=True, beam_size=3)
        segments = []
        for segment in iterator:
            self.check()
            segments.append(dict(start=segment.start,end=segment.end,text=segment.text.strip(),
                                 words=[dict(start=w.start,end=w.end,word=w.word) for w in (segment.words or [])]))
            self.progress('Transcribing locally', min(99, int(100*segment.end/max(.1,duration))))
        if not segments:
            raise ValueError('No speech was found. Try the multilingual model or a different audio track.')
        self.check()
        output.write_text(to_srt(segments), encoding='utf-8')
        output.with_suffix('.json').write_text(json.dumps(segments,ensure_ascii=False,indent=2),encoding='utf-8')
        return dict(path=str(output),segments=segments,source=str(Path(path).resolve()))

    def voice(self, output):
        import tempfile
        # The phonemizer copies its DLL to a temp directory on Windows. Keep it
        # inside this app rather than relying on an external temp-folder ACL.
        private_temp = ROOT / 'work' / 'voice-temp'
        private_temp.mkdir(parents=True, exist_ok=True)
        tempfile.tempdir = str(private_temp)
        from kokoro_onnx import Kokoro
        import soundfile as sf
        text = self.spec.get('text','').strip()
        if not text:
            raise ValueError('Type the words you want Kokoro to speak.')
        if len(text) > 12000:
            raise ValueError('Use up to 12,000 characters per voice generation.')
        if not all((ROOT/'models/kokoro'/name).exists() for name in ['kokoro-v1.0.onnx','voices-v1.0.bin']):
            raise ValueError('Kokoro voices are not installed. Close the app and run Install.bat without -CoreOnly to download the speech assets.')
        self.progress('Loading Kokoro locally', 5)
        engine = Kokoro(str(ROOT/'models/kokoro/kokoro-v1.0.onnx'),str(ROOT/'models/kokoro/voices-v1.0.bin'))
        self.check()
        voice = self.spec.get('voice','af_heart')
        language = 'en-gb' if voice.startswith('b') else 'en-us'
        samples, rate = engine.create(text, voice=voice,speed=float(self.spec.get('voice_speed',1)),lang=language)
        self.check()
        sf.write(output,samples,rate,subtype='PCM_16')
        return dict(path=str(output),media=probe(output))

    def convert_image(self, source, output):
        from PIL import Image, ImageOps, UnidentifiedImageError

        def read_image(path):
            with Image.open(path) as opened:
                opened.seek(0)
                opened.load()
                return ImageOps.exif_transpose(opened).copy()

        self.check()
        self.progress('Converting image', 5)
        try:
            image = read_image(source)
        except (UnidentifiedImageError, OSError):
            # Retain FFmpeg's input-format support when Pillow has no decoder.
            decoded = self.work / 'decoded.png'
            self.ffmpeg(['-i', source, '-frames:v', '1', '-pix_fmt', 'rgba', decoded], 1, 'Reading image')
            image = read_image(decoded)
        profile = image.info.get('icc_profile') if image.mode in {'RGB', 'RGBA'} else None
        if image.mode not in {'RGB', 'RGBA'}:
            alpha = 'A' in image.getbands() or 'transparency' in image.info
            image = image.convert('RGBA' if alpha else 'RGB')
        if self.spec.get('size', 'Original') != 'Original':
            size = dimensions(self.spec['size'], {})
            if self.spec.get('fit', 'Fit') == 'Fill / crop':
                image = ImageOps.fit(image, size, method=Image.Resampling.LANCZOS)
            else:
                image = ImageOps.pad(image, size, method=Image.Resampling.LANCZOS,
                                     color=(0, 0, 0, 255) if image.mode == 'RGBA' else (0, 0, 0))
        image_format = self.spec.get('image_format', 'PNG')
        options = {'icc_profile': profile} if profile else {}
        if image_format == 'JPEG':
            if image.mode == 'RGBA':
                background = Image.new('RGB', image.size, 'white')
                background.paste(image, mask=image.getchannel('A'))
                image = background
            options.update(quality=95, subsampling=0, optimize=True)
        elif image_format == 'WebP':
            options.update(lossless=True, exact=True, method=6)
        partial = output.with_name(output.stem + '.partial' + output.suffix)
        try:
            self.check()
            image.save(partial, format=image_format.upper(), **options)
            with Image.open(partial) as verified:
                verified.load()
                if verified.size != image.size:
                    raise RuntimeError('Image output verification found incorrect dimensions.')
            self.check()
            media = probe(partial)
            os.replace(partial, output)
            media['path'] = str(output.resolve())
            self.progress('Finished', 100)
            return dict(path=str(output), media=media)
        finally:
            partial.unlink(missing_ok=True)

    def utility(self, output):
        op = self.spec['operation']
        sources = self.spec.get('audio') if op in {'join_audio','normalize_audio'} else self.spec.get('images') if op == 'image' else self.spec.get('videos')
        if not sources:
            raise ValueError('Add a file to the matching bucket first.')
        source = sources[0]
        if op == 'image':
            return self.convert_image(source, output)
        if op == 'join_audio':
            args, labels = [], []
            for i,p in enumerate(sources):
                args += ['-i',p]
                labels.append(f'[{i}:a]aresample=48000,aformat=channel_layouts=stereo,asetpts=PTS-STARTPTS[a{i}]')
            graph = ';'.join(labels) + ';' + ''.join(f'[a{i}]' for i in range(len(sources))) + f'concat=n={len(sources)}:v=0:a=1[out]'
            args += ['-filter_complex',graph,'-map','[out]','-c:a','pcm_s16le',output]
            duration = sum(probe(p)['duration'] for p in sources)
        elif op in {'extract_audio','normalize_audio'}:
            if not probe(source)['audio']:
                raise ValueError('That file has no audio stream.')
            args=['-i',source,'-vn']
            if op == 'normalize_audio': args += ['-af','loudnorm=I=-16:TP=-1.5:LRA=11']
            args += ['-c:a','pcm_s16le',output]
            duration=probe(source)['duration']
        else:
            info=probe(source)
            w,h=dimensions(self.spec.get('size','Original'),info)
            args=(['-ss',str(self.spec.get('start',0))] if op=='frame' else [])+['-i',source,'-vf',video_filter(w,h,self.spec.get('fit','Fit')),'-frames:v','1',output]
            duration=1
        try:
            self.ffmpeg(args,duration,'Processing '+op.replace('_',' '))
            self.check()
            return dict(path=str(output),media=probe(output))
        except Exception:
            output.unlink(missing_ok=True)
            raise
