#!/usr/bin/env python3
from __future__ import annotations
import argparse, sys
from pathlib import Path

# Bootstrap this module directory before importing sibling modules.
_MODULE_ROOT = Path(__file__).resolve().parent
if str(_MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(_MODULE_ROOT))

from module_version import MODULE_VERSION
VERSION = MODULE_VERSION


def parse_args(argv=None):
    p = argparse.ArgumentParser(description='DeepTuneIO — Module 12: Automatic Campaign Article Validation')
    p.add_argument('--campaign-root', type=Path, required=True)
    p.add_argument('--golden-reference', type=Path, required=True)
    p.add_argument('--article-id', default='Article_01')
    p.add_argument('--application', required=True)
    p.add_argument('--dataset-group', required=True)
    p.add_argument('--scenario', required=True)
    p.add_argument('--file-format', required=True)
    p.add_argument('--filesystem', default='auto')
    p.add_argument('--stripe-count', default='auto', help="integer, 'auto', or 'all'; DLIO auto uses multi-stripe scope")
    p.add_argument('--module-root', type=Path, default=Path(__file__).resolve().parent)
    p.add_argument('--output-dir', type=Path, default=None)
    p.add_argument('--figure-registry', type=Path, default=None, help='Optional Figure Registry CSV/JSON; auto-discovered when omitted')
    return p.parse_args(argv)


def main(argv=None):
    a = parse_args(argv)
    module_root = a.module_root.resolve()
    if str(module_root) not in sys.path:
        sys.path.insert(0, str(module_root))
    from Article_Validation.campaign import article_application_name, infer_filesystem, resolve_stripe_scope, resolve_figures, validate_campaign, result_access_mode
    from Article_Validation.structural_validator import resolve_structural_reference

    filesystem = infer_filesystem(a.scenario, a.filesystem)
    stripe_scope = resolve_stripe_scope(application=a.application, scenario=a.scenario, requested=a.stripe_count)
    stripe_label = 'MULTIPLE/AUTO' if stripe_scope is None else str(stripe_scope)
    article_application = article_application_name(a.application)

    print('='*80)
    print('DeepTuneIO — Module 12: Automatic Campaign Article Validation')
    print('='*80)
    for k,v in [
        ('Version',VERSION),('Article',a.article_id),('Application',a.application),('Article app',article_application),
        ('Dataset group',a.dataset_group),('Scenario',a.scenario),('File format',a.file_format),
        ('Filesystem',filesystem),('Stripe scope',stripe_label),('Campaign root',a.campaign_root),
        ('Golden reference',a.golden_reference)
    ]:
        print(f'{k:17s}: {v}')
    print('='*80)

    resolved = resolve_figures(
        a.golden_reference, article_id=a.article_id, application=a.application,
        filesystem=filesystem, stripe_count=stripe_scope, file_format=a.file_format, dataset_group=a.dataset_group
    )
    print('\nResolved directly from Golden Reference:')
    resolved_display = resolved.copy()
    if not resolved_display.empty:
        resolved_display = resolved_display.rename(columns={'data_loading_mode':'article_mode'})
        resolved_display['result_access_mode'] = resolved_display['article_mode'].map(
            lambda m: result_access_mode(a.application, m)
        )
        resolved_display = resolved_display[['figure','article_mode','result_access_mode','stripe_counts']]
    print(resolved_display.to_string(index=False))

    structural_resolved = resolve_structural_reference(a.application, a.dataset_group, a.scenario)
    print('\nResolved structural/visual Article references:')
    print(structural_resolved.to_string(index=False))

    if resolved.empty and structural_resolved.empty:
        from Article_Validation.campaign import dataset_validation_policy
        policy = dataset_validation_policy(a.application, a.dataset_group)
        if not policy.get('exact_scalar_validation', True):
            reason = policy.get('reason', 'No exact scalar validation is defined for this dataset.')
        else:
            reason = (
                f'Article {a.article_id} contains no validation-ready scalar references for '
                f'article_application={article_application}, filesystem={filesystem}, '
                f'file_format={a.file_format}, stripe_scope={stripe_scope!r}.'
            )
        print('\n' + '='*80)
        print('CAMPAIGN VALIDATION SUMMARY')
        print('='*80)
        print('Status           : NOT_APPLICABLE / SKIPPED')
        print('Reason           :', reason)
        print('Validation checks: 0')
        print('Return code      : 0')
        return 0

    reps = validate_campaign(
        golden_path=a.golden_reference, campaign_root=a.campaign_root,
        article_id=a.article_id, application=a.application,
        dataset_group=a.dataset_group, scenario=a.scenario,
        file_format=a.file_format, filesystem=filesystem,
        stripe_count=stripe_scope, output_dir=a.output_dir, figure_registry=a.figure_registry
    )
    print('\n' + '='*80)
    print('CAMPAIGN VALIDATION SUMMARY')
    print('='*80)
    rc = 0
    for r in reps:
        s = 'PASS' if r['status']=='PASS' else 'NOT_VALIDATED'
        stripes = ','.join(map(str, r.get('stripe_counts', []))) or '-'
        family = r.get('validation_family', 'performance')
        print(f"Fig. {r['figure']:<3} | family={family:<14} | article={r['data_loading_mode']:<20} | result={r.get('result_access_mode', r['data_loading_mode']):<20} | OST={stripes:<8} | {s} | rc={r['rc']}")
        rc = max(rc, r['rc'])
    return rc


if __name__ == '__main__':
    raise SystemExit(main())
