from __future__ import annotations
from pathlib import Path
from typing import Iterable, Optional
import pandas as pd


class GoldenReference:
    def __init__(self, path: Path):
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"Golden reference not found: {self.path}")
        self.df = pd.read_csv(self.path)

    @staticmethod
    def _norm_fmt(v):
        x = str(v).strip().lower().lstrip('.')
        return {'h5':'hdf5','hdf':'hdf5','tfrecords':'tfrecord'}.get(x, x)

    @staticmethod
    def _stripe_filter(series: pd.Series, stripe_count):
        """Return a mask for an exact, multiple or unrestricted stripe scope.

        stripe_count may be:
          - None / 'all' / 'auto' / 0: do not constrain stripe_count;
          - an integer: exact stripe_count;
          - an iterable of integers: any listed stripe_count.
        """
        values = pd.to_numeric(series, errors='coerce')
        if stripe_count is None:
            return pd.Series(True, index=series.index)
        if isinstance(stripe_count, str) and stripe_count.strip().lower() in {'', 'all', 'auto', 'multiple', 'multi'}:
            return pd.Series(True, index=series.index)
        if isinstance(stripe_count, (int, float)) and int(stripe_count) == 0:
            return pd.Series(True, index=series.index)
        if isinstance(stripe_count, Iterable) and not isinstance(stripe_count, (str, bytes)):
            allowed = {int(x) for x in stripe_count}
            return values.isin(allowed)
        return values.eq(int(stripe_count))

    def select(self, *, article_id, application, filesystem, stripe_count=None, file_format,
               figure=None, mode=None, scope='figure'):
        d = self.df.copy()
        mask = (
            d['article_id'].astype(str).eq(str(article_id)) &
            d['application'].astype(str).str.lower().eq(str(application).lower()) &
            d['filesystem'].astype(str).str.lower().eq(str(filesystem).lower()) &
            self._stripe_filter(d['stripe_count'], stripe_count) &
            d['file_format'].map(self._norm_fmt).eq(self._norm_fmt(file_format))
        )
        d = d.loc[mask].copy()
        if figure is not None:
            d = d[pd.to_numeric(d['figure'], errors='coerce').eq(int(figure))]
        if mode is not None:
            d = d[d['data_loading_mode'].astype(str).str.lower().eq(str(mode).lower())]
        if 'validation_ready' in d.columns:
            ready = d['validation_ready']
            if ready.dtype != bool:
                ready = ready.astype(str).str.lower().isin(['true','1','yes'])
            d = d[ready]
        if scope == 'figure':
            # Figure validation uses explicit article prose or explicit numeric labels printed on figures; tables remain independent.
            d = d[d['source_type'].astype(str).isin(['ARTICLE_TEXT','ARTICLE_FIGURE'])]
            # Article 01 automatic figure validation currently validates the three
            # common performance metrics reconstructed by Module 10.
            d = d[d['metric'].astype(str).isin(['bandwidth','iops','io_time'])]
        return d.reset_index(drop=True)
