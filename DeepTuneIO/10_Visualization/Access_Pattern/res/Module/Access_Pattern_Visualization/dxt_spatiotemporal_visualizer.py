"""DeepTuneIO Analyzer — DXT spatial-temporal visualizer.

Parse human-readable `darshan-dxt-parser` output (DXT_POSIX and DXT_MPIIO)
and plot per-rank I/O operations against time, colored by request size.

Usage:
  python dxt_spatiotemporal_visualizer.py trace.dxt --output figure.png --csv operations.csv
  python dxt_spatiotemporal_visualizer.py trace.dxt --operation read --time-max 5

The plot is temporal, not proof of storage contention. Offset is retained
in the CSV for subsequent overlap/contension analysis.
"""
from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D

# Boundaries in bytes. The image's legend omits 1M–4M, so we add it to avoid
# leaving a gap in the classification.
BINS = [
    (100, '0–100 B', '#bb2b15'),
    (1024, '101 B–1 KiB', '#bb680d'),
    (10 * 1024, '1–10 KiB', '#e6b700'),
    (100 * 1024, '10–100 KiB', '#e8e000'),
    (1024**2, '100 KiB–1 MiB', '#83e600'),
    (4 * 1024**2, '1–4 MiB', '#29bf83'),
    (10 * 1024**2, '4–10 MiB', '#00d6ae'),
    (100 * 1024**2, '10–100 MiB', '#04b9dd'),
    (float('inf'), '>100 MiB', '#4754ad'),
]

@dataclass(frozen=True)
class Operation:
    module: str
    rank: int
    operation: str
    offset: int
    length: int
    start: float
    end: float
    file_id: str


def size_bin(length: int):
    for bound, label, color in BINS:
        if length <= bound:
            return label, color
    raise AssertionError('unreachable')


def parse_dxt(text: str) -> list[Operation]:
    """Read standard Darshan DXT text; skip non-segment metadata lines.

    Expected record headers include:
      # DXT, file_id: 123, file_name: /data/file.h5
      # DXT, rank: 0, hostname: node1
      # DXT, write_count: 0, read_count: 2
      # DXT, module: DXT_POSIX
    And segment rows like:
      X_POSIX 0 read 0 4096 1.2 1.3
      X_MPIIO 0 read 0 4096 1.2 1.3
    Some versions use DXT_POSIX / DXT_MPIIO as row prefixes.
    """
    operations = []
    current_rank = None
    current_file = ''
    current_module = None
    # Typical DXT segment: module rank op offset length start end.
    segment = re.compile(
        r'^\s*(?:X_|DXT_)?(POSIX|MPIIO|MPI-IO)\s+'
        r'(-?\d+)\s+(read|write)\s+(-?\d+)\s+(\d+)\s+'
        r'([0-9.eE+-]+)\s+([0-9.eE+-]+)', re.I
    )
    # Alternative Darshan dxt-parser layout with only op offset length start end,
    # under a header that defines module and rank.
    short_segment = re.compile(
        r'^\s*(read|write)\s+(-?\d+)\s+(\d+)\s+'
        r'([0-9.eE+-]+)\s+([0-9.eE+-]+)\s*$', re.I
    )
    for line in text.splitlines():
        file_match = re.search(r'\bfile_(?:id|name)\s*:\s*([^,\s]+)', line, re.I)
        if file_match:
            current_file = file_match.group(1)
        rank_match = re.search(r'\brank\s*:\s*(-?\d+)', line, re.I)
        if rank_match:
            current_rank = int(rank_match.group(1))
        module_match = re.search(r'\bmodule\s*:\s*(?:DXT_|X_)?(POSIX|MPIIO|MPI-IO)', line, re.I)
        if module_match:
            current_module = module_match.group(1).replace('-', '').upper()
        match = segment.match(line)
        if match:
            module, rank, op, offset, length, start, end = match.groups()
            module = module.replace('-', '').upper()
            operations.append(Operation(module, int(rank), op.lower(), int(offset), int(length), float(start), float(end), current_file))
            continue
        match = short_segment.match(line)
        if match and current_rank is not None and current_module is not None:
            op, offset, length, start, end = match.groups()
            operations.append(Operation(current_module, current_rank, op.lower(), int(offset), int(length), float(start), float(end), current_file))
    return [o for o in operations if o.length > 0 and o.end >= o.start]


