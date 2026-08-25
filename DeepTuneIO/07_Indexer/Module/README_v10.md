# DeepTuneIO-Indexer v10

## Objetivo

La v10 separa el núcleo del indexador de los adaptadores de aplicación. El núcleo no asume que los parámetros de una aplicación sean estáticos ni que todas las aplicaciones utilicen los mismos nombres.

Por el momento se incluyen dos adaptadores DLIO:

- `DLIOV1Adapter`: detecta el CLI legado (`python src/dlio_benchmark.py -f ... -nf ... -sf ...`).
- `DLIOV2Adapter`: detecta el entrypoint actual `dlio_benchmark` con configuración Hydra (`workload=...`, `++workload.dataset...`).

## Estructura

```text
DeepTuneIO_Indexer_v10/
├── DeepTuneIO_Indexer_v10.py
├── deeptuneio/
│   ├── __init__.py
│   └── adapters/
│       ├── __init__.py
│       ├── base.py
│       ├── dlio_common.py
│       ├── dlio_v1.py
│       ├── dlio_v2.py
│       └── registry.py
└── tests/
    └── test_dlio_adapters.py
```

## Detección de versión a partir de Darshan

El Parser de Darshan contiene normalmente `# exe:`. DeepTuneIO usa esa línea como evidencia primaria.

### DLIO v1

Firma fuerte:

```text
# exe: python src/dlio_benchmark.py -f npz -fa multi -nf 4 -sf 196608 ...
```

Salida:

```text
application = DLIO
application_version = v1
application_version_source = legacy_cli_signature
application_version_confidence = HIGH
configuration_source = legacy_cli
```

### DLIO 2.x/current

Firma fuerte:

```text
# exe: mpirun -np 8 dlio_benchmark workload=unet3d ++workload.dataset.format=npz ...
```

Salida:

```text
application = DLIO
application_version = 2.x
application_version_source = hydra_cli_signature
application_version_confidence = HIGH
configuration_source = hydra_overrides
```

Si Darshan no contiene suficiente evidencia, DeepTuneIO no inventa la versión.

## Normalización

Los adaptadores conservan dos representaciones:

1. `application_parameters`: parámetros originales tal como se recuperan de la aplicación.
2. `normalized_parameters`: equivalentes semánticos DeepTuneIO cuando existe una correspondencia conocida.

Ejemplo:

```text
DLIO v1: -sf 196608
DLIO 2.x: dataset.num_samples_per_file=196608
                  ↓
samples_per_file = 196608
```

Los parámetros no normalizados no se descartan. En DLIO 2.x se conservan con prefijo `dlio2.` para evitar asignar una semántica universal incorrecta.

## Configuración reproducible

`configuration_parameters` contiene los parámetros normalizados usados para distinguir configuraciones experimentales. Se excluyen únicamente controles claros de procedencia/localización como rutas de salida, logs o debug. `configuration_signature` permite que la matriz experimental detecte réplicas sin depender de un conjunto rígido de parámetros.

## Ejecución

Desde el directorio del proyecto:

```bash
python DeepTuneIO_Indexer_v10.py /ruta/experimentos -o /ruta/salida
```

## Pruebas

```bash
PYTHONPATH=. python -m pytest -q tests/test_dlio_adapters.py
```

La entrega v10 incluye pruebas de detección y normalización para DLIO v1 y DLIO 2.x/current.


## Notebook workflow

`DeepTuneIO_Indexer_v10.ipynb` incorpora el flujo práctico utilizado en la v9
modificada: selección de campaña por posición, construcción automática de rutas,
separación entre experimentos validados e incompletos, recuperación de metadatos,
matriz experimental, cobertura de campaña e inspección de réplicas. En v10 las
celdas se han actualizado para `samples_per_file`, parámetros HDF5 normalizados y
detección de versión DLIO.

## Semantic parameter roles and signatures

This revision adds a generic role-based signature layer. Application adapters may
classify parameters as APPLICATION, DATASET, SCALING, STORAGE, EXECUTION or
PROVENANCE and may expose observed derived parameters. DLIO v1 and DLIO 2.x
currently derive `total_samples = number_files * samples_per_file` when both
values are available.

The Indexer now stores:
- `parameter_roles`
- `derived_parameters`
- `application_configuration_signature`
- `dataset_configuration_signature`
- `experiment_configuration_signature`

Replica grouping is based on the complete experiment signature, not on a static
list of application parameters.

## DLIO v1 defaults

The DLIO v1 adapter now distinguishes explicit CLI parameters from documented
version defaults. Only unambiguous defaults supplied/validated by the project
are injected into the effective normalized configuration. Allowed-value lists
are not treated as defaults.

Each effective parameter records provenance in `parameter_provenance`, using
sources such as `explicit_application_command`, `application_default`, and
`generic_extraction`.

## DLIO v1 source-verified defaults

The complete DLIO v1 default set is now taken from the original
`argument_parser.py` supplied with the project. This supersedes the earlier
partial/default-conservative mapping. Explicit CLI arguments always override
these defaults, and `parameter_provenance` records whether an effective value
came from the command or from the version-specific default.

## DeepGalaxy adapter

DeepTuneIO-Indexer v10 now includes a dedicated `DeepGalaxyAdapter`.

The adapter:
- identifies executions launched with `dg_train.py`;
- extracts explicit DeepGalaxy CLI parameters;
- applies source-verified defaults from the supplied `dg_train.py`;
- derives `file_format` from the dataset file;
- preserves `data_loading_mode` and adds the semantic `access_strategy`;
- participates in the generic semantic signature system without modifying the
  application-agnostic Indexer core.

Initial validation target:
`1_DG_N1p4e1_EfficientNetB4_outputbw512hdf5_ds36nc14_M0_lustre_ss1MBsc1_4935078_FT3RESDT_*`

## Generic application-result metrics

The adapter contract now exposes `parse_application_metrics()` and
`parse_application_metric_series()`. Metric names are not hard-coded in the
Indexer core. DeepGalaxy parses completed Keras epoch summaries and preserves
both normalized and native metric names. A new
`application_metrics_<suffix>.csv` is generated in long format. Application
results never participate in configuration signatures.
