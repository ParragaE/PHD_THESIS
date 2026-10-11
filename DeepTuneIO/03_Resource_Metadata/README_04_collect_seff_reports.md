# DeepTuneIO Analyzer --- Module 04: SLURM `seff` Report Collector

## Purpose

`04_collect_seff_reports_args.sh` collects SLURM resource-efficiency
reports for a set of JobIDs by invoking `seff`.

The script is intended for the **cluster side** of the DeepTuneIO
Analyzer workflow. It does not launch jobs and does not perform I/O or
performance analysis. Its only purpose is to retrieve accounting
information already stored by SLURM.

The revised version receives the **application** and **mapping**
explicitly as command-line parameters. These values are incorporated
into output filenames, which preserves the experimental context when
reports from multiple campaigns are stored together.

## Requirements

The script requires:

-   Bash.
-   Access to a SLURM environment.
-   The `seff` command available in `PATH`.
-   A text manifest containing one numeric SLURM JobID per line.
-   Permission to query the corresponding jobs through SLURM accounting.

The script should normally be executed from a login or service node,
subject to the HPC center's usage policy.

## Command-line interface

``` bash
./04_collect_seff_reports_args.sh \
    --jobids JOBIDS.txt \
    --output-dir OUTPUT_DIR \
    --application APPLICATION \
    --mapping MAPPING
```

All four parameters are required.

  -----------------------------------------------------------------------
  Parameter                           Description
  ----------------------------------- -----------------------------------
  `--jobids FILE`                     Text file containing one SLURM
                                      JobID per line.

  `--output-dir DIR`                  Directory where the generated
                                      `seff` reports are stored.

  `--application NAME`                Name of the application or
                                      experimental campaign.

  `--mapping NAME`                    Dataset, mapping, or experimental
                                      configuration identifier.

  `-h`, `--help`                      Display command-line help.

  `--version`                         Display the script version.
  -----------------------------------------------------------------------

## Example: DeepTuneIO-Training

``` bash
chmod +x 04_collect_seff_reports_args.sh

./04_collect_seff_reports_args.sh \
    --jobids 03_jobids_JCC24.txt \
    --output-dir ./seff \
    --application DeepTuneIO-Training \
    --mapping HDF5_Distrib_Shared_TinyImageNet-200
```

The command records the experiment as:

``` text
Application : DeepTuneIO-Training
Mapping     : HDF5_Distrib_Shared_TinyImageNet-200
```

## JobID manifest

The input file should contain one JobID per line:

``` text
8365604
8366063
8374379
8374752
8375308
8400042
```

Blank lines are ignored. Non-numeric entries are reported as invalid and
skipped.

Windows CRLF line endings are accepted; carriage-return characters are
removed before validating each JobID.

## Output naming

Successful reports use the following convention:

``` text
seff_<application>_<mapping>_<jobid>.txt
```

For example:

``` text
seff_DeepTuneIO-Training_HDF5_Distrib_Shared_TinyImageNet-200_8374752.txt
```

Application and mapping labels are sanitized before being used as
filename components. Spaces and path separators are replaced so they
cannot unintentionally create directories.

If `seff` executes but its output does not contain a recognizable SLURM
job report, the result is preserved as:

``` text
seff_<application>_<mapping>_<jobid>.txt.failed
```

This preserves diagnostic information instead of discarding it.

## Existing reports

If a non-empty report already exists, the script does not overwrite it:

``` text
SKIP 8374752: report already exists.
```

This makes the collector safe to rerun after an interrupted or partially
completed collection.

## Execution summary

At the end of execution, the script reports:

``` text
Application : DeepTuneIO-Training
Mapping     : HDF5_Distrib_Shared_TinyImageNet-200
Total       : 6
Generated   : 6
Skipped     : 0
Invalid     : 0
Failed      : 0
Output      : ./seff
```

`Generated` counts newly generated reports. `Skipped` counts valid
reports that already existed. `Invalid` counts malformed JobIDs.
`Failed` counts valid JobIDs for which `seff` did not produce a
recognizable report.

## Exit status

The script returns:

-   `0` when at least one valid report was generated or an existing
    valid report was reused.
-   `1` for configuration or argument errors, such as a missing manifest
    or unavailable `seff`.
-   `2` when no useful report was generated or reused.

Partial results are preserved.

## Recommended workflow

A typical DeepTuneIO Analyzer workflow is:

``` text
Experiment
    |
    v
Darshan / SLURM execution
    |
    v
JobID manifest
    |
    v
04_collect_seff_reports_args.sh
    |
    +--> seff_<application>_<mapping>_<jobid>.txt
    +--> seff_<application>_<mapping>_<jobid>.txt
    +--> ...
```

The application and mapping parameters make each resource report
traceable to the experimental configuration that produced the
corresponding JobID.

## Reproducibility

The collector intentionally does not infer the application or mapping
from filenames or directory names. Both values must be supplied
explicitly. This reduces ambiguity and makes command invocations
reproducible in CORA/RDR documentation.

For reproducibility, record the complete command used for each campaign
together with:

-   script version;
-   application;
-   mapping;
-   JobID manifest;
-   output directory;
-   HPC system or event identifier when applicable.

## Version

Current version: **2.0.0**

Main changes in version 2.0.0:

-   named command-line arguments;
-   explicit `--application`;
-   explicit `--mapping`;
-   application and mapping included in report filenames;
-   filename-label sanitization;
-   CRLF-safe JobID parsing;
-   clearer validation and execution summary;
-   documented exit codes and rerun behavior.
