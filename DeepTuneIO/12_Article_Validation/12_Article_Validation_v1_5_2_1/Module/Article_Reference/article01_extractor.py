from __future__ import annotations
import re
import pandas as pd
import math

EXTRACTOR_VERSION = "1.1.1"

def _num(value):
    if value is None:
        return None
    return float(str(value).replace(",", ""))

def _row(
    *,
    figure,
    panel,
    application,
    filesystem,
    stripe_count,
    file_format,
    data_loading_mode,
    nodes,
    process_io,
    metric,
    value,
    unit,
    source_type,
    source_page,
    source_section,
    source_reference,
    evidence_text,
):
    return {
        "article_id": "Article_01",
        "figure": figure,
        "panel": panel,
        "application": application,
        "filesystem": filesystem,
        "stripe_count": stripe_count,
        "file_format": file_format,
        "data_loading_mode": data_loading_mode,
        "nodes": nodes,
        "process_io": process_io,
        "metric": metric,
        "reference_value": value,
        "unit": unit,
        "source_type": source_type,
        "source_page": source_page,
        "source_section": source_section,
        "source_reference": source_reference,
        "evidence_text": evidence_text,
        "validation_ready": True,
    }

def _search(pattern, text, flags=re.I):
    m = re.search(pattern, text, flags)
    return m


def _normalize_pdf_text(text):
    """Normalize born-digital PDF text before applying article regexes.

    The published PDF contains non-breaking spaces, typographic dashes and
    words split at line endings (e.g. ``configura-\ntion`` or ``shuf-\nfle``).
    These are extraction artifacts, not scientific content.  Normalization is
    deliberately lexical only: it never changes, inserts or estimates numeric
    values.
    """
    if text is None:
        return ""
    x = str(text)
    x = x.replace("\u00a0", " ")
    x = x.replace("\u2013", "-").replace("\u2014", "-").replace("\u2212", "-")
    # Rejoin alphabetic words split by PDF line wrapping. Preserve genuine
    # numeric/configuration hyphens such as 1N-4P-1OST.
    x = re.sub(r"(?<=[A-Za-z])-[ \t]*\n[ \t]*(?=[A-Za-z])", "", x)
    x = re.sub(r"\s+", " ", x).strip()
    return x

