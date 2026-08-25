from pathlib import Path
import sys,pandas as pd
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'Module'))
from Article_Validation.validator import validate_figure

def test_fig16_correct_values_pass(tmp_path):
    refs=pd.DataFrame([
      {'figure':16,'panel':'a','nodes':1,'process_io':4,'stripe_count':4,'metric':'io_time','unit':'s','reference_value':54.35,'source_type':'ARTICLE_TEXT','source_reference':'Fig16'},
      {'figure':16,'panel':'a','nodes':16,'process_io':64,'stripe_count':4,'metric':'io_time','unit':'s','reference_value':24.31,'source_type':'ARTICLE_TEXT','source_reference':'Fig16'},])
    r=pd.DataFrame([{'nodes':1,'processes':4,'stripe_count':4,'io_time_s_mean':54.345699},{'nodes':16,'processes':64,'stripe_count':4,'io_time_s_mean':24.305551}]); p=tmp_path/'r.csv'; r.to_csv(p,index=False)
    c={'article_id':'Article_01','application':'DeepGalaxy','dataset_group':'DG','scenario':'lustre_4ost','file_format':'hdf5','filesystem':'lustre','stripe_count':4,'data_loading_mode':'shared_reload_shuffle','figure':16,'campaign_root':tmp_path}
    d=validate_figure(refs=refs,results_csv=p,context=c); assert (d.validation_status=='PASS').all()
