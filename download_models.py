from pathlib import Path
import urllib.request, json, concurrent.futures, time
root=Path(__file__).resolve().parent/'.models'
repos={'speechbrain/sepformer-whamr':['hyperparams.yaml','encoder.ckpt','decoder.ckpt','masknet.ckpt'],
       'mobiuslabsgmbh/faster-whisper-large-v3-turbo':['config.json','model.bin','tokenizer.json','preprocessor_config.json','vocabulary.json'],
       'Systran/faster-whisper-small':['config.json','model.bin','tokenizer.json','vocabulary.txt']}
def fetch(job):
    repo,name=job
    target=root/repo.split('/')[-1]/name
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():
        return str(target)
    print('Downloading',repo,name,flush=True)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(f'https://huggingface.co/{repo}/resolve/main/{name}',timeout=120) as r, open(str(target)+'.part','wb') as f:
                while True:
                    b=r.read(1024*1024)
                    if not b: break
                    f.write(b)
            Path(str(target)+'.part').replace(target)
            print('Downloaded',name,target.stat().st_size,flush=True)
            return str(target)
        except Exception as e:
            if getattr(e,'code',None)==404 and name in ['preprocessor_config.json','vocabulary.json']:
                print('Optional absent:',name,flush=True);return
            print('Retry',name,str(e),flush=True)
            time.sleep(2)
    raise RuntimeError(name)
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    list(pool.map(fetch,[(r,f) for r,files in repos.items() for f in files]))
