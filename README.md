# DeepTuneIO — Benchmark y análisis reproducible de E/S para IA en HPC

## Descripción

**DeepTuneIO** reúne herramientas de ejecución, instrumentación, procesamiento, análisis y validación de experimentos de entrada/salida (E/S) en aplicaciones de inteligencia artificial sobre infraestructuras HPC. El repositorio combina **DeepTuneIO-Training** (carga de trabajo de entrenamiento) con el flujo de análisis **DeepTuneIO Analyzer**, y contempla campañas de **DeepGalaxy** y **DLIOv1**.

Su objetivo es caracterizar el movimiento de datos, identificar patrones de acceso y posibles situaciones de contención, estudiar el rendimiento de la E/S y producir evidencias reproducibles para comparar configuraciones experimentales. No debe interpretarse una coincidencia temporal de accesos como prueba, por sí sola, de degradación causal del rendimiento.

## Alcance experimental

El código contiene soporte y scripts para campañas con diferentes formatos y condiciones de acceso. Entre los casos representados se encuentran HDF5, NPZ y TFRecord; almacenamiento Lustre y escenarios asociados a NFS; variaciones de recursos, distribución de archivos y configuración de *striping*. La disponibilidad de cada combinación depende de la campaña y de los datos de entrada.

Las principales fuentes de evidencia son trazas **Darshan/DXT**, informes del parser, métricas de rendimiento y metadatos de recursos (incluidos informes `seff` cuando existen). La correlación entre productos experimentales se realiza mediante identificadores de trabajo y metadatos reconstruidos.

## Organización del repositorio

| Directorio | Función |
|---|---|
| `00_Training/` | Aplicación DeepTuneIO-Training, utilidades de datos, modelo y configuración de instrumentación. |
| `01_Execution/` | Scripts de ejecución de campañas DeepGalaxy, DLIOv1 y HPC. |
| `02_Darshan_Conversion/` | Conversión de trazas Darshan a representaciones de texto. |
| `03_Resource_Metadata/` | Extracción de JobID y métricas de recursos/SEFF. |
| `04_Access_Pattern/` | Procesamiento de eventos DXT, patrones de acceso y asociación lógica de OST. |
| `05_Aggregation/` | Procesamiento y agregación de informes del parser Darshan. |
| `06_Performance/` | Procesamiento de informes y métricas de rendimiento. |
| `07_Analysis/` | Análisis de comportamiento de E/S e indicadores compuestos. |
| `08_Experiment_Indexing/` | Indexación, reconstrucción y validación de metadatos experimentales. |
| `09_Consolidator/` | Consolidación de resultados de diferentes fuentes. |
| `10_Visualization/` | Visualización de patrones de acceso, rendimiento y análisis de contención. |
| `11_Figure_Registry/` | Registro y trazabilidad de figuras. |
| `12_Article_Validation/` | Construcción de referencias y validación de resultados del artículo. |

Los directorios contienen sus propios notebooks, módulos Python y, en varios casos, documentación técnica adicional.

## Flujo de trabajo recomendado

```text
Configuración de la campaña
        ↓
01 Ejecución e instrumentación (00/01)
        ↓
02 Conversión Darshan + 03 metadatos de recursos
        ↓
04 Patrones DXT + 05 parser + 06 rendimiento
        ↓
07 Análisis
        ↓
08 Indexación y validación de metadatos
        ↓
09 Consolidación por experimento/JobID
        ↓
10 Visualización y análisis de contención
        ↓
11 Registro de figuras
        ↓
12 Validación frente a referencias del artículo
```

Este esquema describe las dependencias conceptuales: **no todos los módulos son obligatorios en todas las campañas**. La disponibilidad de productos depende de la instrumentación y del caso de uso. En particular, el consolidador no exige universalmente Training y SEFF para analizar BW, tiempo de E/S o IOPS.

## Requisitos

