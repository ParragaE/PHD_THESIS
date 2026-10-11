# DeepTuneIO Analyzer — Contention_Analysis (módulo 10)

Esta carpeta se instala en `10_Visualization/Contention_Analysis/`, junto a `Access_Pattern`.
**No implementa un segundo detector**: consume `10_contention_three_cases_pairs.csv` del detector A/B/C de Access_Pattern y los **mismos CSV de eventos DXT**, en el **mismo orden de carga** utilizado al detectar los pares.

## Figuras
- `01_offset_time_AB_Pall_*.png`: mapa **Offset × Tiempo**, con histogramas superior (tiempo) y lateral (offset). Cada celda cuenta los pares A/B cuyo intervalo de coincidencia temporal y rango común de bytes intersectan esa celda; el color **no** mide latencia ni pérdida de rendimiento.
- `02_process_matrix_AB.png`: matriz **Proceso × Proceso** de pares A/B; puede mostrarse por caso A, B o C. La diagonal se deja vacía.
- Filtros: caso (`AB`, `A_exact`, `B_partial`, `C_shared_resource`), proceso, archivo y JobID descriptivo.
- **C no tiene un offset compartido por definición**: se visualiza en la matriz de procesos, no en el heatmap Offset × Tiempo.

## Ejecución
Abrir `Contention_Analysis.ipynb`, configurar `PAIRS_CSV`, `EVENT_CSVS`, `ACCESS_PATTERN_MODULE`, `OUTPUT_DIR`, `JOBID` y ejecutar todas las celdas. `EVENT_CSVS` debe contener exactamente los ficheros usados en la llamada original al detector de Access_Pattern y en el mismo orden. No se deben unir los índices de evento a ficheros de otra ejecución.

## Interpretación y límites
Coincidencias DXT = candidatos de concurrencia espacial/temporal, **no** degradación probada. La suma marginal representa **cobertura par-celda**, no el número de operaciones únicas: un par puede ocupar múltiples celdas. El algoritmo puede truncar la lista de pares (`truncated=true` en el JSON del detector); en ese caso los mapas no representan el total de coincidencias. No mezclar offsets de diferentes archivos.
