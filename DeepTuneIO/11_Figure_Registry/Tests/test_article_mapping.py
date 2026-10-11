from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]/'Module'
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from Figure_Registry.registry import map_article01_row

def row(app,dataset,mode,p,logical,family='access_pattern',scenario='lustre_ost'):
    return {'application':app,'dataset_group':dataset,'data_loading_mode':mode,'processes':str(p),'logical_figure':logical,'visualization_family':family,'scenario':scenario,'validation_status':'PENDING'}

def test_dlio_fig2_panels():
    assert map_article01_row(row('DLIOv1','HDF5_64bs','shared',4,'03_temporal_pattern'))['article_panel']=='a'
    assert map_article01_row(row('DLIOv1','HDF5_64bs','shared',4,'04_spatial_pattern_by_process'))['article_panel']=='b'
    assert map_article01_row(row('DLIOv1','HDF5_64bs','shared',48,'03_temporal_pattern'))['article_panel']=='c'
    assert map_article01_row(row('DLIOv1','HDF5_64bs','shared',48,'04_spatial_pattern_by_process'))['article_panel']=='d'

def test_dlio_dataset_figures():
    for ds,mode,fig in [('HDF5_64bs','shared','2'),('NPZ_64bs','file_per_process','3'),('TFRecord_256kts_64bs','file_per_process','4'),('TFRecord_1mts_64bs','file_per_process','5')]:
        x=map_article01_row(row('DLIOv1',ds,mode,4,'03_temporal_pattern'));assert x['article_figure']==fig;assert x['mapping_status']=='MATCHED_RULE';assert x['validation_status']=='PENDING_STRUCTURAL_VALIDATION'

def test_dlio_non_article_process():
    assert map_article01_row(row('DLIOv1','NPZ_64bs','file_per_process',8,'03_temporal_pattern'))['mapping_status']=='NOT_IN_ARTICLE'

def test_deepgalaxy_fig10_regression():
    a=map_article01_row(row('DeepGalaxy','DG_bw512_f3c5x64','shared',4,'03_temporal_pattern','access_pattern','lustre_1ost'))
    d=map_article01_row(row('DeepGalaxy','DG_bw512_f3c5x64','shared',64,'04_spatial_pattern_by_process','access_pattern','lustre_1ost'))
    assert (a['article_figure'],a['article_panel'])==('10','a');assert (d['article_figure'],d['article_panel'])==('10','d')

def test_performance_regression():
    x=map_article01_row({'application':'DeepGalaxy','dataset_group':'DG_bw512_f3c5x64','data_loading_mode':'shared_reload_shuffle','logical_figure':'06_iops_vs_io_time','visualization_family':'performance','scenario':'lustre_4ost','validation_status':'PENDING'})
    assert (x['article_figure'],x['article_panel'],x['mapping_status'])==('16','b','MATCHED_RULE')
