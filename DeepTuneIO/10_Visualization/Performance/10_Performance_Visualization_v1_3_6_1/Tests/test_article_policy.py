import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FILE=ROOT/'Module'/'10_performance_visualization.py'
spec=importlib.util.spec_from_file_location('m10',FILE)
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

def _args(app):
    return m.parse_args(['--application',app,'--dataset-group','x','--scenario','x','--file-format','.x','--analysis-scope','article','--profile','auto','--iops-column','auto'])

def test_dlio_article_policy():
    cfg, profile, iops, preset=m.resolve_reproduction_policy(_args('DLIOv1'))
    assert cfg is None
    assert profile=='bar'
    assert iops=='iops_ds_legacy'

def test_deepgalaxy_article_policy():
    cfg, profile, iops, preset=m.resolve_reproduction_policy(_args('DeepGalaxy'))
    assert cfg is None
    assert profile=='dual'
    assert iops=='iops_ds_legacy'

def test_general_scope_is_not_article_filtered():
    a=m.parse_args(['--application','DLIOv1','--dataset-group','x','--scenario','x','--file-format','.x','--analysis-scope','all','--profile','auto','--iops-column','iops_posix'])
    cfg, profile, iops, preset=m.resolve_reproduction_policy(a)
    assert cfg is None and profile=='all' and iops=='iops_posix' and preset is None


def test_explicit_article_filter_is_respected():
    a=m.parse_args(['--application','DeepGalaxy','--dataset-group','x','--scenario','x','--file-format','.x','--analysis-scope','article','--profile','auto','--iops-column','auto','--configuration-filter','1x4,16x64'])
    cfg, profile, iops, preset=m.resolve_reproduction_policy(a)
    assert cfg == [(1,4),(16,64)]
    assert profile == 'dual'
    assert iops == 'iops_ds_legacy'
