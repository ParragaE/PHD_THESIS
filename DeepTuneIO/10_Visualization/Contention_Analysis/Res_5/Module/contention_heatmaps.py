"""DXT contention visualizations: true time/byte overlap, rank involvement.

Pair event indices refer to _valid_events(events).reset_index(drop=True) from
Access_Pattern_Visualization.plotting. The exact same normalized event table
must be supplied; do not join to a different DXT file by row number.
"""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm, Normalize
from matplotlib.gridspec import GridSpec

CASES = {
    'AB': 'Exact and partial file-region overlap',
    'A_exact': 'Concurrent I/O Accesses to Identical File Regions',
    'B_partial': 'Concurrent I/O Accesses to Partially Overlapping File Regions',
    'C_shared_resource': 'Concurrent I/O Activity on Shared Storage Resources',
}
PALETTES = ('Blues', 'viridis', 'cividis', 'YlOrRd', 'magma', 'plasma', 'PuBuGn', 'turbo')

def _palette(name):
    if name not in PALETTES:
        raise ValueError(f'Paleta no admitida: {name}. Opciones: {PALETTES}')
    cmap = plt.get_cmap(name).copy()
    cmap.set_bad('#f1f3f5')
    return cmap

def _norm(z, logarithmic):
    maximum = max(1, int(np.max(z)))
    if logarithmic:
        return LogNorm(vmin=1, vmax=max(2, maximum))
    return Normalize(vmin=0, vmax=max(1, maximum))

def _metadata_line(metadata, jobid):
    if not metadata:
        return f'JobID: {jobid}'
    fields = [('application','Application'),('filesystem','Filesystem'),('file_format','Format'),
              ('access_mode','Access mode'),('nodes','Nodes'),('processes','I/O processes'),
              ('epochs','Epochs')]
    items = [str(metadata[k]) for k, _ in fields if metadata.get(k) is not None and str(metadata[k]).strip()]
    items.append(f'JobID: {jobid}')
    return ' | '.join(items)


def load_pairs(path):
    d=pd.read_csv(path)
    needed={'case','event_a','event_b','process_a','process_b','start_s','end_s','file_a','file_b'}
    if not needed.issubset(d):raise ValueError(f'Pair CSV missing: {sorted(needed-set(d))}')
    return d

def _events_normalized(events):
    """Match the event ordering and validity used by Access_Pattern detector."""
    from Access_Pattern_Visualization.plotting import _valid_events
    return _valid_events(events).reset_index(drop=True)

def build_overlap_rectangles(pairs, events, *, case='AB', process=None, file=None):
    """Return actual time/offset intersection rectangles; C excluded by design."""
    d=pairs[pairs['case'].isin(['A_exact','B_partial'] if case=='AB' else [case])].copy()
    if process is not None:
        d=d[(d.process_a==int(process))|(d.process_b==int(process))]
    ev=_events_normalized(events)
    if len(ev)==0 or d.empty:return pd.DataFrame(columns=['t0','t1','o0','o1','file','process_a','process_b','case'])
    d['event_a']=pd.to_numeric(d.event_a,errors='coerce');d['event_b']=pd.to_numeric(d.event_b,errors='coerce')
    d=d[d.event_a.between(0,len(ev)-1)&d.event_b.between(0,len(ev)-1)].copy()
    if d.empty:return pd.DataFrame(columns=['t0','t1','o0','o1','file','process_a','process_b','case'])
    ia=d.event_a.to_numpy(dtype=int);ib=d.event_b.to_numpy(dtype=int)
    a=ev.iloc[ia];b=ev.iloc[ib]
    a0=a.offset_bytes.to_numpy(float);b0=b.offset_bytes.to_numpy(float)
    a1=a0+a.request_size_bytes.to_numpy(float);b1=b0+b.request_size_bytes.to_numpy(float)
    d['o0']=np.maximum(a0,b0);d['o1']=np.minimum(a1,b1)
    d['t0']=pd.to_numeric(d.start_s,errors='coerce');d['t1']=pd.to_numeric(d.end_s,errors='coerce')
    d['file']=d.file_a.astype(str)
    d=d[(d.o1>d.o0)&(d.t1>d.t0)&(d.file_a.astype(str)==d.file_b.astype(str))]
    if file is not None:d=d[d.file==str(file)]
    return d[['t0','t1','o0','o1','file','process_a','process_b','case']]

