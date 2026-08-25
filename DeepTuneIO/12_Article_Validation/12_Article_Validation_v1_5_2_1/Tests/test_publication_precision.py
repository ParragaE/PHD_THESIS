import importlib.util, sys
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
MODULE=ROOT/'Module'
sys.path.insert(0,str(MODULE))
from Article_Validation.validator import validate_figure

def test_fig6_rounding_precision_secondary_pass(tmp_path):
    refs=pd.DataFrame([{
        'figure':6,'panel':'c','nodes':12,'process_io':48,'stripe_count':12,
        'metric':'io_time','unit':'s','reference_value':2.7,
        'publication_decimals':1,'publication_precision_source':'PUBLISHED_TOKEN',
        'source_type':'ARTICLE_TEXT','source_reference':'Fig. 6'
    }])
    results=tmp_path/'r.csv'
    pd.DataFrame([{'nodes':12,'processes':48,'stripe_count':12,'io_time_s_mean':2.6516786}]).to_csv(results,index=False)
    context={'article_id':'Article_01','application':'DLIOv1','article_application':'DLIO',
             'dataset_group':'HDF5_64bs','scenario':'lustre_ost','file_format':'h5',
             'filesystem':'lustre','data_loading_mode':'shared','result_access_mode':'shared',
             'figure':6,'campaign_root':tmp_path}
    d=validate_figure(refs=refs,results_csv=results,context=context)
    assert d.iloc[0]['validation_status']=='PASS_PUBLICATION_PRECISION'
    assert d.iloc[0]['validation_method']=='publication_precision'
    assert d.iloc[0]['rounded_reproduced_value']==2.7
