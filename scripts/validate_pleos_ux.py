"""Official console-only UX restriction probe. Refuses physical-device serials."""
import subprocess,threading,time,json,argparse
from pathlib import Path
from urllib.request import Request,urlopen
parser=argparse.ArgumentParser()
parser.add_argument('--serial',default='emulator-5584')
args=parser.parse_args()
if not args.serial.startswith('emulator-'): raise SystemExit('Refusing a physical device')
adb=['.tooling/android-sdk/platform-tools/adb','-s',args.serial]
assert subprocess.check_output(adb+['shell','getprop','ro.kernel.qemu'],text=True).strip()=='1'
stop=threading.Event()
def api(path,method='PUT'):
 with urlopen(Request('http://127.0.0.1:8088'+path,method=method),timeout=8) as r:return json.load(r)
def pulse():
 while not stop.is_set():
  api('/browser/session?client=carcue-ux-validation','POST');stop.wait(.8)
thread=threading.Thread(target=pulse,daemon=True);thread.start();time.sleep(1)
subprocess.run(adb+['logcat','-c'],check=True)
try:
 subprocess.run(adb+['shell','am','start','-W','-n','com.carcue.app/com.carcue.app.MainActivity'],check=True,capture_output=True)
 api('/vehicle/gear?gear=Drive');api('/vehicle/controls?speed=20&accelerator=0&brake=0')
 time.sleep(3)
 with open('output/qa/pleos-driving-restriction.png','wb') as f:subprocess.run(adb+['exec-out','screencap','-p'],stdout=f,check=True)
finally:
 api('/vehicle/controls?speed=0&accelerator=0&brake=0');api('/vehicle/gear?gear=Park');time.sleep(2)
 stop.set();thread.join();api('/browser/session?client=carcue-ux-validation&closing=1','POST')
text=subprocess.check_output(adb+['logcat','-d','-s','CarCueVehicle:I'],text=True)
Path('output/qa/pleos-ux-events.txt').write_text(text);print(text)
required=['UX:GET:requires=false','UX:CALLBACK:requires=true','UX:CALLBACK:requires=false']
if not all(value in text for value in required):
 raise SystemExit('UX change/restore evidence missing; inspect output/qa/pleos-ux-events.txt')
print('PASS: actual UX initial read, restriction callback and parked restore')
