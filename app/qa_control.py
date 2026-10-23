"""QA-only: send ordinary mouse/keyboard events to the app. No state inspection."""
import json,sys,time,uuid,os
from pathlib import Path
if sys.argv[1].startswith('{'):r=json.loads(sys.argv[1])
else:
 command=sys.argv[1];r={'action':command}
 if command in ['click','doubleclick','drop']:r.update(x=int(sys.argv[2]),y=int(sys.argv[3]))
 if command=='drop':r['paths']=sys.argv[4:]
 if command=='type':r['text']=sys.argv[2]
 if command=='key':r['key']=sys.argv[2]
directory=Path(__file__).resolve().parent/'qa';directory.mkdir(exist_ok=True)
r['id']=uuid.uuid4().hex
temporary=directory/('request-'+r['id']+'.tmp');temporary.write_text(json.dumps(r),encoding='utf-8');os.replace(temporary,directory/'request.json')
reply=directory/('response-'+r['id']+'.json')
for _ in range(300):
 if reply.exists():
  print(reply.read_text(encoding='utf-8'));reply.unlink(missing_ok=True);break
 time.sleep(.05)
else:raise SystemExit('QA app did not reply within 15 seconds.')