- Python y Jupyter para los notebooks y módulos de análisis.
- Un entorno de entrenamiento compatible con las dependencias importadas por `00_Training/` (por ejemplo, TensorFlow/Keras y, para ejecución distribuida, los componentes utilizados por el código).
- Herramientas Darshan para generar e interpretar trazas; habilitar DXT cuando se requiera análisis temporal detallado.
- Entorno HPC y planificador compatible con los scripts de campaña cuando se ejecuten experimentos distribuidos; herramientas `seff` si se recopilan esos informes.
- Datos experimentales, rutas de trabajo y permisos de lectura/escritura configurados para la infraestructura concreta.

**Nota:** el ZIP no define en su raíz un entorno único y portable de instalación. Antes de ejecutar, revisar las importaciones, las rutas y las variables de configuración de cada script o notebook; no asumir que los valores preconfigurados funcionan fuera del sistema original.

## Inicio rápido

1. Descomprimir el proyecto y revisar los scripts de `01_Execution/` correspondientes a la campaña deseada.
2. Preparar el dataset, el entorno Python, la instrumentación Darshan y las rutas de entrada/salida.
3. Ejecutar la campaña elegida; conservar los archivos `.darshan`, identificadores JobID y los informes de ejecución.
4. Procesar las evidencias con los módulos `02` a `06`, utilizando los notebooks o scripts de cada directorio.
5. Ejecutar los análisis e indexación (`07` y `08`), consolidar (`09`) y generar visualizaciones (`10`).
6. Registrar las figuras (`11`) y, si se reproducen resultados publicados, ejecutar la validación (`12`).

### Ejemplo de navegación

```bash
unzip DeepTuneIO.zip
cd DeepTuneIO
ls 01_Execution/HPC
ls 04_Access_Pattern
ls 08_Experiment_Indexing
```

No se incluye un comando universal de ejecución: los argumentos, rutas y parámetros deben tomarse del script específico de la campaña.

## Metadatos y control de calidad

El módulo `08_Experiment_Indexing` reconstruye metadatos y aplica el criterio documentado:

```text
execution=PASS AND instrumentation=COMPLETE AND metadata=PASS
```

El módulo `09_Consolidator` integra las fuentes disponibles sin confundir la ausencia de una fuente opcional con la invalidez automática de todas las métricas. Conviene registrar el JobID, la aplicación, el dataset, el escenario, el sistema de archivos, el formato, el modo de acceso, los recursos asignados y la configuración de instrumentación de cada ejecución.

Para comparaciones reproducibles, conservar trazas originales, productos intermedios, configuración, versiones del software y manifiestos de salida; documentar los casos `SKIPPED`, `MISSING`, `FAIL` y cualquier discrepancia con la referencia.

## Análisis de contención

`10_Visualization/Contention_Analysis/` incluye notebooks y documentación metodológica para analizar coincidencias temporales de accesos. El README de esta sección advierte que los mapas de calor de concurrencia representan **evidencia de solapamiento**, no una medición causal de pérdida de rendimiento. El flujo contempla un manifiesto de figuras (`contention_figures_manifest.json`) y límites de pares analizados que deben verificarse para detectar posibles truncamientos.

## Validación de resultados publicados

La documentación de `12_Article_Validation/` establece este orden:

1. `12_Golden_Reference_Builder.ipynb` cuando se instala/actualiza el módulo o cambia la fuente de publicación.
2. `12_Automatic_Article_Validation.ipynb` una vez generados los productos de rendimiento agrupados del módulo 10.
3. `Diagnostics/12_Article_Validation_Provenance_Diagnostic.ipynb` si aparecen resultados `FAIL`, `MISSING` o `ERROR`.

La documentación del módulo señala **82 filas únicas** como línea base de aceptación de Golden Reference para Article 01. Es un criterio del módulo documentado, no una validación ejecutada durante la preparación de este README.

## Documentación específica

- `08_Experiment_Indexing/README.md` y `Documentation/`: indexación, adaptadores y entradas/salidas.
- `09_Consolidator/README.md` y `Documentation/`: consolidación y validación.
- `10_Visualization/Contention_Analysis/README.md`: interpretación de los análisis de contención.
- `10_Visualization/Performance/README.md`: productos de visualización de rendimiento.
- `11_Figure_Registry/README.md`: registro de figuras.
- `12_Article_Validation/Documentation/EXECUTION_ORDER.md`: secuencia de validación.

