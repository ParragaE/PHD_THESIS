from pathlib import Path
import sys
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]/"Module"
sys.path.insert(0,str(ROOT))
from Article_Validation.reporting import write_validation_reports, MODULE_VERSION

def test_reporting_multistripe(tmp_path):
    d=pd.DataFrame([{"validation_status":"PASS","stripe_count":1},{"validation_status":"PASS","stripe_count":12}])
    ctx=dict(article_id="Article_01",application="DLIO",dataset_group="d",scenario="lustre",file_format="hdf5",filesystem="lustre",stripe_count=None,reference_stripe_counts=[1,12],data_loading_mode="shared",figure=6,campaign_root=tmp_path)
    rep=write_validation_reports(d,output_dir=tmp_path,context=ctx,results_source=tmp_path/"r.csv",golden_reference=tmp_path/"g.csv")
    s=pd.read_csv(rep["summary_csv"])
    assert MODULE_VERSION=="1.5.2.1"
    assert s.iloc[0].stripe_scope=="multiple"
    assert s.iloc[0].reference_stripe_counts=="1;12"
