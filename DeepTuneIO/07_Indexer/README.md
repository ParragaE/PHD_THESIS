# DeepTuneIO-Indexer v10 — Complete Master Version

Esta es la versión maestra acumulativa del proyecto.

## Estructura

- `DeepTuneIO_Indexer_v10.ipynb`: notebook principal con selección dinámica de aplicación y campaña.
- `Module/DeepTuneIO_Indexer_v10.py`: núcleo del indexador.
- `Module/deeptuneio/adapters/`: adaptadores por aplicación/versión.
- `tests/`: pruebas de regresión.

## Flujo del notebook

1. Seleccionar `APPLICATION`.
2. Resolver `BASE_DIR`.
3. Descubrir automáticamente campañas con `discover_campaigns()`.
4. Seleccionar `POSICION`.
5. Construir `INPUT_DIR` y `OUTPUT_DIR`.
6. Ejecutar `DeepTuneIOIndexer`.
7. Generar índice, matriz, cobertura, validación y métricas de aplicación.

## Funcionalidad acumulada

- DLIO v1 y DLIO actual.
- DeepGalaxy.
- Parámetros explícitos + valores por defecto con procedencia.
- Firmas semánticas:
  - application configuration
  - dataset configuration
  - experiment configuration
- Validación conservadora:
  - execution
  - instrumentation
  - metadata
- Métricas genéricas de aplicación.
- Estados de métricas:
  - AVAILABLE
  - PARTIAL
  - UNAVAILABLE
- Las métricas científicas no participan en las firmas de configuración.

## DeepGalaxy

DeepGalaxy extrae:
- parámetros CLI y defaults;
- `operation_mode = read` para el dataset de entrenamiento;
- `loss`;
- `accuracy`;
- `validation_loss`;
- `validation_accuracy`;
- `training_time_s`;
- `step_time_s`;
- `steps`;
- serie por epoch cuando existe.

La completitud científica de DeepGalaxy se define dentro de su adaptador y no en el núcleo genérico.