## Limitaciones y reproducibilidad

La presencia de un módulo no garantiza que todas las campañas incluyan los datos necesarios para ejecutarlo. Las métricas derivadas deben interpretarse dentro de su campaña y con las unidades y normalizaciones correspondientes. La validez de una comparación exige comprobar equivalencia de configuración, integridad de la instrumentación y procedencia de los archivos.

Este README documenta la **estructura y el procedimiento identificables en el código entregado**; no certifica que el proyecto se haya ejecutado de extremo a extremo ni sustituye la validación experimental.

## Guía reproducible de ejecución de DeepTuneIO-Training en HPC

Esta sección amplía el inicio rápido con opciones verificadas en los scripts incluidos en `01_Execution/HPC/`. **Los ejemplos son plantillas de invocación, no ejecuciones comprobadas en este entorno.** Los scripts contienen rutas y módulos específicos de CESGA que deben adaptarse al clúster de destino.

### Preparación del entorno

La implementación HPC incluida utiliza SLURM, módulos de CESGA (`cesga/2020`, `gcc/system`, `openmpi/4.1.4_ft3`, `python/3.9.9`), un entorno virtual Python, datos Tiny ImageNet-200 y la instrumentación Darshan/DXT. Configurar las rutas de instalación antes de lanzar trabajos:

```bash
export DTIO_APP_DIR=/ruta/a/DeepTuneIO/00_Training
export DTIO_VENV=/ruta/a/entorno_virtual
export DTIO_TINY_ROOT=/ruta/a/Tiny_ImageNet_200
export DTIO_DATASET_ROOT=/ruta/a/datasets_generados
export DTIO_RESULTS_ROOT=/ruta/a/resultados
export DTIO_CAMPAIGN_ROOT=/ruta/a/campanas
```

**Importante:** los scripts HPC buscan `DeepTuneIO_Training_Tiny_Real_v4.py`, `trace_DXT4M.sh` y `darshan_DXT4M.conf` dentro de `DTIO_APP_DIR`, pero en el ZIP el programa principal se llama `DeepTuneIO_Training_Tiny_Real_v4.py` (sin guion bajo entre `DeepTuneIO` y `Training`). Corregir la referencia `MAIN` del script o adaptar el nombre de archivo antes de ejecutar; comprobar también las rutas por defecto que incluyen `DeepTuneIO_Trainig` (grafía heredada). No renombrar a ciegas los directorios de resultados de campañas existentes.

### Envío de una campaña SLURM

El controlador `03_submit_campaign.sh` debe ejecutarse **desde el nodo de acceso**, no con `sbatch`:

```bash
cd DeepTuneIO/01_Execution/HPC
chmod +x 01_inspect_prepare_hdf5.sh 03_submit_campaign.sh
./03_submit_campaign.sh \
  --nodes 1 \
  --run run001 \
  --format HDF5 \
  --strategy full_shared \
  --scenario lustre_1ost \
  --epochs 1 \
  --batch-size 32
```

Las combinaciones admitidas por el controlador son `HDF5 + full_shared`, `HDF5 + distributed_shared` y `JPEG + direct`. Los escenarios admitidos son `lustre_1ost`, `lustre_2ost` y `lustre_4ost`, con tamaño de franja de 1 MiB en el script de ejecución. El controlador permite `--nodes`, `--nodelist`, `--tasks-per-node` (4 por defecto), `--run`, `--format`, `--strategy`, `--scenario`, `--num-classes` (10), `--images-per-class` (100), `--epochs` (1), `--batch-size` (32), `--dataset-scope` (`train-val` o `train-only`), `--generate-only`, `--time` y `--mem-per-cpu`.

Para generar datos sin ejecutar entrenamiento, añadir `--generate-only`. Para JPEG se debe utilizar `--strategy direct`:

```bash
./03_submit_campaign.sh --nodes 1 --run jpeg001 \
  --format JPEG --strategy direct --scenario lustre_1ost
```

