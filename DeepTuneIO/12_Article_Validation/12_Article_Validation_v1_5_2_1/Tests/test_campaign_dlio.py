from pathlib import Path
import sys
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]/"Module"
sys.path.insert(0,str(ROOT))
from Article_Validation.golden_reference import GoldenReference
from Article_Validation.campaign import article_application_name, resolve_figures, resolve_stripe_scope
from Article_Validation.validator import validate_figure


def _golden(tmp_path):
    rows=[]
    for stripe,nodes,procs,val in [(1,1,4,100.0),(12,12,48,200.0)]:
        for metric in ["bandwidth","iops","io_time"]:
            rows.append(dict(article_id="Article_01",figure=6,panel="a",application="DLIO",filesystem="lustre",stripe_count=stripe,file_format="hdf5",data_loading_mode="shared",nodes=nodes,process_io=procs,metric=metric,reference_value=val,unit="x",source_type="ARTICLE_TEXT",validation_ready=True))
    p=tmp_path/"g.csv"; pd.DataFrame(rows).to_csv(p,index=False); return p

def test_article_application_mapping():
    assert article_application_name("DLIOv1") == "DLIO"
    assert article_application_name("DeepGalaxy") == "DeepGalaxy"


def test_dlio_auto_is_multistripe():
    assert resolve_stripe_scope(application="DLIOv1",scenario="lustre_ost",requested="auto") is None
    assert resolve_stripe_scope(application="DeepGalaxy",scenario="lustre_4ost",requested="auto") == 4

def test_dlio_figure_resolution_across_stripes(tmp_path):
    g=_golden(tmp_path)
    r=resolve_figures(g,article_id="Article_01",application="DLIOv1",filesystem="lustre",stripe_count=None,file_format=".h5")
    assert r.iloc[0].figure == 6
    assert r.iloc[0].data_loading_mode == "shared"
    assert r.iloc[0].stripe_counts == [1,12]

def test_validator_matches_reference_specific_stripe(tmp_path):
    g=_golden(tmp_path)
    refs=GoldenReference(g).select(article_id="Article_01",application="DLIO",filesystem="lustre",stripe_count=None,file_format="hdf5",figure=6,mode="shared",scope="figure")
    result=pd.DataFrame([
        dict(nodes=1,processes=4,stripe_count=1,bandwidth_mib_s_mean=100,iops_mean=100,io_time_s_mean=100),
        dict(nodes=12,processes=48,stripe_count=12,bandwidth_mib_s_mean=200,iops_mean=200,io_time_s_mean=200),
    ])
    rp=tmp_path/"r.csv"; result.to_csv(rp,index=False)
    d=validate_figure(refs=refs,results_csv=rp,context=dict(article_id="Article_01",application="DLIOv1",article_application="DLIO",dataset_group="HDF5_64bs",scenario="lustre_ost",file_format=".h5",filesystem="lustre",data_loading_mode="shared",figure=6,campaign_root=tmp_path,stripe_count=None))
    assert len(d)==6
    assert set(d.validation_status)=={"PASS"}
    assert sorted(d.stripe_count.unique().tolist())==[1,12]

def test_tfrecord_256k_has_no_exact_scalar_figure(tmp_path):
    g=_golden(tmp_path)
    r=resolve_figures(
        g, article_id="Article_01", application="DLIOv1", filesystem="lustre",
        stripe_count=None, file_format=".tfrecords", dataset_group="TFRecord_256kts_64bs"
    )
    assert r.empty
