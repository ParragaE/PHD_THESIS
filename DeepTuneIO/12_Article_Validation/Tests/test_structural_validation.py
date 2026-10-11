from pathlib import Path
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parents[1] / 'Module'
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Article_Validation.structural_validator import (
    resolve_structural_reference,
    validate_structural_figure,
)


def _make_job(root: Path, job: int, processes: int, logicals, mode='file_per_process', fmt='tfrecord'):
    d = root / 'results' / 'Figures' / 'Access_Pattern' / f'job_{job}'
    d.mkdir(parents=True, exist_ok=True)
    rows=[]
    for p in range(processes):
        rows.append(dict(job_id=job, process_io=p, temporal_order=p, offset_bytes=p*262144,
                         request_size_bytes=262144, start_time_s=float(p), operation_type='read',
                         file_name=f'f{p}.dat'))
    pd.DataFrame(rows).to_csv(d/'access_pattern_events_normalized.csv', index=False)
    (d/'access_pattern_summary.csv').write_text('x\n1\n', encoding='utf-8')
    dxt = root/'results'/'Access_Pattern_DXT'/'Analysis'/f'x_{job}_dxt_analysis.csv'
    dxt.parent.mkdir(parents=True, exist_ok=True); dxt.write_text('x\n1\n',encoding='utf-8')
    out=[]
    for logical in logicals:
        png=d/f'{logical}.png'; pdf=d/f'{logical}.pdf'; png.write_bytes(b'x'); pdf.write_bytes(b'x')
        out.append(dict(application='DLIOv1',dataset_group='TFRecord_256kts_64bs',scenario='lustre_ost',
                        visualization_family='access_pattern',logical_figure=logical,figure_png=str(png),
                        figure_pdf=str(pdf),source_files=f'{dxt};{d/"access_pattern_events_normalized.csv"};{d/"access_pattern_summary.csv"}',
                        job_ids=str(job),processes=str(processes),data_loading_mode=mode,file_format=fmt,
                        provenance_status='COMPLETE'))
    return out


def test_article_panel_policy_is_3d_plus_process_offset():
    d=resolve_structural_reference('DLIOv1','TFRecord_256kts_64bs','lustre_ost')
    assert list(d.panel)==['a','b','c','d']
    assert list(d.logical_figure)==['01_spatial_temporal_3d','04_spatial_pattern_by_process',
                                    '01_spatial_temporal_3d','04_spatial_pattern_by_process']
    assert list(d.processes)==[4,4,48,48]


def test_structural_validator_passes_reproducible_tfrecord_campaign(tmp_path):
    rows=[]
    rows += _make_job(tmp_path, 1001, 4, ['01_spatial_temporal_3d','04_spatial_pattern_by_process'])
    rows += _make_job(tmp_path, 1002, 48, ['01_spatial_temporal_3d','04_spatial_pattern_by_process'])
    regdir=tmp_path/'results'/'Figure_Registry'; regdir.mkdir(parents=True)
    pd.DataFrame(rows).to_csv(regdir/'figure_registry.csv',index=False)
    detail, context = validate_structural_figure(
        campaign_root=tmp_path, application='DLIOv1', dataset_group='TFRecord_256kts_64bs',
        scenario='lustre_ost', file_format='.tfrecords', filesystem='lustre', article_id='Article_01')
    assert context['figure']==4
    assert not detail.empty
    assert set(detail.validation_status)=={'PASS'}
    assert set(detail.panel)=={'a','b','c','d'}


def test_deepgalaxy_fig10_policy_uses_temporal2d_plus_process_offset():
    d = resolve_structural_reference('DeepGalaxy','DG_bw512_f3c5x64','lustre_1ost')
    assert list(d.panel) == ['a','b','c','d']
    assert list(d.logical_figure) == [
        '03_temporal_pattern','04_spatial_pattern_by_process',
        '03_temporal_pattern','04_spatial_pattern_by_process'
    ]
    assert list(d.processes) == [4,4,64,64]
