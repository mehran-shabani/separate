from pathlib import Path
import os, time, json
os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING']='1'
import torch, numpy as np, soundfile as sf
from hyperpyyaml import load_hyperpyyaml
from scipy.signal import butter,sosfiltfilt

torch.set_num_threads(2)
root=Path(__file__).resolve().parent
folder=root/'.models/sepformer-whamr'
print('Loading separator',flush=True)
with open(folder/'hyperparams.yaml',encoding='utf-8') as f:
    hp=load_hyperpyyaml(f)
for name in ['encoder','decoder','masknet']:
    hp['modules'][name].load_state_dict(torch.load(folder/(name+'.ckpt'),map_location='cpu',weights_only=True))
    hp['modules'][name].eval()
x,sr=sf.read(root/'output/01_original.wav',dtype='float32')
assert sr==8000 and x.ndim==1
# Remove DC/low rumble only before separation.
x=sosfiltfilt(butter(2,70,fs=sr,btype='highpass',output='sos'),x).astype('float32')
t=time.time()
print('Separating overlapping windows, seconds:',len(x)/sr,flush=True)
def separate(part):
    wave=torch.from_numpy(part).unsqueeze(0)
    encoded=hp['modules']['encoder'](wave)
    masks=hp['modules']['masknet'](encoded)
    streams=[]
    for i in range(2):
        y=hp['modules']['decoder'](encoded*masks[i]).squeeze().numpy()
        y=np.pad(y,(0,max(0,len(part)-len(y))))[:len(part)]
        streams.append(y)
    return np.stack(streams,axis=1)
win,overlap=10*sr,4*sr
result=np.zeros((len(x),2),np.float32)
weights=np.zeros(len(x),np.float32)
alignment=[]
with torch.inference_mode():
    for start in range(0,len(x),win-overlap):
        end=min(start+win,len(x))
        if end-start<sr: break
        y=separate(x[start:end])
        n=min(overlap,end-start)
        if start:
            prev=result[start:start+n]/np.maximum(weights[start:start+n,None],1e-9)
            def corr(a,b):
                return float(np.dot(a,b)/(np.linalg.norm(a)*np.linalg.norm(b)+1e-12))
            same=corr(prev[:,0],y[:n,0])+corr(prev[:,1],y[:n,1])
            swap=corr(prev[:,0],y[:n,1])+corr(prev[:,1],y[:n,0])
            if swap>same: y=y[:,::-1]
            alignment.append({'start':start/sr,'same':same,'swapped':swap,'did_swap':swap>same})
        w=np.ones(end-start,np.float32)
        if start: w[:n]=np.linspace(0,1,n)
        if end<len(x): w[-overlap:]=np.linspace(1,0,overlap)
        result[start:end]+=y*w[:,None]
        weights[start:end]+=w
        print('Separated',start/sr,'to',end/sr,'elapsed',round(time.time()-t,1),flush=True)
        if end==len(x): break
result/=np.maximum(weights[:,None],1e-9)
for i in range(2):
    y=result[:,i]
    peak=max(float(np.max(np.abs(y))),1e-8)
    sf.write(root/f'output/0{i+3}_speaker_{i+1}.wav',y*min(0.94/peak,8),sr,subtype='PCM_16')
np.save(root/'output/separated_raw.npy',result)
(root/'output/separation_alignment.json').write_text(json.dumps(alignment,indent=2))
print('Separation complete in',round(time.time()-t,1),'seconds',flush=True)
