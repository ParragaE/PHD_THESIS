"""Direct integration with the existing Access_Pattern DXT detector."""
from pathlib import Path
import json
import pandas as pd
from Access_Pattern_Visualization.processor import prepare_access_pattern
from Access_Pattern_Visualization.plotting import analyze_potential_contention
from contention_heatmaps import heatmap_with_marginals, process_matrix


def run_contention(*, campaign_root, application, dataset_group, scenario, file_format,
                   job_id, operation='read', access_mode='auto', case='AB', process=None,
                   file=None, time_bins=50, offset_bins=40, max_pairs=200000,
                   min_overlap_s=0.0, resource_mode='auto', output_dir=None):
    if job_id is None:
        raise ValueError('Indica un JobID: no se mezclan offsets de trabajos diferentes.')
    root = Path(campaign_root).expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f'No existe la carpeta de campaña: {root}')
    output = Path(output_dir) if output_dir else root/'results'/'Figures'/'Contention_Analysis'/f'job_{job_id}'
    output.mkdir(parents=True, exist_ok=True)
    dataset = prepare_access_pattern(campaign_root=root, application=application,
             dataset_group=dataset_group, scenario=scenario, file_format=file_format,
             job_id=int(job_id), operation=operation, access_mode=access_mode, max_events=None)
    events = dataset.events
    if events.empty:
        raise ValueError(f'No se encontraron eventos DXT para JobID {job_id}')
    if 'job_id' in events:
        jobs = set(pd.to_numeric(events['job_id'], errors='coerce').dropna().astype(int))
        if jobs != {int(job_id)}:
            raise ValueError(f'La selección incluye otros JobIDs: {sorted(jobs)}')
    # Export the EXACT normalized event table used by the detector, for provenance.
    events.to_csv(output/'contention_input_events.csv', index=False)
    analyze_potential_contention(events, output, min_overlap_s=min_overlap_s,
            max_pairs=max_pairs, resource_mode=resource_mode, scenario=scenario,
            meta=dataset.metadata)
    pairs_path = output/'10_contention_three_cases_pairs.csv'
    if not pairs_path.is_file():
        raise RuntimeError(f'El detector no generó {pairs_path}. Revisa los eventos DXT y los diagnósticos.')
    pairs = pd.read_csv(pairs_path)
    report = json.loads((output/'10_contention_three_cases_diagnostics.json').read_text(encoding='utf-8'))
    figures = []
    if case != 'C_shared_resource':
        figures.extend(heatmap_with_marginals(pairs, events, output, case=case,
             process=process, file=file, time_bins=time_bins,
             offset_bins=offset_bins, max_pairs=max_pairs, jobid=job_id))
    matrix = process_matrix(pairs, output, case=case, process=process, jobid=job_id)
    if matrix: figures.append(matrix)
    return {'figures': figures, 'output_dir': output, 'diagnostics': report,
            'source_files': [str(p) for p in dataset.source_files],
            'event_count': len(events), 'pair_count': len(pairs)}