def heatmap_with_marginals(pairs,events,outdir,*,case='AB',process=None,file=None,time_bins=50,offset_bins=40,max_pairs=200000,jobid=None,palette='Blues',log_scale=True,metadata=None):
    """Time × offset overlap coverage (pair-cell intersection counts), one file per figure.

    Each candidate contributes once per intersected time/offset cell, not by its
    event start only. This is a binned pair-coverage count, NOT latency or proof
    of performance degradation. A sampled pair cap is explicit in the title.
    """
    outdir=Path(outdir);outdir.mkdir(parents=True,exist_ok=True)
    rect=build_overlap_rectangles(pairs,events,case=case,process=process,file=file)
    if rect.empty:return []
    results=[]
    for fname,group in rect.groupby('file',sort=True):
        if len(group)>max_pairs:
            group=group.sample(max_pairs,random_state=13)
            sampled=True
        else:sampled=False
        t0=float(group.t0.min());t1=float(group.t1.max());o0=float(group.o0.min());o1=float(group.o1.max())
        if t1<=t0 or o1<=o0:continue
        te=np.linspace(t0,t1,int(time_bins)+1);oe=np.linspace(o0,o1,int(offset_bins)+1)
        z=np.zeros((offset_bins,time_bins),dtype=np.int64)
        for rec in group.itertuples(index=False):
            x0=max(0,np.searchsorted(te,rec.t0,side='right')-1)
            x1=min(time_bins-1,np.searchsorted(te,rec.t1,side='left'))
            y0=max(0,np.searchsorted(oe,rec.o0,side='right')-1)
            y1=min(offset_bins-1,np.searchsorted(oe,rec.o1,side='left'))
            if x1>=x0 and y1>=y0:z[y0:y1+1,x0:x1+1]+=1
        fig=plt.figure(figsize=(11,7),layout='constrained')
        gs=GridSpec(2,2,figure=fig,height_ratios=[1,4],width_ratios=[5,1])
        top=fig.add_subplot(gs[0,0]);ax=fig.add_subplot(gs[1,0],sharex=top);side=fig.add_subplot(gs[1,1],sharey=ax)
        mesh=ax.pcolormesh(te,oe/1048576,np.ma.masked_where(z==0,z) if log_scale else z,
                           cmap=_palette(palette),norm=_norm(z,log_scale),shading='flat')
        ax.set(xlabel='Time (s)',ylabel='File offset (MiB)')
        top.bar((te[:-1]+te[1:])/2,z.sum(axis=0),width=np.diff(te)*.9,color='#526a82')
        top.set_ylabel('Pair-cell coverage');top.tick_params(labelbottom=False)
        side.barh((oe[:-1]+oe[1:])/2097152,z.sum(axis=1),height=np.diff(oe)/1048576*.9,color='#526a82')
        side.set_xlabel('Pair-cell coverage');side.tick_params(labelleft=False)
        fig.colorbar(mesh,ax=ax,label='Concurrent operation-pair coverage per time/offset cell')
        title = ('Spatiotemporal Overlap of Concurrent I/O Operations' if case=='AB' else CASES.get(case,case))
        fig.suptitle(title+'\n'+_metadata_line(metadata,jobid)+'\nFile: '+str(fname)+\
                     (' | Sampled candidate pairs' if sampled else '')+' | Not measured slowdown',fontsize=10)
        suffix=f'{case}_P{process if process is not None else "all"}_{len(results)+1:02d}'
        path=outdir/f'01_offset_time_{suffix}.png';fig.savefig(path,dpi=180,bbox_inches='tight');plt.close(fig)
        results.append(path)
        pd.DataFrame(z,index=[f'{oe[i]/1048576:.6g}-{oe[i+1]/1048576:.6g} MiB' for i in range(offset_bins)],columns=[f'{te[i]:.6g}-{te[i+1]:.6g} s' for i in range(time_bins)]).to_csv(outdir/f'01_offset_time_{suffix}.csv')
    return results

def process_matrix(pairs,outdir,*,case='AB',process=None,jobid=None,palette='Blues',log_scale=True,metadata=None):
    outdir=Path(outdir);outdir.mkdir(parents=True,exist_ok=True)
    cases=['A_exact','B_partial'] if case=='AB' else [case]
    d=pairs[pairs.case.isin(cases)].copy()
    if d.empty:return None
    d=d.dropna(subset=['process_a','process_b'])
    d=d[d.process_a!=d.process_b]
    ranks=sorted(set(d.process_a.astype(int))|set(d.process_b.astype(int)))
    if not ranks:return None
    pos={p:i for i,p in enumerate(ranks)};z=np.zeros((len(ranks),len(ranks)),dtype=int)
    for a,b in zip(d.process_a.astype(int),d.process_b.astype(int)):
        z[pos[a],pos[b]]+=1;z[pos[b],pos[a]]+=1
    fig,ax=plt.subplots(figsize=(max(7,len(ranks)*.19),max(6,len(ranks)*.19)),layout='constrained')
    masked=np.ma.masked_where(z==0,z)
    im=ax.imshow(masked if log_scale else z,cmap=_palette(palette),norm=_norm(z,log_scale),interpolation='nearest')
    if process is not None:
        for i,r in enumerate(ranks):
            if r!=int(process):
                ax.axhspan(i-.5,i+.5,color='white',alpha=.5)
                ax.axvspan(i-.5,i+.5,color='white',alpha=.5)
    step=max(1,len(ranks)//16);ticks=np.arange(0,len(ranks),step)
    ax.set_xticks(ticks,[ranks[i] for i in ticks]);ax.set_yticks(ticks,[ranks[i] for i in ticks]);ax.set(xlabel='Process / rank',ylabel='Process / rank',title='Concurrent I/O Interactions Between Processes\n'+_metadata_line(metadata,jobid)+'\n'+CASES.get(case,case))
    fig.colorbar(im,ax=ax,label='Concurrent I/O operation pairs (not measured degradation)')
    path=outdir/f'02_process_matrix_{case}.png';fig.savefig(path,dpi=180,bbox_inches='tight');plt.close(fig)
    pd.DataFrame(z,index=ranks,columns=ranks).to_csv(outdir/f'02_process_matrix_{case}.csv',index_label='process')
    return path

def render(pairs_csv,events_csv,output,*,case='AB',process=None,file=None,jobid=None):
    """Use exact event-level CSV supplied to Access_Pattern detector, with same ordering."""
    from Access_Pattern_Visualization.loader import load_event_csvs
    pairs=load_pairs(pairs_csv)
    events=load_event_csvs([Path(p) for p in (events_csv if isinstance(events_csv,(list,tuple)) else [events_csv])])
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    images=heatmap_with_marginals(pairs,events,out,case=case,process=process,file=file,jobid=jobid)
    matrix=process_matrix(pairs,out,case=case,process=process,jobid=jobid)
    return images+([matrix] if matrix else [])
