"""SRT interchange and ASS caption styles; no online services."""
import re
import math


def seconds(value):
    value = str(value).strip().replace(',', '.')
    parts = value.split(':')
    if len(parts) > 3:
        raise ValueError('Use seconds or HH:MM:SS for a time.')
    result = 0.0
    for part in parts:
        result = result * 60 + float(part)
    if not math.isfinite(result) or result < 0:
        raise ValueError('Times must be finite, non-negative numbers.')
    return result


def clock(value, ass=False):
    scale = 100 if ass else 1000
    total = max(0, round(value * scale))
    h, total = divmod(total, 3600 * scale)
    m, total = divmod(total, 60 * scale)
    s, fraction = divmod(total, scale)
    return (f'{h}:{m:02}:{s:02}.{fraction:02}' if ass else
            f'{h:02}:{m:02}:{s:02},{fraction:03}')


def to_srt(segments):
    return '\n\n'.join(f'{i}\n{clock(s["start"])} --> {clock(s["end"])}\n{s["text"].strip()}'
                        for i, s in enumerate(segments, 1)) + '\n'


def parse_srt(text):
    result = []
    for block in re.split(r'\n\s*\n', text.strip().replace('\r', '')):
        lines = block.strip().splitlines()
        if lines and lines[0].strip().isdigit():
            lines.pop(0)
        if not lines:
            continue
        if '-->' not in lines[0] or len(lines) < 2:
            raise ValueError('Each subtitle needs a time range and text, separated by a blank line.')
        left, right = lines[0].split('-->', 1)
        start, end = seconds(left.strip()), seconds(right.strip())
        if end <= start:
            raise ValueError('A subtitle end must come after its start.')
        if result and start < result[-1]['start']:
            raise ValueError('Subtitles must be in time order.')
        result.append(dict(start=start, end=end, text='\n'.join(lines[1:]).strip()))
    if not result:
        raise ValueError('There are no subtitles to export.')
    return result


def safe_text(text):
    return text.replace('\\', '／').replace('{', '(').replace('}', ')').replace('\n', r'\N')


def make_ass(segments, width, height, style='Highlight', font_size=48, position='Bottom', words=None):
    size = max(16, round(font_size * height / 1080))
    margin = round(height * 0.09)
    alignment = 8 if position == 'Top' else 5 if position == 'Center' else 2
    boxed = style == 'Boxed'
    header = f'''[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,{size},&H00FFFFFF,&H0000FFFF,&H00181818,&H80000000,-1,0,0,0,100,100,0,0,{3 if boxed else 1},{3 if boxed else 2},1,{alignment},40,40,{margin},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    events = []
    for index, segment in enumerate(segments):
        def event(start, end, text):
            if end > start:
                events.append(f'Dialogue: 0,{clock(start, True)},{clock(end, True)},Default,,0,0,0,,{text}')
        if style != 'Highlight':
            event(segment['start'], segment['end'], safe_text(segment['text']))
            continue
        tokens = segment['text'].split()
        original = words[index].get('words', []) if words and index < len(words) else []
        matches = ' '.join(w.get('word', '').strip() for w in original)
        unchanged_times = (words and index < len(words) and
                           abs(words[index]['start']-segment['start']) < .02 and
                           abs(words[index]['end']-segment['end']) < .02)
        if matches.split() == tokens and original and unchanged_times:
            timed = [dict(text=t, start=max(segment['start'], float(w['start'])),
                          end=min(segment['end'], float(w['end']))) for t, w in zip(tokens, original)]
        else:
            span = (segment['end'] - segment['start']) / max(1, len(tokens))
            timed = [dict(text=t, start=segment['start'] + i * span,
                          end=segment['start'] + (i + 1) * span) for i, t in enumerate(tokens)]
        for base in range(0, len(timed), 6):
            group = timed[base:base + 6]
            for j, word in enumerate(group):
                start = group[0]['start'] if j == 0 else word['start']
                end = group[j + 1]['start'] if j + 1 < len(group) else group[-1]['end']
                line = ' '.join((r'{\c&H00E8FF&}' if k == j else r'{\c&HFFFFFF&}') + safe_text(w['text'])
                                for k, w in enumerate(group))
                event(start, end, line)
    return header + '\n'.join(events) + '\n'
