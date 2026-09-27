from pathlib import Path
import json
from faster_whisper import WhisperModel
root=Path(__file__).resolve().parent
model=WhisperModel(str(root/'.models/faster-whisper-small'),device='cpu',compute_type='int8',cpu_threads=2)
for name in ['01_original.wav','01_original_boosted.wav','speaker_1_cleaned_boosted.wav','speaker_2_cleaned_boosted.wav']:
    print('Crosschecking',name,flush=True)
    segs,info=model.transcribe(str(root/'output'/name),language='fa',beam_size=5,temperature=0,condition_on_previous_text=False,vad_filter=False,repetition_penalty=1.15,no_repeat_ngram_size=3)
    data=[]
    for s in segs:
        d={'start':s.start,'end':s.end,'text':s.text,'avg_logprob':s.avg_logprob,'no_speech_prob':s.no_speech_prob}
        data.append(d);print(json.dumps(d,ensure_ascii=True),flush=True)
    (root/'output'/(Path(name).stem+'_small_asr.json')).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