def plot_operations(operations: list[Operation], output: Path, operation='read', time_max=None,
                    dpi=180, title='DXT · Patrón temporal de E/S'):
    selected = [o for o in operations if operation == 'both' or o.operation == operation]
    if time_max is not None:
        selected = [o for o in selected if o.start <= time_max]
    if not selected:
        raise ValueError('No se encontraron operaciones DXT para los filtros seleccionados.')

    fig, axes = plt.subplots(2, 1, figsize=(15, 8), sharex=True, constrained_layout=True)
    max_rank = max(o.rank for o in selected)
    for ax, module in zip(axes, ['MPIIO', 'POSIX']):
        subset = [o for o in selected if o.module == module]
        for _, label, color in BINS:
            rows = [o for o in subset if size_bin(o.length)[0] == label]
            if rows:
                # Horizontal segments: duration is end-start, y is MPI rank.
                segments = [[(o.start, o.rank), (max(o.end, o.start + 1e-6), o.rank)] for o in rows]
                ax.add_collection(LineCollection(segments, colors=color, linewidths=1.25, alpha=0.88))
        ax.set_ylim(-max(1, max_rank * .05), max_rank + max(1, max_rank * .05))
        ax.set_ylabel('Rank', fontsize=12)
        ax.text(1.005, .5, 'MPI-IO' if module == 'MPIIO' else 'POSIX',
                transform=ax.transAxes, rotation=-90, va='center', fontsize=12)
        ax.grid(True, alpha=.15)
        ax.set_axisbelow(True)
    xmin = min(0, min(o.start for o in selected))
    xmax = time_max if time_max is not None else max(o.end for o in selected)
    axes[-1].set_xlim(xmin, xmax + (xmax == xmin) * 0.001)
    axes[-1].set_xlabel('Tiempo de ejecución (s)', fontsize=13)
    handles = [Line2D([0], [0], color=color, marker='o', linestyle='None', markersize=6, label=label)
               for _, label, color in BINS]
    fig.legend(handles=handles, ncol=5, loc='upper center', bbox_to_anchor=(.5, .97), frameon=False, fontsize=9)
    fig.suptitle(title, fontsize=16, y=1.02)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=dpi, bbox_inches='tight')
    plt.close(fig)


def export_csv(operations: list[Operation], output: Path):
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['module', 'rank', 'operation', 'file_id', 'offset', 'length_bytes',
                         'start_s', 'end_s', 'size_category'])
        for o in operations:
            writer.writerow([o.module, o.rank, o.operation, o.file_id, o.offset, o.length,
                             o.start, o.end, size_bin(o.length)[0]])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('input', type=Path, help='Salida de darshan-dxt-parser (texto)')
    p.add_argument('--output', type=Path, default=Path('dxt_spatiotemporal.png'))
    p.add_argument('--csv', type=Path, help='CSV con las operaciones procesadas')
    p.add_argument('--operation', choices=['read', 'write', 'both'], default='read')
    p.add_argument('--time-max', type=float)
    p.add_argument('--dpi', type=int, default=180)
    args = p.parse_args()
    operations = parse_dxt(args.input.read_text(encoding='utf-8', errors='replace'))
    print(f'Operaciones DXT extraídas: {len(operations)}')
    if args.csv:
        export_csv(operations, args.csv)
        print(f'CSV: {args.csv}')
    plot_operations(operations, args.output, args.operation, args.time_max, args.dpi)
    print(f'Figura: {args.output}')

if __name__ == '__main__':
    main()
