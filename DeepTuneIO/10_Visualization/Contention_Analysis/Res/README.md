# DeepTuneIO Analyzer — Contention Analysis

**Ubicación:** `10_Visualization/Contention_Analysis/` (hermano de `Access_Pattern`).

## Objetivo

1. **DXT:** operaciones únicas implicadas en coincidencias exactas, parciales o sobre recursos compartidos (candidatos, no contención demostrada).
2. **Rendimiento:** contrastar tiempos de E/S, ancho de banda y duración con ejecuciones comparables. Los gráficos descriptivos de un solo JobID NO demuestran degradación.

## Instalación

Copiar la carpeta `Contention_Analysis` dentro de `DeepTuneIO/10_Visualization/`. Abrir `Contention_Analysis.ipynb`, seleccionar campaña, revisar los CSV encontrados y ejecutar.

## Dependencias de datos

Consume los `10_contention_three_cases_pairs.csv` y `10_contention_three_cases_diagnostics.json` de `Access_Pattern` por JobID y los CSV de rendimiento de la campaña. No altera el módulo `Access_Pattern`.

## Figuras añadidas

- `01_dxt_candidate_involvement_by_job.png`: porcentaje de operaciones DXT involucradas, por JobID, con cobertura explícita.
- `02_performance_of_dxt_covered_jobs.png`: métricas observadas de los mismos JobIDs, separadas en paneles.

Las gráficas comparativas 2A/2B existentes se conservan, pero su interpretación requiere equivalencia de carga, almacenamiento y configuración. No se atribuye causalidad automáticamente.

**Limitación:** la comparación de degradación exige baselines equivalentes y, preferiblemente, repeticiones; no se puede inferir solo del porcentaje de coincidencias DXT.