La variable `DTIO_DXT_ENABLE=1` habilita `DXT_ENABLE_IO_TRACE=1` en el trabajo. La configuración incluida deshabilita los módulos H5F/H5D de Darshan (`DARSHAN_MOD_DISABLE="H5F,H5D"`) y conserva instrumentación POSIX/DXT_POSIX/LUSTRE según disponibilidad. Por tanto, no debe interpretarse la ausencia de métricas HDF5 de Darshan como ausencia de operaciones HDF5 en la aplicación.

### Campañas DLIOv1

Los cuatro scripts de `01_Execution/DLIOv1/DeepTuneIO_DLIOv1_Execution_Scripts/` reconstruyen configuraciones experimentales de la publicación:

| Campaña | Formato y acceso | Parámetros relevantes |
|---|---|---|
| `HDF5_64bs` | `hdf5`, `shared` | 1 archivo, tamaño 786432, longitud de registro 786432, batch 64 |
| `NPZ_64bs` | `npz`, `multi` | `P` archivos, tamaño por archivo `786432/P`, registro 131072, batch 64 |
| `TFRecord_256kts_64bs` | `tfrecord`, `multi | Tamaño de shard `ts=262144` |
| `TFRecord_1mts_64bs` | `tfrecord`, `multi | Tamaño de shard `ts=1048576` |

En esta campaña `P = 4 × número de nodos`, `stripe_count = número de nodos` y `stripe_size = 1 MiB`, según el README de los scripts. Las fases controladas mediante `DLIO_PHASE` son `generate`, `read` y `both`. Los scripts no borran silenciosamente datasets preexistentes; `DLIO_ALLOW_EXISTING_DATASET=1` debe establecerse únicamente cuando su reutilización sea intencionada.

### Productos, trazabilidad y comprobaciones

La ejecución HPC construye el nombre de traza con `RUN_ID`, formato, estrategia, escenario, número de nodos, procesos y `SLURM_JOB_ID`, por ejemplo:

```text
run001_DTIO_HDF5_full_shared_lustre_1ost_N1P4_<JOB_ID>.darshan
```

Antes del análisis se recomienda verificar: (a) finalización correcta del trabajo SLURM; (b) existencia y legibilidad de la traza; (c) módulos Darshan realmente capturados; (d) concordancia entre JobID, formato, escenario y número de procesos; (e) disponibilidad de productos DXT, parser, rendimiento y SEFF cuando correspondan; y (f) presencia de los datasets que espera cada experimento.

## Validación del artículo: detalles de aceptación

Según `12_Article_Validation/README.md`, el módulo mantiene una línea base histórica de **82 referencias** y extiende la cobertura con **12 anotaciones numéricas exactas de la Figura 8**. No deben confundirse las 82 referencias históricas con el total de referencias tras esa ampliación. La política de procedencia prioriza `ARTICLE_TEXT > ARTICLE_FIGURE > ARTICLE_TABLE`; prohíbe inventar referencias, estimar valores a partir de la altura de barras o modificar arbitrariamente tolerancias.

Para BW, IOPS y tiempo de E/S, la validación estricta utiliza tolerancia relativa del **1 %** y absoluta de **1e-6**. Un valor compatible únicamente con la precisión decimal publicada se identifica separadamente como `PASS_PUBLICATION_PRECISION`, no como `PASS` estricto. La validación de patrones de acceso utiliza evidencias estructurales DXT y el registro de figuras; no debe confundirse con la comparación de métricas escalares.

## Estado de portabilidad y puntos pendientes

- No se ha encontrado un archivo único de dependencias reproducibles en la raíz; registrar versiones efectivas de Python, TensorFlow, MPI, Darshan y librerías de análisis antes de publicar el benchmark.
- Adaptar las rutas absolutas y los módulos del clúster; comprobar la discrepancia entre el nombre del programa principal y la referencia `MAIN` en `02_run_dtio_training.sh`.
- Registrar parámetros de cada campaña y semillas aleatorias cuando apliquen, junto con la versión del código y checksums de los datasets/resultados.
- Evitar presentar como **validados** resultados que no hayan pasado la ejecución completa y las comprobaciones del módulo 12.
- Para compartir el repositorio, excluir `.ipynb_checkpoints/`, `__pycache__/`, copias `.bak` y cachés de pruebas, sin eliminar las fuentes originales de evidencia experimental.
