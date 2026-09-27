from pathlib import Path
import json, subprocess, hashlib
import numpy as np, soundfile as sf, imageio_ffmpeg
root=Path(__file__).resolve().parent
out=root/'output'
ff=imageio_ffmpeg.get_ffmpeg_exe()
metrics={}
for i in (1,2):
    src=out/f'0{i+2}_speaker_{i}.wav'
    dst=out/f'speaker_{i}_cleaned.wav'
    subprocess.run([ff,'-hide_banner','-loglevel','error','-y','-i',str(src),'-af','highpass=f=90,lowpass=f=3700,afftdn=nf=-35:nr=5:tn=1,loudnorm=I=-18:TP=-2:LRA=11','-ar','16000','-c:a','pcm_s16le',str(dst)],check=True)
    subprocess.run([ff,'-hide_banner','-loglevel','error','-y','-i',str(dst),'-c:a','libmp3lame','-b:a','96k',str(dst.with_suffix('.mp3'))],check=True)
for p in out.glob('*.wav'):
    x,sr=sf.read(p)
    metrics[p.name]={'duration':len(x)/sr,'sample_rate':sr,'finite':bool(np.isfinite(x).all()),'peak':float(np.max(np.abs(x))),'rms':float(np.sqrt(np.mean(x*x)))}
raw=np.load(out/'separated_raw.npy')
metrics['stream_correlation']=float(np.corrcoef(raw.T)[0,1])
metrics['original_sha256']=hashlib.sha256((root/'01012007.3gp').read_bytes()).hexdigest()
(out/'validation.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
print(json.dumps(metrics,indent=2))