def extract_deepgalaxy_figures(pages):
    """
    Extract explicit endpoint values for Figures 11-16 from article prose.

    Values are extracted from the PDF text. No plot digitization,
    interpolation, or estimation is performed.
    """
    rows = []
    audit = []

    specs = [
        # figure, stripe, mode, pages, io_start, io_end page patterns etc.
        (11, 1, "shared", [41,42]),
        (12, 1, "shared_reload_shuffle", [42]),
        (13, 2, "shared", [42,43]),
        (14, 2, "shared_reload_shuffle", [43,44]),
        (15, 4, "shared", [44]),
        (16, 4, "shared_reload_shuffle", [44,45]),
    ]

    allpages = {x["page"]: _normalize_pdf_text(x["text"]) for x in pages}

    # Explicit known sentence structures for each figure.
    patterns = {
        11: {
            "io_time": (
                r"1 node and 4 processes, I/O time is ([\d,.]+) s.*?"
                r"16 nodes and 64 processes, this metric improves to ([\d,.]+) s",
                "a"
            ),
            "bandwidth": (
                r"Bandwidth follows a similar trend, increasing from ([\d,.]+) MiB/s.*?"
                r"to .*?([\d,.]+) MiB/s in the largest",
                "a"
            ),
            "iops": (
                r"1-node, 4-process configuration, IOPS reach ([\d,.]+), while in the "
                r"16-node, 64-process configuration, this value rises to ([\d,.]+)",
                "b"
            ),
        },
        12: {
            "io_time": (
                r"1 node and 4 processes, the I/O time is ([\d,.]+) s.*?"
                r"16 nodes and 64 processes, this time drops to ([\d,.]+) s",
                "a"
            ),
            "bandwidth": (
                r"smallest configuration \(1 node, 4 processes\), the bandwidth is ([\d,.]+) MiB/s, "
                r"increasing to ([\d,.]+) MiB/s in the largest configuration",
                "a"
            ),
            "iops": (
                r"IOPS rises from ([\d,.]+) in the 1-node setup to ([\d,.]+) in the 16-node setup",
                "b"
            ),
        },
        13: {
            "io_time": (
                r"initial configuration with 1 node and 4 processes, the I/O time is ([\d,.]+) s.*?"
                r"16 nodes and 64 processes, this metric decreases to ([\d,.]+) s",
                "a"
            ),
            "bandwidth": (
                r"1-node, 4-process configuration, the recorded bandwidth is ([\d,.]+) MiB/s, while "
                r"in the 16-node, 64-process configuration it rises to ([\d,.]+) MiB/s",
                "a"
            ),
            "iops": (
                r"IOPS improve with increased resources, rising from ([\d,.]+) IOPS to ([\d,.]+) IOPS",
                "b"
            ),
        },
        14: {
            "io_time": (
                r"initial configuration with 1 node and 4 processes, the I/O time is ([\d,.]+) s.*?"
                r"16 nodes and 64 processes reduces this time to ([\d,.]+) s",
                "a"
            ),
            "bandwidth": (
                r"1-node, 4-process configuration, the bandwidth is ([\d,.]+) MiB/s, which increases "
                r"to ([\d,.]+) MiB/s in the 16-node, 64-process setup",
                "a"
            ),
            "iops": (
                r"IOPS increases notably, rising from ([\d,.]+) to ([\d,.]+)",
                "b"
            ),
        },
        15: {
            "io_time": (
                r"configuration with 1 node and 4 processes, the I/O time is ([\d,.]+) s.*?"
                r"16 nodes and 64 processes reduces .*?this metric to ([\d,.]+) s",
                "a"
            ),
            "bandwidth": (
                r"1-node, 4-process configuration, the recorded bandwidth is ([\d,.]+) MiB/s, which "
                r"rises to ([\d,.]+) MiB/s with 16 nodes and 64 processes",
                "a"
            ),
            "iops": (
                r"IOPS increases from ([\d,.]+) to ([\d,.]+)",
                "b"
            ),
        },
        16: {
            "io_time": (
                r"with 1 node and 4 processes, the I/O time is ([\d,.]+) s.*?"
                r"16 nodes and 64 processes reduces .*?this metric to ([\d,.]+) s",
                "a"
            ),
            "bandwidth": (
                r"1-node, 4-process configuration, bandwidth reaches ([\d,.]+) MiB/s, rising "
                r"to ([\d,.]+) MiB/s with 16 nodes and 64 processes",
                "a"
            ),
            "iops": (
                r"IOPS shows a significant increase, rising from ([\d,.]+) to ([\d,.]+)",
                "b"
            ),
        },
    }

    units = {"io_time":"s", "bandwidth":"MiB/s", "iops":"IOPS"}

    for fig, stripe, mode, pnos in specs:
        text = " ".join(allpages.get(p, "") for p in pnos)

        # Figure 16 immediately follows Figure 15 in the article.  Its original
        # I/O-time sentence has the same grammatical form as the Figure 15
        # sentence, so searching both pages without context can associate the
        # Figure 15 values with Figure 16.  Scope ONLY Figure 16 to its explicit
        # shared(reload+shuffle) subsection.  No numeric value is encoded here.
        if fig == 16:
            marker = re.search(
                r"Shared\s*\(\s*reload\s*\+\s*shuffle\s*\)\s*Access\s*Mode",
                text,
                re.I | re.S,
            )
            if marker:
                text = text[marker.start():]

        for metric, (pattern, panel) in patterns[fig].items():
            m = _search(pattern, text, re.I | re.S)
            if not m:
                audit.append({
                    "figure": fig,
                    "element": metric,
                    "status": "NOT_EXTRACTED",
                    "reason": "Expected explicit prose pattern not found.",
                    "source_pages": ",".join(map(str,pnos)),
                })
                continue

            start, end = _num(m.group(1)), _num(m.group(2))
            # Locate the first page that contains at least one captured value.
            source_page = next(
                (p for p in pnos if str(m.group(1)).replace(",", "")[:4] in allpages.get(p,"").replace(",","")),
                pnos[0]
            )
            evidence = m.group(0)

            for nodes, procs, value in [(1,4,start), (16,64,end)]:
                rows.append(_row(
                    figure=fig,
                    panel=panel,
                    application="DeepGalaxy",
                    filesystem="lustre",
                    stripe_count=stripe,
                    file_format="hdf5",
                    data_loading_mode=mode,
                    nodes=nodes,
                    process_io=procs,
                    metric=metric,
                    value=value,
                    unit=units[metric],
                    source_type="ARTICLE_TEXT",
                    source_page=source_page,
                    source_section="4.6.1",
                    source_reference=f"Article 01, Sec. 4.6.1, Fig. {fig}",
                    evidence_text=evidence,
                ))
            audit.append({
                "figure": fig,
                "element": metric,
                "status": "EXTRACTED",
                "reason": "",
                "source_pages": ",".join(map(str,pnos)),
            })

    return rows, audit


