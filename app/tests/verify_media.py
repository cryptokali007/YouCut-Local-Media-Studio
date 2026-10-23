"""Meaningful end-to-end checks using actual FFmpeg output and local models."""
from pathlib import Path
import json
import os
import socket
import subprocess
import sys
import time
import argparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from media_workbench.engine import ROOT,Job,probe,binaries
from media_workbench.captions import to_srt

FIX=ROOT/'sample-media';FIX.mkdir(exist_ok=True)
OUT=ROOT/'tests/results';OUT.mkdir(exist_ok=True)
FF,FP=binaries()
results=[]

def raw(args):
    p=subprocess.run([FF,'-hide_banner','-loglevel','error','-y','-threads','2']+list(map(str,args)),capture_output=True,text=True)
    if p.returncode:raise RuntimeError(p.stderr)

def check(name,spec,duration=None):
    t=time.perf_counter();result=Job(dict(output_dir=str(OUT),size='Original',**spec)).export()
    info=probe(result['path'])
    if duration is not None:assert abs(info['duration']-duration)<.12,(name,info['duration'],duration)
    if info['kind']=='video':raw(['-i',result['path'],'-f','null','-'])
    results.append(dict(name=name,path=result['path'],duration=info['duration'],seconds=round(time.perf_counter()-t,3)))
    print('PASS',name,info['duration'],flush=True)
    return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--core-only',action='store_true',help='Skip hardware-specific and speech-model checks.')
    args=parser.parse_args()
    from PIL import Image,ImageDraw
    a=FIX/'01 Landscape with sound.mp4';b=FIX/'02 Portrait silent.mp4';long=FIX/'03 Timelapse source 256 seconds.mp4';song=FIX/'Music 7 seconds.wav';logo=FIX/'Logo transparent.png'
    if not a.exists():raw(['-f','lavfi','-i','testsrc2=s=320x180:r=24:d=3','-f','lavfi','-i','sine=frequency=440:duration=3','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-shortest',a])
    if not b.exists():raw(['-f','lavfi','-i','testsrc2=s=180x320:r=25:d=2','-c:v','libx264','-an',b])
    if not long.exists():raw(['-f','lavfi','-i','testsrc2=s=128x72:r=4:d=256','-c:v','libx264','-preset','ultrafast','-an',long])
    if not song.exists():raw(['-f','lavfi','-i','sine=frequency=660:duration=7','-ac','2',song])
    image=Image.new('RGBA',(180,64),(0,0,0,0));draw=ImageDraw.Draw(image);draw.rounded_rectangle((0,0,179,63),8,fill=(0,150,140,230));draw.text((15,23),'MY WATERMARK',fill='white');image.save(logo)
    check('trim plus speed and pitch audio',dict(operation='edit',videos=[str(a)],start=.5,end=2.5,speed=2,keep_audio=True),1)
    for speed in [64,128,256]:check(f'actual {speed}x export',dict(operation='edit',videos=[str(long)],speed=speed,keep_audio=False),256/speed)
    check('mixed video hard concat',dict(operation='join',videos=[str(a),str(b)],transition='none'),5)
    joined=check('mixed fps size missing-audio transition',dict(operation='join',videos=[str(a),str(b)],transition='fade',transition_duration=.4),4.6)
    check('loop short video to long music',dict(operation='music',videos=[str(a)],audio=[str(song)],loop=True),7)
    check('music mix and preserve video duration',dict(operation='music',videos=[str(a)],audio=[str(song)],loop=False,mix=True),3)
    segments=[dict(start=.1,end=2.8,text='These are styled local captions.')]
    for style in ['Highlight','Boxed','Outlined']:
        check('caption '+style,dict(operation='captions',videos=[str(a)],subtitles=to_srt(segments),caption_style=style,watermark=str(logo)),3)
    check('slideshow transitions',dict(operation='slideshow',images=[str(logo),str(logo)],slide_duration=2,transition='fade',transition_duration=.4),3.6)
    for operation,kwargs in [('extract_audio',dict(videos=[str(a)])),('join_audio',dict(audio=[str(song),str(song)])),('normalize_audio',dict(audio=[str(song)])),('frame',dict(videos=[str(a)],start=1)),('image',dict(images=[str(logo)]))]:check(operation,dict(operation=operation,**kwargs))
    if os.environ.get('YCO_TEST_NVENC')=='1':
        check('real NVIDIA encoder',dict(operation='edit',videos=[str(a)],encoder='NVIDIA'),3)
    else:print('SKIP optional NVIDIA test (set YCO_TEST_NVENC=1 to enable)',flush=True)
    if args.core_only:
        (OUT/'verification.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
        print('COMPLETE',len(results),'real core media checks',flush=True)
        return
    # Deny outbound socket connections, while exercising actual voice and speech inference.
    def denied(*a,**k):raise AssertionError('Unexpected network attempt during offline inference')
    socket.socket.connect=denied;socket.create_connection=denied
    voice=check('offline Kokoro narration',dict(operation='voice',text='Welcome to YouCutOwn Studio. This is a local offline subtitle test.',voice='af_heart'))
    import shutil
    shutil.copy2(voice['path'],FIX/'Kokoro spoken example.wav')
    speech_video=FIX/'04 Spoken caption example.mp4'
    raw(['-stream_loop','-1','-i',a,'-i',voice['path'],'-map','0:v','-map','1:a','-c:v','libx264','-c:a','aac','-t',probe(voice['path'])['duration'],speech_video])
    trans=Job(dict(operation='transcribe',videos=[str(speech_video)],model='base.en',output_dir=str(OUT))).export()
    assert len(' '.join(s['text'] for s in trans['segments']).split())>=7,trans
    assert any(s['words'] for s in trans['segments'])
    results.append(dict(name='offline Whisper transcription',path=trans['path'],text=' '.join(s['text'] for s in trans['segments'])))
    print('PASS offline Whisper transcription',results[-1]['text'],flush=True)
    check('actual transcription caption burn',dict(operation='captions',videos=[str(speech_video)],subtitles=to_srt(trans['segments']),word_segments=trans['segments'],caption_style='Highlight'))
    (FIX/'Example subtitles.srt').write_text(to_srt(segments),encoding='utf-8')
    (OUT/'verification.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    print('COMPLETE',len(results),'real media checks',flush=True)

if __name__=='__main__':main()
