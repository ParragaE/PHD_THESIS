from __future__ import annotations
from pathlib import Path
import math
from decimal import Decimal, ROUND_HALF_UP
import pandas as pd

from module_version import MODULE_VERSION
RELATIVE_TOLERANCE_PCT=1.0
ABSOLUTE_TOLERANCE=1e-6
METRIC_COLUMNS={
    'bandwidth':'bandwidth_mib_s_mean',
    'iops':'iops_mean',
    'io_time':'io_time_s_mean',
}

def _norm_fmt(v):
    x=str(v).strip().lower().lstrip('.')
    return {'h5':'hdf5','hdf':'hdf5','tfrecords':'tfrecord'}.get(x,x)

def _match_result_row(results, ref):
    d=results.copy()
    if 'nodes' in d: d=d[pd.to_numeric(d['nodes'],errors='coerce').eq(int(ref['nodes']))]
    if 'processes' in d: d=d[pd.to_numeric(d['processes'],errors='coerce').eq(int(ref['process_io']))]
    if 'stripe_count' in d and pd.notna(ref.get('stripe_count')):
        d=d[pd.to_numeric(d['stripe_count'],errors='coerce').eq(int(ref['stripe_count']))]
    return d



def _passes_publication_precision(value, reference, decimals):
    if pd.isna(decimals):
        return False, None
    try:
        d = int(decimals)
        quantum = Decimal("1").scaleb(-d)
        rounded = Decimal(str(float(value))).quantize(quantum, rounding=ROUND_HALF_UP)
        published = Decimal(str(float(reference))).quantize(quantum, rounding=ROUND_HALF_UP)
        return rounded == published, float(rounded)
    except Exception:
        return False, None


def validate_figure(*, refs: pd.DataFrame, results_csv: Path, context: dict):
    results_csv=Path(results_csv)
    if not results_csv.exists():
        raise FileNotFoundError(f"Performance grouped CSV not found: {results_csv}")
    results=pd.read_csv(results_csv)
    records=[]
    base={
        'article_id':context['article_id'],'application':context['application'],
        'article_application':context.get('article_application', context['application']),
        'dataset_group':context['dataset_group'],'scenario':context['scenario'],
        'file_format':_norm_fmt(context['file_format']),'filesystem':context['filesystem'],
        'data_loading_mode':context['data_loading_mode'],
        'result_access_mode':context.get('result_access_mode', context['data_loading_mode']),
        'article_figure':int(context['figure']),'campaign_root':str(context['campaign_root']),
        'module_version':MODULE_VERSION,
    }
    for _,ref in refs.iterrows():
        metric=str(ref['metric']); col=METRIC_COLUMNS.get(metric)
        rec={**base,
             'figure':int(ref['figure']),'panel':ref.get('panel',''),
             'nodes':int(ref['nodes']),'process_io':int(ref['process_io']),
             'stripe_count':int(ref['stripe_count']) if pd.notna(ref.get('stripe_count')) else pd.NA,
             'metric':metric,'unit':ref.get('unit',''),
             'reference_value':float(ref['reference_value']),
             'publication_decimals':ref.get('publication_decimals', pd.NA),
             'publication_precision_source':ref.get('publication_precision_source',''),
             'reproduced_value':math.nan,'absolute_error':math.nan,'relative_error_pct':math.nan,
             'relative_tolerance_pct':RELATIVE_TOLERANCE_PCT,
             'absolute_tolerance':ABSOLUTE_TOLERANCE,'metric_column':col or '',
             'source_type':ref.get('source_type',''),'source_reference':ref.get('source_reference',''),
             'results_source':str(results_csv),'validation_method':'','rounded_reproduced_value':math.nan,
             'validation_status':'ERROR','validation_notes':''}
        if not col or col not in results.columns:
            rec['validation_notes']=f"Required reproduced metric column not found: {col}"
            records.append(rec); continue
        matched=_match_result_row(results,ref)
        if matched.empty:
            rec['validation_status']='MISSING'
            rec['validation_notes']='No reproduced row matched the expected experimental configuration.'
            records.append(rec); continue
        if len(matched)>1:
            rec['validation_status']='ERROR'
            rec['validation_notes']=f"Multiple reproduced rows matched configuration ({len(matched)})."
            records.append(rec); continue
        value=pd.to_numeric(matched.iloc[0][col],errors='coerce')
        if pd.isna(value):
            rec['validation_status']='ERROR'; rec['validation_notes']=f"Reproduced metric is NaN: {col}"
            records.append(rec); continue
        refv=float(ref['reference_value']); val=float(value)
        ae=abs(val-refv)
        re_pct=(ae/abs(refv)*100.0) if refv != 0 else (0.0 if ae<=ABSOLUTE_TOLERANCE else math.inf)
        passed=(ae<=ABSOLUTE_TOLERANCE) or (re_pct<=RELATIVE_TOLERANCE_PCT)
        if passed:
            rec.update(reproduced_value=val, absolute_error=ae, relative_error_pct=re_pct,
                       validation_method='strict_tolerance', validation_status='PASS')
        else:
            precision_pass, rounded_value = _passes_publication_precision(
                val, refv, ref.get('publication_decimals', pd.NA)
            )
            if precision_pass:
                rec.update(
                    reproduced_value=val, absolute_error=ae, relative_error_pct=re_pct,
                    rounded_reproduced_value=rounded_value,
                    validation_method='publication_precision',
                    validation_status='PASS_PUBLICATION_PRECISION',
                    validation_notes=(
                        f"Strict relative error {re_pct:.6f}% exceeds {RELATIVE_TOLERANCE_PCT:.6f}%, "
                        f"but the reproduced value rounds to the published value using "
                        f"{int(ref.get('publication_decimals'))} decimal place(s)."
                    ),
                )
            else:
                rec.update(reproduced_value=val, absolute_error=ae, relative_error_pct=re_pct,
                           validation_method='strict_tolerance', validation_status='FAIL')
        records.append(rec)
    return pd.DataFrame(records)
