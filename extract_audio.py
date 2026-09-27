from pathlib import Path
import json, subprocess
import av, numpy as np, soundfile as sf, imageio_ffmpeg

root = Path(__file__).resolve().parent
out = root / 'output'
out.mkdir(exist_ok=True)
source = root / '01012007.3gp'
with av.open(str(source)) as c:
    s = c.streams.audio[0]
    meta = {'source': source.name, 'codec': s.codec_context.name,
            'sample_rate': s.codec_context.sample_rate, 'channels': s.codec_context.channels,
            'duration_seconds': float(s.duration * s.time_base) if s.duration else c.duration / 1e6}
ff = imageio_ffmpeg.get_ffmpeg_exe()
def convert(name, *args):
    subprocess.run([ff, '-hide_banner', '-loglevel', 'error', '-y', '-i', str(source), '-vn', *args, str(out / name)], check=True)
convert('01_original.wav', '-c:a', 'pcm_s16le')
convert('02_cleaned.wav', '-af', 'highpass=f=90,lowpass=f=3700,afftdn=nf=-28:nr=8:tn=1,loudnorm=I=-18:TP=-2:LRA=11', '-ar','16000','-c:a','pcm_s16le')
convert('preview.mp3','-t','30','-af','volume=2','-c:a','libmp3lame','-b:a','64k')
x,sr=sf.read(out/'01_original.wav')
meta.update({'samples':len(x),'duration_decoded':len(x)/sr,'peak':float(np.max(np.abs(x))), 'rms':float(np.sqrt(np.mean(x*x)))})
(out/'metadata.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
print(json.dumps(meta,indent=2))
