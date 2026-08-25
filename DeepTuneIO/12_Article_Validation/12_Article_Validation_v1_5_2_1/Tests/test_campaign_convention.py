from pathlib import Path
import json, sys

ROOT=Path(__file__).resolve().parents[1]
MOD=ROOT/'Module'
sys.path.insert(0,str(MOD))
from Article_Validation.campaign import article_application_name, discover_results


def test_notebook_uses_standard_campaign_structure():
    nb=json.loads((ROOT/'12_Automatic_Article_Validation.ipynb').read_text(encoding='utf-8'))
    text='\n'.join(''.join(c.get('source',[])) for c in nb['cells'])
    assert '"DeepGalaxy"' in text
    assert '"DLIOv1"' in text
    assert '"HDF5_64bs"' in text
    assert '"NPZ_64bs"' in text
    assert '"TFRecord_256kts_64bs"' in text
    assert '"TFRecord_1mts_64bs"' in text
    assert 'APPLICATION_POS = 1' in text
    assert 'DATASET_POS = 1' in text
    assert 'SCENARIO_POS = 3' in text
    assert 'discover_campaign_tree' not in text


def test_article_application_bridge():
    assert article_application_name('DLIOv1') == 'DLIO'
    assert article_application_name('DeepGalaxy') == 'DeepGalaxy'


def test_canonical_module10_filename_uses_physical_campaign(tmp_path):
    root=tmp_path/'Data'/'DLIOv1'/'HDF5_64bs'/'lustre_ost'
    data=root/'results'/'Figures'/'Performance'/'Data'
    data.mkdir(parents=True)
    expected=data/'performance_grouped_dliov1_hdf5_64bs_lustre_ost_h5_shared.csv'
    expected.write_text('nodes,processes,stripe_count\n1,4,1\n',encoding='utf-8')
    got=discover_results(root,application='DLIOv1',dataset_group='HDF5_64bs',scenario='lustre_ost',file_format='.h5',mode='shared')
    assert got == expected
