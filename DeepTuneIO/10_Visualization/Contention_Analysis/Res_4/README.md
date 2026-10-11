# Contention Analysis (v5)

Visualización integrada con `Access_Pattern` en `10_Visualization`.

1. Coloca `Access_Pattern` y `Contention_Analysis` como carpetas hermanas en `10_Visualization`.
2. Abre `Contention_Analysis.ipynb` desde esa carpeta o la raíz del proyecto.
3. Indica `CAMPAIGN_ROOT`, `JOBID`, `FILE_FORMAT` y los filtros.
4. Ejecuta todas las celdas. No se necesitan `EVENT_CSVS` ni `PAIRS_CSV`.

La campaña debe contener eventos DXT detallados bajo `results`. El notebook llama a `prepare_access_pattern()` y `analyze_potential_contention()` del módulo existente, exporta la tabla exacta de eventos normalizados y genera mapas Offset × Tiempo con histogramas marginales, y matriz Proceso × Proceso. Los mapas de offsets muestran A/B; C se representa en la matriz de procesos.

**Limitación:** coincidencias no prueban degradación; la validación requiere rendimiento y referencias comparables. El detector puede truncar el número de pares a `max_pairs`.