def extract_deepgalaxy_tables(pages):
    """
    Extract Tables 11 and 12.

    These tables provide 1N-4P and 16N-64P references for 1/2/4 OST,
    including runtime and memory. Table values are less precise for IOPS
    than the prose, so duplicate-key resolution later prefers ARTICLE_TEXT.
    """
    rows = []
    audit = []
    page_map = {x["page"]: _normalize_pdf_text(x["text"]) for x in pages}

    table_specs = [
        (11, 46, "shared", {
            1: [(1,4,11.21,26808.03,187.43,48112,90),
                (16,64,5.80,2792.90,400.50,117211,643)],
            2: [(1,4,12.26,31389.29,159.20,40866,89),
                (16,64,7.10,2538.88,325.87,95359,641)],
            4: [(1,4,8.13,28736.68,251.88,64654,89),
                (16,64,6.59,2789.80,348.38,101945,633)],
        }),
        (12, 47, "shared_reload_shuffle", {
            1: [(1,4,30.13,27959.11,523.43,133083,122),
                (16,64,16.36,2591.08,9827.04,2500443,662)],
            2: [(1,4,50.35,28935.78,304.19,77347,119),
                (16,64,23.02,2923.26,6918.71,1760368,662)],
            4: [(1,4,54.35,28320.95,289.94,73718,120),
                (16,64,24.31,2583.75,6807.47,1732473,665)],
        }),
    ]

    # To prevent hardcoded numbers silently becoming truth, verify every encoded
    # table value is actually present in the extracted PDF page before accepting it.
    for table_no, page_no, mode, matrix in table_specs:
        page = page_map.get(page_no, "")
        missing_tokens = []
        for stripe, records in matrix.items():
            for rec in records:
                for value in rec[2:]:
                    token = f"{value:,.2f}" if isinstance(value, float) else f"{value:,}"
                    # PDF extraction may strip thousands separators or trailing zeroes.
                    candidates = {
                        token,
                        token.replace(",",""),
                        str(value),
                        str(value).replace(",",""),
                    }
                    if not any(c in page for c in candidates):
                        missing_tokens.append(str(value))

        if missing_tokens:
            audit.append({
                "figure": f"Table_{table_no}",
                "element": "table",
                "status": "TABLE_VERIFICATION_FAILED",
                "reason": "Encoded extraction template contains values not found on PDF page: "
                          + ", ".join(sorted(set(missing_tokens))),
                "source_pages": str(page_no),
            })
            continue

        metric_map = [
            ("io_time", 2, "s"),
            ("runtime", 3, "s"),
            ("bandwidth", 4, "MiB/s"),
            ("iops", 5, "IOPS"),
            ("memory_usage", 6, "GB"),
        ]

        figure_by_stripe_mode = {
            ("shared",1):11, ("shared",2):13, ("shared",4):15,
            ("shared_reload_shuffle",1):12,
            ("shared_reload_shuffle",2):14,
            ("shared_reload_shuffle",4):16,
        }

        for stripe, records in matrix.items():
            fig = figure_by_stripe_mode[(mode,stripe)]
            for rec in records:
                nodes, procs = rec[0], rec[1]
                for metric, idx, unit in metric_map:
                    rows.append(_row(
                        figure=fig,
                        panel="table",
                        application="DeepGalaxy",
                        filesystem="lustre",
                        stripe_count=stripe,
                        file_format="hdf5",
                        data_loading_mode=mode,
                        nodes=nodes,
                        process_io=procs,
                        metric=metric,
                        value=float(rec[idx]),
                        unit=unit,
                        source_type="ARTICLE_TABLE",
                        source_page=page_no,
                        source_section="5",
                        source_reference=f"Article 01, Table {table_no}",
                        evidence_text=f"Table {table_no}, Lustre {stripe} OST, {nodes}N-{procs}P",
                    ))
        audit.append({
            "figure": f"Table_{table_no}",
            "element": "table",
            "status": "EXTRACTED_AND_VERIFIED",
            "reason": "",
            "source_pages": str(page_no),
        })

    return rows, audit


