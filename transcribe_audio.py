from pathlib import Path
import json, sys, os, time
os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING']='1'
from faster_whisper import WhisperModel
root=Path(__file__).resolve().parent
print('Loading transcription model',flush=True)
model=WhisperModel(str(root/'.models/faster-whisper-large-v3-turbo'),device='cpu',compute_type='int8',cpu_threads=2,num_workers=1)
files=sys.argv[1:] or ['01_original.wav','02_cleaned.wav','03_speaker_1.wav','04_speaker_2.wav']
use_vad='--no-vad' not in files
files=[f for f in files if f!='--no-vad']
for filename in files:
    path=root/'output'/filename
    if not path.exists(): continue
    print('Transcribing',filename,flush=True)
    segments,info=model.transcribe(str(path),language='fa',task='transcribe',beam_size=5,temperature=0,condition_on_previous_text=False,word_timestamps=True,vad_filter=use_vad,vad_parameters=dict(min_silence_duration_ms=400,speech_pad_ms=300))
    print('VAD retained',info.duration_after_vad,'of',info.duration,flush=True)
    data=[]
    for s in segments:
        d={'start':s.start,'end':s.end,'text':s.text,'avg_logprob':s.avg_logprob,'no_speech_prob':s.no_speech_prob,'words':[{'start':w.start,'end':w.end,'word':w.word,'probability':w.probability} for w in (s.words or [])]}
        data.append(d)
        print(json.dumps(d,ensure_ascii=True),flush=True)
    suffix='_asr.json' if use_vad else '_full_asr.json'
    (root/'output'/(path.stem+suffix)).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Completed',filename,flush=True)
