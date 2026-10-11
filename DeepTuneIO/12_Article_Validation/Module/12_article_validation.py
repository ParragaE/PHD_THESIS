#!/usr/bin/env python3
from __future__ import annotations
import argparse,sys
from pathlib import Path
from module_version import MODULE_VERSION
VERSION=MODULE_VERSION
def main(argv=None):
 p=argparse.ArgumentParser(); p.add_argument('--campaign-root',type=Path,required=True); p.add_argument('--golden-reference',type=Path,required=True); p.add_argument('--article-id',default='Article_01'); p.add_argument('--application',required=True); p.add_argument('--dataset-group',required=True); p.add_argument('--scenario',required=True); p.add_argument('--file-format',required=True); p.add_argument('--filesystem',required=True); p.add_argument('--stripe-count',type=int,required=True); p.add_argument('--figure',type=int,required=True); p.add_argument('--data-loading-mode',required=True); p.add_argument('--module-root',type=Path,default=Path(__file__).resolve().parent)
 a=p.parse_args(argv); sys.path.insert(0,str(a.module_root.resolve())) if str(a.module_root.resolve()) not in sys.path else None
 from Article_Validation.golden_reference import GoldenReference
 from Article_Validation.campaign import article_application_name, discover_results
 from Article_Validation.validator import validate_figure
 from Article_Validation.reporting import write_validation_reports
 article_application=article_application_name(a.application); gr=GoldenReference(a.golden_reference); refs=gr.select(article_id=a.article_id,application=article_application,filesystem=a.filesystem,stripe_count=a.stripe_count,file_format=a.file_format,figure=a.figure,mode=a.data_loading_mode,scope='figure')
 result=discover_results(a.campaign_root,application=a.application,dataset_group=a.dataset_group,scenario=a.scenario,file_format=a.file_format,mode=a.data_loading_mode)
 c={'article_id':a.article_id,'application':a.application,'article_application':article_application,'dataset_group':a.dataset_group,'scenario':a.scenario,'file_format':a.file_format,'filesystem':a.filesystem,'stripe_count':a.stripe_count,'data_loading_mode':a.data_loading_mode,'figure':a.figure,'campaign_root':a.campaign_root}
 d=validate_figure(refs=refs,results_csv=result,context=c); rep=write_validation_reports(d,output_dir=a.campaign_root/'results'/'Article_Validation',context=c,results_source=result,golden_reference=a.golden_reference); print(rep['summary'].to_string(index=False)); return 0 if rep['status']=='PASS' else 2
if __name__=='__main__': raise SystemExit(main())
