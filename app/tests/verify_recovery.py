"""Cancellation, invalid ranges, path handling and source-preservation checks."""
from pathlib import Path
import hashlib,json,threading,time,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from media_workbench.engine import ROOT,Job,Cancelled,probe
from media_workbench.captions import parse_srt,make_ass

source=ROOT/'sample-media/03 Timelapse source 256 seconds.mp4'
before=hashlib.sha256(source.read_bytes()).hexdigest()
output_dir=ROOT/'tests/results/Unicode 雪 O’Brien'
output_dir.mkdir(exist_ok=True)
valid=dict(operation='edit',videos=[str(source)],output_dir=str(output_dir),size='720p',speed=1)
job=Job(valid)
errors=[]
def run():
    try:job.export()
    except Exception as exc:errors.append(exc)
t=threading.Thread(target=run);t.start();time.sleep(.3);job.cancel();t.join(20)
assert not t.is_alive(),'Cancellation left a worker running'
assert errors and isinstance(errors[0],Cancelled),errors
assert not list(output_dir.glob('*.partial.mp4')),'Partial export remained after cancellation'
assert not job.output.exists(),'Cancelled output was marked complete'
assert hashlib.sha256(source.read_bytes()).hexdigest()==before,'Source changed'
for settings in [dict(start=20,end=10),dict(speed=0),dict(speed=99999)]:
    try:Job(dict(valid,**settings)).export()
    except ValueError:pass
    else:raise AssertionError('Invalid settings were accepted')
result=Job(dict(valid,speed=256,watermark=str(ROOT/'sample-media/Logo transparent.png'),
                subtitles='1\n00:00:00,000 --> 00:00:01,000\nUnicode path works.\n')).export()
assert abs(probe(result['path'])['duration']-1)<.05
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
edited=parse_srt('1\n00:00:05,000 --> 00:00:06,000\nNew corrected words\n')
ass=make_ass(edited,1280,720,'Highlight',words=[dict(start=0,end=1,words=[dict(start=0,end=1,word='New corrected words')])])
assert '0:00:05.00' in ass and 'New' in ass
(ROOT/'tests/results/recovery.json').write_text(json.dumps(dict(cancellation=True,invalid_ranges=True,unicode_output=True,source_preserved=True,edited_caption_timing=True),indent=2))
print('PASS cancellation, invalid settings, Unicode output, source preservation, edited caption timing')
