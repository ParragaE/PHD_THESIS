from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import json
import pandas as pd

SCHEMA = 'DeepTuneIO Report Metadata Standard'
SCHEMA_VERSION = '1.1'
from module_version import MODULE_VERSION


def overall_status(detail):
    st = detail['validation_status'].astype(str) if not detail.empty else pd.Series([], dtype=str)
    if (st == 'ERROR').any(): return 'ERROR'
    if (st == 'FAIL').any(): return 'FAIL'
    if (st == 'MISSING').any(): return 'INCOMPLETE'
    return 'PASS'


def _stripe_metadata(context, detail):
    stripes = context.get('reference_stripe_counts')
    if not stripes and not detail.empty and 'stripe_count' in detail.columns:
        stripes = sorted(pd.to_numeric(detail['stripe_count'], errors='coerce').dropna().astype(int).unique().tolist())
    stripes = [int(x) for x in (stripes or [])]
    exact = stripes[0] if len(stripes) == 1 else None
    scope = str(exact) if exact is not None else ('multiple' if stripes else 'unspecified')
    return exact, stripes, scope


def write_validation_reports(detail: pd.DataFrame, *, output_dir: Path, context: dict,
                             results_source: Path, golden_reference: Path):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    mode = context['data_loading_mode']
    fmt = str(context['file_format']).lower().lstrip('.')
    stem = (
        f"article_01_validation_{context['application']}_{context['dataset_group']}_"
        f"{context['scenario']}_{fmt}_{mode}_fig{int(context['figure'])}"
    )
    dp = output_dir/f'{stem}_detailed.csv'
    sp = output_dir/f'{stem}_summary.csv'
    mp = output_dir/f'{stem}_manifest.json'
    detail.to_csv(dp, index=False)
    counts = {s:int((detail['validation_status']==s).sum()) for s in ['PASS','PASS_PUBLICATION_PRECISION','FAIL','MISSING','ERROR']}
    pass_total = counts['PASS'] + counts['PASS_PUBLICATION_PRECISION']
    status = overall_status(detail)
    exact_stripe, stripes, stripe_scope = _stripe_metadata(context, detail)

    summary = pd.DataFrame([{
        'module_version': MODULE_VERSION,
        'article_id': context['article_id'], 'application': context['application'],
        'article_application': context.get('article_application', context['application']),
        'dataset_group': context['dataset_group'], 'scenario': context['scenario'],
        'file_format': fmt, 'filesystem': context['filesystem'],
        'stripe_count': exact_stripe if exact_stripe is not None else pd.NA,
        'stripe_scope': stripe_scope,
        'reference_stripe_counts': ';'.join(map(str, stripes)),
        'data_loading_mode': mode,
        'result_access_mode': context.get('result_access_mode', mode),
        'article_figure': int(context['figure']),
        'campaign_root': str(context['campaign_root']),
        'checks_total': len(detail), 'checks_pass': pass_total,
        'checks_pass_strict': counts['PASS'],
        'checks_pass_publication_precision': counts['PASS_PUBLICATION_PRECISION'],
        'checks_fail': counts['FAIL'], 'checks_missing': counts['MISSING'],
        'checks_error': counts['ERROR'], 'article_validation_status': status,
    }])
    summary.to_csv(sp, index=False)

    manifest = {
        'schema': SCHEMA, 'schema_version': SCHEMA_VERSION,
        'module': 'DeepTuneIO Article Validation', 'module_version': MODULE_VERSION,
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'article_id': context['article_id'], 'application': context['application'],
        'article_application': context.get('article_application', context['application']),
        'dataset_group': context['dataset_group'], 'scenario': context['scenario'],
        'file_format': fmt, 'filesystem': context['filesystem'],
        'stripe_count': exact_stripe,
        'stripe_scope': stripe_scope,
        'reference_stripe_counts': stripes,
        'data_loading_mode': mode,
        'result_access_mode': context.get('result_access_mode', mode),
        'article_figure': int(context['figure']),
        'campaign_root': str(context['campaign_root']),
        'golden_reference': str(golden_reference), 'results_source': str(results_source),
        'validation_status': status,
        'checks': {'total':len(detail),'pass':pass_total,
                   'pass_strict':counts['PASS'],
                   'pass_publication_precision':counts['PASS_PUBLICATION_PRECISION'],
                   'fail':counts['FAIL'],'missing':counts['MISSING'],'error':counts['ERROR']},
        'tolerances': {'relative_tolerance_pct':1.0,'absolute_tolerance':1e-6,
                       'secondary_rule':'publication_precision_when_metadata_available'},
        'outputs': {'detailed_csv':str(dp),'summary_csv':str(sp)},
    }
    mp.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
    return {'detailed_csv':dp,'summary_csv':sp,'manifest_json':mp,'status':status,'summary':summary}


