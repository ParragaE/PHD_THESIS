#!/usr/bin/env python3
from pathlib import Path
import argparse,sys
ROOT=Path(__file__).resolve().parent
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from Figure_Registry import VERSION,build_registry,save_registry

def main(argv=None):
    p=argparse.ArgumentParser(description='DeepTuneIO — Module 11: Figure Registry')
    p.add_argument('--campaign-root',type=Path,required=True);p.add_argument('--application',required=True);p.add_argument('--dataset-group',required=True);p.add_argument('--scenario',required=True)
    a=p.parse_args(argv);df=build_registry(a.campaign_root,application=a.application,dataset_group=a.dataset_group,scenario=a.scenario);out=a.campaign_root/'results'/'Figure_Registry';files=save_registry(df,out)
    print('='*80);print('DeepTuneIO — Module 11: Figure Registry');print('='*80);print('Version        :',VERSION);print('Application    :',a.application);print('Dataset group  :',a.dataset_group);print('Scenario       :',a.scenario);print('Logical figures:',len(df));print('Mapping status :',df.mapping_status.value_counts().to_dict() if not df.empty else {});print('Provenance     :',df.provenance_status.value_counts().to_dict() if not df.empty else {});print('CSV            :',files[0]);print('Article audit  :',files[3]);print('='*80);return 0
if __name__=='__main__':raise SystemExit(main())
