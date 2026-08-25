#!/usr/bin/env python3
from __future__ import annotations
import argparse, os, sys
from pathlib import Path
import pandas as pd

VERSION = "4.0.0"

def parse_args(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--campaign-root", type=Path, default=None)
    p.add_argument("--project-root", type=Path, default=None)
    p.add_argument("--article-id", default="Article_01_Parallel_IO_Analysis")
    p.add_argument("--application", required=True)
    p.add_argument("--dataset-group", required=True)
    p.add_argument("--scenario", required=True)
    p.add_argument("--file-format", required=True)
    p.add_argument("--filter-mode", required=True, choices=["exact","prefix","extension","regex"])
    p.add_argument("--filter-value", required=True)
    p.add_argument("--regex-ignore-case", action="store_true")
    p.add_argument("--event", default="JSC24")
    p.add_argument("--module-root", type=Path, default=None)
    p.add_argument("--parser-dir", type=Path, default=None)
    p.add_argument("--output-dir", type=Path, default=None)
    return p.parse_args(argv)

def resolve_campaign_paths(args):
    if args.campaign_root:
        root = args.campaign_root.resolve()
    else:
        pr = args.project_root or Path(os.environ.get("PROJECT_ROOT", r"F:\NoteBooks\CORA_DR_UAB"))
        root = (pr/args.article_id/"Data"/args.application/args.dataset_group/args.scenario).resolve()

    return {
        "campaign_root": root,
        "module_root": (args.module_root or Path(__file__).parent).resolve(),
        "parser_dir": (args.parser_dir or root/"processed"/"Parser").resolve(),
        "output_dir": (args.output_dir or root/"results"/"Parser").resolve(),
    }

def main(argv=None):
    args = parse_args(argv)
    paths = resolve_campaign_paths(args)

    if str(paths["module_root"]) not in sys.path:
        sys.path.insert(0, str(paths["module_root"]))

    from Analysis_DarParser.ProcessData import analizar_directorio_y_procesar
    from Analysis_DarParser.data_debugger import leer_valores_filtro_y_transformar, actualizar_y_depurar_csv
    from Analysis_DarParser.StatisticsParser import procesar_datos
    from Analysis_DarParser.LoadFile import guardar_datos
    from Analysis_DarParser.ExecutionSummary import save_execution_summary

    if not paths["parser_dir"].exists():
        print(f"ERROR: Parser directory does not exist: {paths['parser_dir']}")
        return 1

    paths["output_dir"].mkdir(parents=True, exist_ok=True)

    stem = f"{args.application}_Parser_{args.scenario}_{args.dataset_group}_{args.event}"
    p4a = paths["output_dir"]/f"4a_Analisis_IO_{stem}.csv"
    p4b = paths["output_dir"]/f"4b_Analisis_IO_{stem}_dep.csv"
    ps = paths["output_dir"]/f"4_Summary_Global_Avg_{stem}.csv"
    pe = paths["output_dir"]/f"4_Execution_Summary_{stem}.csv"

    dataset_filter = {
        "mode": args.filter_mode,
        "value": args.filter_value,
        "regex_ignore_case": args.regex_ignore_case,
    }

    print("="*80)
    print("DeepTuneIO — Module 05: Darshan Parser Processor")
    print("="*80)
    print("Campaign root :", paths["campaign_root"])
    print("Application   :", args.application)
    print("Dataset group :", args.dataset_group)
    print("Scenario      :", args.scenario)
    print("File format   :", args.file_format)
    print("Filter mode   :", args.filter_mode)
    print("Filter value  :", args.filter_value)
    print("Parser input  :", paths["parser_dir"])
    print("Parser output :", paths["output_dir"])
    print("="*80)

    df = analizar_directorio_y_procesar(
        str(paths["parser_dir"]),
        pd.DataFrame(),
        args.file_format,
        dataset_filter,
        args.application,
    )
    if df.empty:
        print("ERROR: no records matched DATASET_FILTER.")
        return 2

    df.to_csv(p4a, index=False)
    leer_valores_filtro_y_transformar(str(p4a))
    actualizar_y_depurar_csv(str(p4a), str(p4b))
    final = procesar_datos(pd.read_csv(p4b))
    guardar_datos(final, str(ps))
    df_execution = save_execution_summary(final, pe)
    print(f"Execution summary: {pe} ({len(df_execution)} rows)")
    print("Parser processing completed.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