def write_structural_validation_reports(detail: pd.DataFrame, *, output_dir: Path, context: dict):
    """Write access-pattern structural/provenance validation products."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    fmt = str(context['file_format']).lower().lstrip('.')
    stem = (
        f"article_01_validation_{context['application']}_{context['dataset_group']}_"
        f"{context['scenario']}_{fmt}_access_pattern_fig{int(context['figure'])}_structural"
    )
    dp = output_dir / f"{stem}_detailed.csv"
    sp = output_dir / f"{stem}_summary.csv"
    mp = output_dir / f"{stem}_manifest.json"
    detail.to_csv(dp, index=False)

    statuses = detail['validation_status'].astype(str) if not detail.empty else pd.Series([], dtype=str)
    counts = {s: int((statuses == s).sum()) for s in ['PASS', 'FAIL', 'MISSING', 'ERROR']}
    status = overall_status(detail)
    panels_expected = 4
    panels_observed = int(detail.loc[detail['check'].eq('registry_row_present') & detail['validation_status'].eq('PASS'), 'panel'].nunique()) if not detail.empty else 0

    summary = pd.DataFrame([{
        'module_version': MODULE_VERSION,
        'article_id': context['article_id'],
        'application': context['application'],
        'dataset_group': context['dataset_group'],
        'scenario': context['scenario'],
        'file_format': fmt,
        'filesystem': context['filesystem'],
        'article_figure': int(context['figure']),
        'validation_family': 'access_pattern',
        'validation_method': context['validation_method'],
        'campaign_root': str(context['campaign_root']),
        'panels_expected': panels_expected,
        'panels_observed': panels_observed,
        'checks_total': len(detail),
        'checks_pass': counts['PASS'],
        'checks_fail': counts['FAIL'],
        'checks_missing': counts['MISSING'],
        'checks_error': counts['ERROR'],
        'article_validation_status': status,
    }])
    summary.to_csv(sp, index=False)

    manifest = {
        'schema': SCHEMA,
        'schema_version': SCHEMA_VERSION,
        'module': 'DeepTuneIO Article Validation',
        'module_version': MODULE_VERSION,
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'article_id': context['article_id'],
        'application': context['application'],
        'dataset_group': context['dataset_group'],
        'scenario': context['scenario'],
        'file_format': fmt,
        'filesystem': context['filesystem'],
        'article_figure': int(context['figure']),
        'validation_family': 'access_pattern',
        'validation_method': context['validation_method'],
        'article_expected_semantics': context.get('article_expected_semantics', ''),
        'campaign_root': str(context['campaign_root']),
        'figure_registry': str(context['figure_registry']),
        'validation_status': status,
        'panels': {'expected': panels_expected, 'observed': panels_observed},
        'checks': {
            'total': len(detail), 'pass': counts['PASS'], 'fail': counts['FAIL'],
            'missing': counts['MISSING'], 'error': counts['ERROR'],
        },
        'outputs': {'detailed_csv': str(dp), 'summary_csv': str(sp)},
        'notes': (
            'Structural validation operates on Figure Registry identity, DXT provenance, '
            'normalized event schema and objective access-structure properties. '
            'No pixel comparison or plot digitization is used.'
        ),
    }
    mp.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
    return {'detailed_csv': dp, 'summary_csv': sp, 'manifest_json': mp, 'status': status, 'summary': summary}