def extract_dlio_performance(pages):
    """
    Extract exact scalar values explicitly published for Figures 6-9.

    Figures 6, 7 and 9 are extracted from article prose. Figure 8 additionally
    contains exact numeric labels printed directly on the published figure.
    Those labels are represented as ARTICLE_FIGURE provenance: they are exact
    transcriptions of printed annotations, not OCR, interpolation, or plot
    digitization/estimation.
    """
    rows, audit = [], []
    page_map = {x["page"]: _normalize_pdf_text(x["text"]) for x in pages}

    def add_pair(fig, metric, panel, mode, fformat, stripe_start, stripe_end,
                 nodes_start, procs_start, nodes_end, procs_end,
                 value_start, value_end, unit, page, evidence):
        for stripe,nodes,procs,value in [
            (stripe_start,nodes_start,procs_start,value_start),
            (stripe_end,nodes_end,procs_end,value_end),
        ]:
            rows.append(_row(
                figure=fig, panel=panel, application="DLIO",
                filesystem="lustre", stripe_count=stripe, file_format=fformat,
                data_loading_mode=mode, nodes=nodes, process_io=procs,
                metric=metric, value=value, unit=unit,
                source_type="ARTICLE_TEXT", source_page=page,
                source_section="3.6.1",
                source_reference=f"Article 01, Sec. 3.6.1, Fig. {fig}",
                evidence_text=evidence,
            ))

    # Figure 6 exact endpoints, pages 25-26.
    t6 = " ".join(page_map.get(p,"") for p in [25,26])
    p6 = {
        "bandwidth": (r"data transfer rate increased from ([\d,.]+) MiB/s .*? to ([\d,.]+) MiB/s", "a","MiB/s"),
        "iops": (r"IOPS metric, which increases from ([\d,.]+) ops/s to ([\d,.]+) ops/s", "b","IOPS"),
        "runtime": (r"total execution time drops .*? from ([\d,.]+)s .*? to ([\d,.]+)s", "c","s"),
        "io_time": (r"I/O time dropping from ([\d,.]+)s to ([\d,.]+)s", "c","s"),
    }
    for metric,(pat,panel,unit) in p6.items():
        m=_search(pat,t6,re.I|re.S)
        if m:
            add_pair(6,metric,panel,"shared","hdf5",1,12,1,4,12,48,
                     _num(m.group(1)),_num(m.group(2)),unit,25,m.group(0))
            audit.append({"figure":6,"element":metric,"status":"EXTRACTED","reason":"","source_pages":"25,26"})
        else:
            audit.append({"figure":6,"element":metric,"status":"NOT_EXTRACTED","reason":"Pattern not found","source_pages":"25,26"})

    # Figure 7 has exact start/peak/final for BW/IOPS and start/final for runtime.
    t7 = " ".join(page_map.get(p,"") for p in [26,27])
    # Start and final/peak values from prose are captured as separate explicit points.
    regexes7 = [
        ("bandwidth", "a", "MiB/s",
         r"rising from ([\d,.]+) MiB/s \(1N-4P-1OST\) to a peak of ([\d,.]+) MiB/s \(8N-32P-8OST\).*?final .*?\(([\d,.]+) MiB/s with 12N-48P-12OST\)",
         [(1,4,1),(8,32,8),(12,48,12)]),
        ("iops", "b", "IOPS",
         r"scaling from ([\d,.]+) ops/s to ([\d,.]+) ops/s, then dropping to ([\d,.]+) ops/s",
         [(1,4,1),(8,32,8),(12,48,12)]),
    ]
    for metric,panel,unit,pat,confs in regexes7:
        m=_search(pat,t7,re.I|re.S)
        if m:
            for (nodes,procs,stripe),val in zip(confs,m.groups()):
                rows.append(_row(
                    figure=7,panel=panel,application="DLIO",filesystem="lustre",
                    stripe_count=stripe,file_format="npz",data_loading_mode="multi",
                    nodes=nodes,process_io=procs,metric=metric, value=_num(val),unit=unit,
                    source_type="ARTICLE_TEXT",source_page=26,source_section="3.6.1",
                    source_reference="Article 01, Sec. 3.6.1, Fig. 7",evidence_text=m.group(0),
                ))
            audit.append({"figure":7,"element":metric,"status":"EXTRACTED","reason":"","source_pages":"26,27"})
        else:
            audit.append({"figure":7,"element":metric,"status":"NOT_EXTRACTED","reason":"Pattern not found","source_pages":"26,27"})

    # Figure 8 exact labels printed on the published figure (page 29).
    # These values are curated transcriptions of explicit annotations in Fig. 8,
    # not values inferred from bar heights.  The article prose itself reports
    # ranges for several of these points, so provenance is ARTICLE_FIGURE.
    fig8_points = {
        "bandwidth": {
            "panel": "a", "unit": "MiB/s",
            "values": [
                (1, 4, 1, 325.2),
                (2, 8, 2, 566.3),
                (4, 16, 4, 5626.9),
                (8, 32, 8, 21157.5),
                (12, 48, 12, 21429.8),
            ],
        },
        "iops": {
            "panel": "b", "unit": "IOPS",
            "values": [
                (1, 4, 1, 1304.7),
                (2, 8, 2, 2265.1),
                (4, 16, 4, 22509.2),
                (8, 32, 8, 84638.8),
                (12, 48, 12, 85101.5),
            ],
        },
        # Endpoint I/O-time labels are unambiguously printed in panel (c).
        "io_time": {
            "panel": "c", "unit": "s",
            "values": [
                (1, 4, 1, 301.7),
                (12, 48, 12, 4.7),
            ],
        },
    }
    for metric, spec in fig8_points.items():
        for nodes, procs, stripe, value in spec["values"]:
            rows.append(_row(
                figure=8, panel=spec["panel"], application="DLIO",
                filesystem="lustre", stripe_count=stripe, file_format="tfrecord",
                data_loading_mode="multi", nodes=nodes, process_io=procs,
                metric=metric, value=value, unit=spec["unit"],
                source_type="ARTICLE_FIGURE", source_page=29,
                source_section="3.6.1",
                source_reference=f"Article 01, Sec. 3.6.1, Fig. 8{spec['panel']}",
                evidence_text=(
                    f"Explicit printed Fig. 8{spec['panel']} annotation: "
                    f"{nodes}N-{procs}P-{stripe}OST = {value} {spec['unit']}"
                ),
            ))
        audit.append({
            "figure": 8, "element": metric, "status": "EXTRACTED_FROM_FIGURE_LABEL",
            "reason": "Exact numeric labels printed directly in published Fig. 8; no plot-height estimation.",
            "source_pages": "29",
        })

    # Figure 9 exact endpoints, pages 30-31.
    t9 = " ".join(page_map.get(p,"") for p in [30,31])
    p9 = {
        "bandwidth": (r"from ([\d,.]+) MiB/s \(1N-4P-1OST\) up to ([\d,.]+) MiB/s \(12N-48P-12OST\)", "a","MiB/s"),
        "iops": (r"increasing from ([\d,.]+) IOPs in the 1N-4P-1OST configuration to ([\d,.]+) IOPs in the 12N-48P-12OST setup", "b","IOPS"),
        "runtime": (r"Total execution .*? time drops significantly: from ([\d,.]+)s \(1N-4P-1OST\) to only ([\d,.]+)s \(12N-48P-12OST\)", "c","s"),
        "io_time": (r"I/O time is drastically reduced, from ([\d,.]+)s down to ([\d,.]+)s", "c","s"),
    }
    for metric,(pat,panel,unit) in p9.items():
        m=_search(pat,t9,re.I|re.S)
        if m:
            add_pair(9,metric,panel,"multi","tfrecord",1,12,1,4,12,48,
                     _num(m.group(1)),_num(m.group(2)),unit,30,m.group(0))
            audit.append({"figure":9,"element":metric,"status":"EXTRACTED","reason":"","source_pages":"30,31"})
        else:
            audit.append({"figure":9,"element":metric,"status":"NOT_EXTRACTED","reason":"Pattern not found","source_pages":"30,31"})

    # Explicitly document non-scalar/range-only figures rather than fabricating exact values.
    audit.extend([
        {"figure":2,"element":"access_pattern","status":"VISUAL_REFERENCE","reason":"Spatial/temporal pattern; not scalar golden reference.","source_pages":"17,20"},
        {"figure":3,"element":"access_pattern","status":"VISUAL_REFERENCE","reason":"Spatial/temporal pattern; not scalar golden reference.","source_pages":"18,20,21"},
        {"figure":4,"element":"access_pattern","status":"VISUAL_REFERENCE","reason":"Spatial/temporal pattern; not scalar golden reference.","source_pages":"19,21,22"},
        {"figure":5,"element":"access_pattern","status":"VISUAL_REFERENCE","reason":"Spatial/temporal pattern; not scalar golden reference.","source_pages":"22,23"},
        {"figure":10,"element":"access_pattern","status":"VISUAL_REFERENCE","reason":"DeepGalaxy spatial/temporal pattern; validate with DXT/provenance, not scalar plot digitization.","source_pages":"40,41"},
    ])

    return rows, audit


