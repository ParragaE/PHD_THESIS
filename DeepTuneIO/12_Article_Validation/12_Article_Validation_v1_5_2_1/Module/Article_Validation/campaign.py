from __future__ import annotations
from pathlib import Path
import re
import pandas as pd
from .golden_reference import GoldenReference
from .validator import validate_figure
from .reporting import write_validation_reports, write_structural_validation_reports
from .structural_validator import validate_structural_figure, resolve_structural_reference

# Physical DeepTuneIO campaign name -> application name used in Article 01.
# This mapping is intentionally narrow and explicit: it bridges repository identity
# and publication identity without renaming campaign directories.
ARTICLE_APPLICATION_MAP = {
    "DeepGalaxy": "DeepGalaxy",
    "DLIOv1": "DLIO",
}

# Dataset-level publication semantics for Article 01. This does not define the
# physical campaign tree; CAMPAIGNS remains the notebook/source of truth for paths.
# It only prevents scientifically invalid cross-matching when two physical datasets
# share a file format but the article provides exact scalar references for only one.

# Publication terminology -> DeepTuneIO execution/result terminology.
# Article 01 uses "multi" for DLIO independent-file access, while Module 10
# canonicalizes the observed access pattern as "file_per_process".  These are
# different semantic layers and must not be conflated with multi-stripe scope.
ARTICLE_MODE_TO_RESULT_ACCESS_MODE = {
    "DLIOv1": {
        "multi": "file_per_process",
    },
}

def result_access_mode(application: str, article_mode: str) -> str:
    """Map article loading-mode terminology to Module 10 result access mode."""
    return ARTICLE_MODE_TO_RESULT_ACCESS_MODE.get(str(application), {}).get(
        str(article_mode).lower(), str(article_mode)
    )

ARTICLE_DATASET_POLICY = {
    "DLIOv1": {
        "HDF5_64bs": {"exact_scalar_validation": True, "figures": [6]},
        "NPZ_64bs": {"exact_scalar_validation": True, "figures": [7]},
        "TFRecord_256kts_64bs": {"exact_scalar_validation": True, "figures": [8]},
        "TFRecord_1mts_64bs": {"exact_scalar_validation": True, "figures": [9]},
    },
}


def dataset_validation_policy(application: str, dataset_group: str) -> dict:
    return ARTICLE_DATASET_POLICY.get(str(application), {}).get(
        str(dataset_group), {"exact_scalar_validation": True}
    )


def _slug(v):
    return re.sub(r'[^a-z0-9]+', '_', str(v).lower()).strip('_')


def article_application_name(application: str) -> str:
    """Return the application identity used by the article Golden Reference."""
    return ARTICLE_APPLICATION_MAP.get(str(application), str(application))


def infer_filesystem(scenario: str, requested: str = 'auto') -> str:
    if requested and str(requested).lower() != 'auto':
        return str(requested).lower()
    s = str(scenario).lower()
    if 'lustre' in s:
        return 'lustre'
    if 'nfs' in s:
        return 'nfs'
    raise ValueError(f"Cannot infer filesystem from scenario '{scenario}'. Set FILESYSTEM explicitly.")


def resolve_stripe_scope(*, application: str, scenario: str, requested='auto'):
    """Resolve exact or multi-stripe validation scope while preserving campaign semantics.

    DeepGalaxy scenarios encode an exact OST count (lustre_1ost/2ost/4ost).
    DLIOv1 uses the shared physical scenario name ``lustre_ost`` and stores several
    stripe counts inside the same campaign, so automatic scope is unrestricted and
    each Golden Reference row is matched against its own stripe_count.
    """
    if requested is None:
        return None
    if isinstance(requested, (int, float)):
        return None if int(requested) == 0 else int(requested)
    text = str(requested).strip().lower()
    if text in {'all', 'multiple', 'multi', 'none'}:
        return None
    if text not in {'auto', ''}:
        return int(text)

    if str(application) == 'DLIOv1':
        return None

    m = re.search(r'(?<!\d)(\d+)\s*ost', str(scenario).lower())
    return int(m.group(1)) if m else None


def discover_results(campaign_root: Path, *, application, dataset_group, scenario, file_format, mode):
    """Locate Module 10 grouped-performance output for the physical campaign."""
    data = Path(campaign_root) / 'results' / 'Figures' / 'Performance' / 'Data'
    fmt = _slug(str(file_format).lstrip('.'))
    canonical = data / (
        f"performance_grouped_{_slug(application)}_{_slug(dataset_group)}_"
        f"{_slug(scenario)}_{fmt}_{_slug(mode)}.csv"
    )
    if canonical.exists():
        return canonical

    legacy = data / f"performance_grouped_{_slug(mode)}.csv"
    if legacy.exists():
        return legacy

    matches = sorted(data.glob(f"performance_grouped_*_{fmt}_{_slug(mode)}.csv")) if data.exists() else []
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise RuntimeError(
            f"Multiple grouped results match format={fmt}, mode={mode}: " +
            ', '.join(p.name for p in matches)
        )
    raise FileNotFoundError(
        f"No performance grouped result found for application={application}, "
        f"dataset={dataset_group}, scenario={scenario}, mode={mode}. "
        f"Tried: {canonical} ; {legacy}"
    )


