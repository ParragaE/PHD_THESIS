"""DeepTuneIO — standalone contention evidence analysis.

Consumes outputs of DXT detector (Module 10) and campaign performance CSV.
Never interprets concurrent requests alone as measured performance degradation.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

CASES = {'A_exact':'Exact-Range Concurrent Access',
         'B_partial':'Partial-Range Concurrent Access',
         'C_shared_resource':'Shared-Resource Concurrent I/O'}
ALIASES = {'individual':'individual','independent':'individual',
           'shared':'shared','shared_reload_shuffle':'shared_reload_shuffle',
           'shared+reload+shuffle':'shared_reload_shuffle','shared/reload/shuffle':'shared_reload_shuffle',
           'shared_distributed':'shared_distributed','distributed_shared':'shared_distributed',
           'full_sharing':'full_sharing','full sharing':'full_sharing','shared_full':'full_sharing',
           'file_per_process':'file_per_process','one_file_per_process':'file_per_process',
           'one file per process':'file_per_process'}

def norm_mode(x):
    if pd.isna(x): return 'unknown'
    s=re.sub(r'\s+',' ',str(x).strip().lower()).replace('-', '_')
    if s in ('0','1','2','3','4','5'): return 'unmapped_code_'+s
    return ALIASES.get(s, s.replace(' ', '_'))

def load_performance(paths, mode_map=None):
    frames=[]
    for p in paths:
        d=pd.read_csv(p)
        d.columns=[str(c).strip() for c in d.columns]
        rename={'Jobid':'jobid','JobID':'jobid','Access_Mode':'access_mode',
                'Processes_IO':'processes','Run_Time_s':'runtime_s','IO_Time_s':'io_time_s',
                'Bandwidth_Darshan_MiB_s':'bandwidth_mib_s','IO_Total_MiB':'io_mib',
                'Application':'application','Dataset_Group':'dataset_group',
                'Scenario':'scenario','File_Format':'file_format','Nodes':'nodes','NNodes':'nodes','Epochs':'epochs',
                'BatchSize':'batch_size','Transfer_Size':'transfer_size'}
        d=d.rename(columns=rename)
        if 'jobid' not in d: raise ValueError(f'Missing JobID in {p}')
        d['jobid']=pd.to_numeric(d['jobid'],errors='coerce').astype('Int64')
        d['source_performance_csv']=str(p)
        d['access_mode_normalized']=d['access_mode'].map(lambda v: norm_mode(mode_map.get(str(v),v)) if mode_map else norm_mode(v)) if 'access_mode' in d else 'unknown'
        frames.append(d)
    if not frames: return pd.DataFrame()
    d=pd.concat(frames,ignore_index=True)
    for c in ['processes','runtime_s','io_time_s','bandwidth_mib_s','io_mib','epochs','batch_size','nodes']:
        if c in d: d[c]=pd.to_numeric(d[c],errors='coerce')
    return d

def read_dxt(job_dirs):
    results=[]
    for folder in job_dirs:
        folder=Path(folder)
        match=re.search(r'(?:job[_-]?)?(\d{6,})',folder.name)
        if not match: raise ValueError(f'Cannot extract job ID from folder name {folder.name}; use job_1234567')
        jobid=int(match.group(1))
        files=sorted(folder.glob('10_contention_three_cases_pairs*.csv'))
        if not files: raise FileNotFoundError(f'No pair CSV in {folder}')
        pairs=pd.read_csv(files[0],usecols=['case','event_a','event_b','process_a','process_b','overlap_s'])
        diag_files=sorted(folder.glob('10_contention_three_cases_diagnostics*.json'))
        diag=json.loads(diag_files[0].read_text(encoding='utf-8')) if diag_files else {}
        if diag.get('truncated') is True: print(f'WARNING: job {jobid} is truncated; comparison will be excluded')
        total=next((diag[k] for k in ['valid_events','valid_dxt_events','total_valid_events'] if k in diag),np.nan)
        all_ids=set(pairs['event_a'].dropna().tolist()) | set(pairs['event_b'].dropna().tolist())
        row={'jobid':jobid,'truncated':bool(diag.get('truncated',False)),
             'diagnostics_present':bool(diag_files),'valid_events':total,
             'candidate_unique_events':len(all_ids),'candidate_pairs':len(pairs),
             'candidate_fraction':len(all_ids)/total if pd.notna(total) and total>0 else np.nan,
             'source_pairs_csv':str(files[0])}
        for key in CASES:
            sub=pairs[pairs['case']==key]
            row[key+'_pairs']=len(sub)
            row[key+'_unique_events']=len(set(sub['event_a'].dropna()) | set(sub['event_b'].dropna()))
            row[key+'_overlap_median_ms']=float(sub['overlap_s'].median()*1000) if len(sub) else np.nan
        results.append(row)
    return pd.DataFrame(results)

def save_chart(df, x, y, title, path, *, categorical=False):
    fig,ax=plt.subplots(figsize=(9,5))
    d=df.dropna(subset=[x,y]).sort_values(x)
    if d.empty: plt.close(fig);return False
    if categorical: ax.bar(d[x].astype(str),d[y]);ax.tick_params(axis='x',rotation=25)
    else: ax.plot(d[x],d[y],'o-')
    ax.set(xlabel=x.replace('_',' '),ylabel=y.replace('_',' '),title=title)
    ax.grid(axis='y',alpha=.2);fig.tight_layout();fig.savefig(path,dpi=170);plt.close(fig)
    return True



def plot_contention_evidence(merged, out):
    """Readable per-JobID evidence. DXT missing is missing, never zero."""
    out=Path(out)
    available=merged.copy()
    if 'candidate_fraction' not in available:
        return []
    available=available.dropna(subset=['candidate_fraction','jobid'])
    if 'truncated' in available:
        available=available[available['truncated'].ne(True)]
    if available.empty:
        return []
    available=available.drop_duplicates(subset=['jobid']).sort_values('jobid')
    labels=[str(int(j)) for j in available.jobid]
    paths=[]
    fig,ax=plt.subplots(figsize=(max(8,len(available)*.7+3),5.2))
    vals=available.candidate_fraction.astype(float).clip(0,1)*100
    bars=ax.bar(labels,vals,color='#477DB5')
    ax.bar_label(bars,labels=[f'{v:.1f}%' for v in vals],padding=3,fontsize=9)
    ax.set(xlabel='JobID',ylabel='DXT operations involved in candidate overlaps (%)',
           title='DXT Candidate Involvement by JobID')
    ax.set_ylim(0,max(100,float(vals.max())*1.15))
    ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
    fig.text(.5,.015,f'DXT available for {len(available)} of {merged.jobid.nunique()} performance jobs; missing DXT is unknown, not zero.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.055,1,1))
    p=out/'01_dxt_candidate_involvement_by_job.png';fig.savefig(p,dpi=180);plt.close(fig);paths.append(p)
    # performance panels for exactly those jobs, without pretending to establish causation
    metrics=[('io_time_s','Recorded I/O time (s)'),('bandwidth_mib_s','Recorded Darshan bandwidth (MiB/s)'),('runtime_s','Execution time (s)')]
    present=[(c,t) for c,t in metrics if c in available and pd.to_numeric(available[c],errors='coerce').notna().any()]
    if present:
        fig,axes=plt.subplots(len(present),1,figsize=(max(8,len(available)*.7+3),3.3*len(present)),squeeze=False)
        for (col,title),axis in zip(present,axes[:,0]):
            v=pd.to_numeric(available[col],errors='coerce')
            axis.bar(labels,v,color='#0D9488')
            axis.set(ylabel=title,title=title)
            axis.grid(axis='y',alpha=.2);axis.set_axisbelow(True)
        axes[-1,0].set_xlabel('JobID')
        fig.suptitle('Measured Job Performance — DXT-Covered Jobs',fontsize=13)
        fig.text(.5,.012,'Descriptive evidence only; matched baselines and workload equivalence are required to assess degradation.',ha='center',fontsize=9)
        fig.tight_layout(rect=(0,.04,1,.97))
        p=out/'02_performance_of_dxt_covered_jobs.png';fig.savefig(p,dpi=180);plt.close(fig);paths.append(p)
    return paths

def run(perf_paths,job_dirs,out,mode_map=None):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    perf=load_performance(perf_paths,mode_map=mode_map)
    dxt=read_dxt(job_dirs) if job_dirs else pd.DataFrame()
    if not dxt.empty:
        dxt.to_csv(out/'01_dxt_candidate_evidence.csv',index=False)
    if perf.empty: raise ValueError('At least one performance CSV required')
    # Keep only rows with DXT evidence, never silently impute missing candidates.
    merged=perf.merge(dxt,on='jobid',how='left',validate='many_to_one') if not dxt.empty else perf.copy()
    merged.to_csv(out/'02_jobid_evidence_join.csv',index=False)
    plot_contention_evidence(merged,out)
    group_cols=[c for c in ['application','dataset_group','scenario','file_format','epochs','batch_size','transfer_size','nodes'] if c in merged]
    metrics=[c for c in ['io_time_s','bandwidth_mib_s','runtime_s','candidate_fraction'] if c in merged]
    eligible=merged.copy()
    if 'truncated' in eligible: eligible=eligible[eligible['truncated'].ne(True) | eligible['truncated'].isna()]
    # Analysis 2A: modes at fixed process count, same campaign and workload.
    a_keys=group_cols+(['processes'] if 'processes' in eligible else [])
    if 'access_mode_normalized' in eligible:
        a=eligible.groupby(a_keys+['access_mode_normalized'],dropna=False)[metrics].agg(['mean','count'])
        a.columns=['_'.join(c) for c in a.columns]
        a=a.reset_index();a.to_csv(out/'03_analysis_2A_access_modes.csv',index=False)
        for keys,grp in a.groupby(a_keys,dropna=False) if a_keys else [((),a)]:
            if grp['access_mode_normalized'].nunique()<2 or grp['access_mode_normalized'].astype(str).str.startswith('unmapped_code_').any():continue
            for m in metrics:
                save_chart(grp,'access_mode_normalized',m+'_mean',f'Access-mode comparison — {m}',out/f'2A_{m}_{len(list(out.glob("2A_*"))):03d}.png',categorical=True)
    else:a=pd.DataFrame()
    # Analysis 2B: fixed mode, vary process count; do not equate varying nodes with fixed nodes.
    b_keys=group_cols+(['access_mode_normalized'] if 'access_mode_normalized' in eligible else [])
    if 'processes' in eligible:
        b=eligible.groupby(b_keys+['processes'],dropna=False)[metrics].agg(['mean','count'])
        b.columns=['_'.join(c) for c in b.columns]
        b=b.reset_index();b.to_csv(out/'04_analysis_2B_scalability.csv',index=False)
        for keys,grp in b.groupby(b_keys,dropna=False) if b_keys else [((),b)]:
            if grp['processes'].nunique()<2:continue
            for m in metrics:
                if m == 'candidate_fraction' and grp[m+'_count'].fillna(0).lt(2).any(): continue
                save_chart(grp,'processes',m+'_mean',f'I/O scalability — {m}',out/f'2B_{m}_{len(list(out.glob("2B_*"))):03d}.png')
    else:b=pd.DataFrame()
    coverage={'performance_jobs':int(perf.jobid.nunique()),'dxt_jobs':int(dxt.jobid.nunique()) if not dxt.empty else 0,
              'joined_jobs_with_dxt':int(merged['candidate_pairs'].notna().sum()) if 'candidate_pairs' in merged else 0,
              'truncated_jobs_excluded':int(dxt.truncated.sum()) if not dxt.empty else 0,
              'access_modes_observed':sorted(merged.access_mode_normalized.dropna().unique().tolist()),
              'unmapped_access_codes':sorted(v for v in merged.access_mode_normalized.dropna().unique().tolist() if str(v).startswith('unmapped_code_')), 
              'analysis_2A_groups':len(a),'analysis_2B_groups':len(b),
              'interpretation':'Concurrent DXT operations are candidates, not proven degradation. Cross-job comparisons are associations, not causal attribution.',
              'limitations':['Missing DXT for a job means unknown, not zero contention',
                             'Only compare equivalent workloads and storage settings',
                             'Runtime and I/O time are different metrics',
                             'Darshan bandwidth aggregation may differ from application throughput',
                             'For causal validation use matched baselines and repeated runs']}
    (out/'00_coverage_and_limitations.json').write_text(json.dumps(coverage,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(coverage,indent=2,ensure_ascii=False))
    return coverage

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--perf',nargs='+',type=Path,required=True,help='Campaign performance CSVs (module 08)')
    p.add_argument('--dxt-job-dir',nargs='*',type=Path,default=[],help='Folders job_JOBID containing module 10 CSVs')
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--mode-map',type=Path,help='JSON mapping source mode codes to documented access modes')
    a=p.parse_args(argv)
    mode_map=json.loads(a.mode_map.read_text(encoding="utf-8")) if a.mode_map else None
    run(a.perf,a.dxt_job_dir,a.output,mode_map=mode_map)
if __name__=='__main__': main()