def compare_reference_sources(rows):
    """Compare ARTICLE_TEXT and ARTICLE_TABLE before duplicate resolution.

    This is an audit-only operation. It never changes reference values,
    tolerances, or duplicate precedence.
    """
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    key = [
        "article_id", "figure", "application", "filesystem", "stripe_count",
        "file_format", "data_loading_mode", "nodes", "process_io", "metric",
    ]
    records = []
    for keys, part in df.groupby(key, dropna=False):
        rec = dict(zip(key, keys if isinstance(keys, tuple) else (keys,)))
        text_rows = part[part["source_type"].eq("ARTICLE_TEXT")]
        table_rows = part[part["source_type"].eq("ARTICLE_TABLE")]

        text_value = float(text_rows.iloc[0]["reference_value"]) if len(text_rows) else math.nan
        table_value = float(table_rows.iloc[0]["reference_value"]) if len(table_rows) else math.nan

        if len(text_rows) and len(table_rows):
            abs_diff = abs(text_value - table_value)
            rel_diff = (abs_diff / abs(table_value) * 100.0) if table_value else (0.0 if abs_diff == 0 else math.inf)
            status = "MATCH" if abs_diff == 0 else "DIFFERENT_SOURCE_VALUES"
        elif len(text_rows):
            abs_diff = rel_diff = math.nan
            status = "TEXT_ONLY"
        elif len(table_rows):
            abs_diff = rel_diff = math.nan
            status = "TABLE_ONLY"
        else:
            continue

        rec.update({
            "text_value": text_value,
            "table_value": table_value,
            "absolute_difference": abs_diff,
            "relative_difference_pct": rel_diff,
            "status": status,
            "text_source_reference": text_rows.iloc[0]["source_reference"] if len(text_rows) else "",
            "table_source_reference": table_rows.iloc[0]["source_reference"] if len(table_rows) else "",
        })
        records.append(rec)

    return pd.DataFrame(records)


def resolve_duplicates(rows):
    """
    Prefer the most precise independent source when the same scientific key
    is reported multiple times.

    Priority:
        ARTICLE_TEXT > ARTICLE_FIGURE > ARTICLE_TABLE

    This keeps narrative decimal IOPS when available while retaining table-only
    runtime/memory references.
    """
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    key = [
        "article_id","figure","application","filesystem","stripe_count","file_format",
        "data_loading_mode","nodes","process_io","metric"
    ]
    priority = {"ARTICLE_TEXT":0, "ARTICLE_FIGURE":1, "ARTICLE_TABLE":2}
    df["_priority"] = df["source_type"].map(priority).fillna(99)
    df = (
        df.sort_values(key + ["_priority"])
          .drop_duplicates(key, keep="first")
          .drop(columns=["_priority"])
          .reset_index(drop=True)
    )
    return df
