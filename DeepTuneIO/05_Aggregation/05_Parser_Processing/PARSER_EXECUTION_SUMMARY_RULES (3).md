# Module 07 — Execution Summary

The new `4_Execution_Summary_*.csv` contains exactly one row per Jobid.

Aggregation rules:
- additive POSIX counters: sum across dataset files;
- accumulated read/write/metadata time: sum;
- start timestamps: minimum;
- end timestamps: maximum;
- max metrics: maximum;
- execution/configuration fields: one unique value is required;
- ACCESS/STRIDE pairs: counts are combined by value and global top-4 rebuilt;
- Lustre OST IDs: union across all files;
- fastest/slowest rank and variance metrics are not propagated because they
  cannot be reconstructed correctly from file-level summaries alone.

Validation columns:
- Observed_Files
- Total_Files
- Files_Coverage
- Parser_Config_Consistent
- Parser_Config_Inconsistent_Fields