def resolve_figures(golden_path: Path, *, article_id, application, filesystem, stripe_count=None, file_format, dataset_group=None):
    """Resolve figures from the Golden Reference for a physical DeepTuneIO application."""
    article_application = article_application_name(application)
    policy = dataset_validation_policy(application, dataset_group) if dataset_group is not None else {"exact_scalar_validation": True}
    if not policy.get("exact_scalar_validation", True):
        return pd.DataFrame(columns=["figure", "data_loading_mode", "stripe_counts"])
    gr = GoldenReference(golden_path)
    d = gr.select(
        article_id=article_id,
        application=article_application,
        filesystem=filesystem,
        stripe_count=stripe_count,
        file_format=file_format,
        scope='figure',
    )
    allowed_figures = policy.get("figures")
    if allowed_figures:
        d = d[pd.to_numeric(d["figure"], errors="coerce").isin([int(x) for x in allowed_figures])].copy()
    if d.empty:
        return pd.DataFrame(columns=['figure', 'data_loading_mode', 'stripe_counts'])
    rows = []
    for (fig, mode), part in d.groupby(['figure', 'data_loading_mode'], dropna=False):
        stripes = sorted(
            pd.to_numeric(part['stripe_count'], errors='coerce')
            .dropna().astype(int).unique().tolist()
        )
        rows.append({
            'figure': int(fig),
            'data_loading_mode': str(mode),
            'stripe_counts': stripes,
        })
    return pd.DataFrame(rows).sort_values('figure').reset_index(drop=True)


def validate_campaign(*, golden_path, campaign_root, article_id, application, dataset_group,
                      scenario, file_format, filesystem, stripe_count=None, output_dir=None, figure_registry=None):
    article_application = article_application_name(application)
    policy = dataset_validation_policy(application, dataset_group)
    reports = []

    # --------------------------------------------------------------
    # Structural/provenance Article 01 access-pattern validation
    # --------------------------------------------------------------
    structural_expected = resolve_structural_reference(application, dataset_group, scenario)
    if not structural_expected.empty:
        detail, structural_context = validate_structural_figure(
            campaign_root=campaign_root, application=application, dataset_group=dataset_group,
            scenario=scenario, file_format=file_format, filesystem=filesystem, article_id=article_id,
            figure_registry=figure_registry,
        )
        if not detail.empty:
            srep = write_structural_validation_reports(
                detail,
                output_dir=output_dir or Path(campaign_root) / 'results' / 'Article_Validation',
                context=structural_context,
            )
            reports.append({
                'figure': int(structural_context['figure']),
                'data_loading_mode': structural_context['data_loading_mode'],
                'result_access_mode': structural_context['data_loading_mode'],
                'stripe_counts': [],
                'validation_family': 'access_pattern',
                'validation_method': 'DXT_STRUCTURAL_AND_PROVENANCE',
                'status': srep['status'],
                'rc': 0 if srep['status'] == 'PASS' else 2,
                **srep,
            })

    # Scalar validation remains unchanged from v1.5.1.
    if not policy.get("exact_scalar_validation", True):
        return reports
    gr = GoldenReference(golden_path)
    resolved = resolve_figures(
        golden_path,
        article_id=article_id,
        application=application,
        filesystem=filesystem,
        stripe_count=stripe_count,
        file_format=file_format,
        dataset_group=dataset_group,
    )
    if resolved.empty:
        # A physical DeepTuneIO campaign may legitimately have no exact scalar
        # reference in the published article (e.g. DeepGalaxy/NFS or DLIO
        # TFRecord 256 KiB, where only ranges/inequalities are reported).
        # This is NOT a validation failure and must not abort campaign execution.
        return reports

    for _, row in resolved.iterrows():
        fig = int(row['figure'])
        article_mode = str(row['data_loading_mode'])
        execution_mode = result_access_mode(application, article_mode)
        refs = gr.select(
            article_id=article_id,
            application=article_application,
            filesystem=filesystem,
            stripe_count=stripe_count,
            file_format=file_format,
            figure=fig,
            mode=article_mode,
            scope='figure',
        )
        result = discover_results(
            campaign_root,
            application=application,
            dataset_group=dataset_group,
            scenario=scenario,
            file_format=file_format,
            mode=execution_mode,
        )
        reference_stripes = sorted(
            pd.to_numeric(refs['stripe_count'], errors='coerce')
            .dropna().astype(int).unique().tolist()
        )
        context = {
            'article_id': article_id,
            'application': application,
            'article_application': article_application,
            'dataset_group': dataset_group,
            'scenario': scenario,
            'file_format': file_format,
            'filesystem': filesystem,
            'stripe_count': stripe_count,
            'reference_stripe_counts': reference_stripes,
            'data_loading_mode': article_mode,
            'result_access_mode': execution_mode,
            'figure': fig,
            'campaign_root': Path(campaign_root),
        }
        detail = validate_figure(refs=refs, results_csv=result, context=context)
        rep = write_validation_reports(
            detail,
            output_dir=output_dir or Path(campaign_root) / 'results' / 'Article_Validation',
            context=context,
            results_source=result,
            golden_reference=golden_path,
        )
        reports.append({
            'figure': fig,
            'data_loading_mode': article_mode,
            'result_access_mode': execution_mode,
            'stripe_counts': reference_stripes,
            'status': rep['status'],
            'rc': 0 if rep['status'] == 'PASS' else 2,
            **rep,
        })
    return reports
