# PHD_THESIS 
 
**Characterization, Modeling, and I/O Performance Improvement for AI Applications on HPC Systems**

**Autor:** Edixon Párraga · **GitHub:** [ParragaE](https://github.com/ParragaE)

Repositorio de investigación dedicado al estudio del comportamiento de la entrada/salida (E/S) y del movimiento de datos en aplicaciones de inteligencia artificial ejecutadas sobre sistemas de computación de altas prestaciones (*High-Performance Computing*, HPC).

El repositorio reúne herramientas, benchmarks y procedimientos de análisis utilizados para estudiar el rendimiento de la E/S, identificar cuellos de botella y evaluar estrategias de mejora con resultados trazables y reproducibles.

> **Estado:** repositorio de investigación en desarrollo. La disponibilidad de scripts, datos y resultados depende de cada componente y campaña experimental.

## Objetivos de investigación

- **Caracterizar** los patrones de acceso a datos y el comportamiento de E/S en aplicaciones de IA.
- **Diagnosticar** cuellos de botella, contención y efectos de la concurrencia.
- **Modelar** las relaciones entre configuración experimental, carga de trabajo y rendimiento.
- **Evaluar** estrategias de mejora relacionadas con formatos de datos, modos de acceso, paralelismo y sistemas de almacenamiento.
- **Garantizar la trazabilidad** entre ejecuciones, trazas, métricas, figuras y resultados publicados.

## Ecosistema DeepTuneIO

El trabajo se articula alrededor de tres componentes complementarios:

| Componente | Función principal |
| --- | --- |
| **DeepTuneIO Analyzer** | Procesamiento y análisis de trazas Darshan/DXT, metadatos y métricas de rendimiento; consolidación y visualización de resultados. |
| **DeepTuneIO-Training** | Generación y ejecución de cargas de entrenamiento para estudiar formatos de datos y modos de acceso. |
| **DeepTuneIO Experiment Organizer** | Organización, correlación por JobID, auditoría y preservación de evidencias experimentales. |

### DeepTuneIO Analyzer

Permite integrar evidencias de ejecución, estudiar patrones de E/S y contrastar resultados mediante referencias de validación (*Golden Reference*). El análisis puede incluir métricas de tiempo, ancho de banda, número de operaciones y distribución temporal de accesos, según los datos disponibles.

### DeepTuneIO-Training

Permite estudiar cargas de entrenamiento y comparar, según la campaña, formatos como **JPEG, HDF5, NPZ y TFRecord**, así como modos de acceso **individual** y **compartido**.

### DeepTuneIO Experiment Organizer

Apoya la organización de datos *raw* y *processed*, la asociación de resultados con identificadores de trabajos (*JobID*) y la preparación de manifiestos y comprobaciones de integridad para la reproducibilidad.

## Benchmarks y campañas experimentales

Los casos de estudio del proyecto incluyen:

| Benchmark / aplicación | Propósito |
| --- | --- |
| **DeepGalaxy** | Estudiar el comportamiento de E/S bajo distintas configuraciones de infraestructura y concurrencia. |
| **DLIO** | Evaluar patrones de acceso y formatos de datos representativos de cargas de aprendizaje profundo. |
| **DeepTuneIO-Training** | Analizar la lectura de datos durante el entrenamiento y comparar configuraciones experimentales. |

Entre las dimensiones de evaluación se encuentran el sistema de archivos (**Lustre** y **NFS** en las campañas pertinentes), la configuración de recursos, el formato de datos, el modo de acceso y el *striping* cuando corresponde.

## Organización del repositorio

La carpeta de benchmark documentada actualmente es:

```text
PHD_THESIS/
├── DeepTuneIO/
│   └── README.md       # Documentación específica del benchmark
└── README.md           # Presentación general del repositorio (este archivo)
```

Esta representación muestra **únicamente las rutas confirmadas**; no pretende enumerar todo el contenido del repositorio.

Para los detalles de implementación, requisitos y ejecución del benchmark, consulta la [documentación de DeepTuneIO](DeepTuneIO/README.md).

## Flujo metodológico

El análisis sigue un proceso reproducible:

1. **Diseño experimental:** definición de aplicación, dataset, sistema de archivos y configuración de ejecución.
2. **Ejecución e instrumentación:** recopilación de trazas y métricas de rendimiento.
3. **Procesamiento:** extracción, limpieza y consolidación de evidencias.
4. **Caracterización y diagnóstico:** identificación de patrones, cuellos de botella y posibles episodios de contención.
5. **Modelado y evaluación:** comparación de configuraciones y formulación de estrategias de mejora.
6. **Validación y preservación:** comprobación de resultados, trazabilidad y preparación de evidencias reproducibles.

## Herramientas y tecnologías

Según el componente y la campaña, el proyecto utiliza:

- **Python** para procesamiento de datos, análisis y visualización.
- **Darshan / DXT** para instrumentación y análisis de operaciones de E/S.
- **SLURM** para la gestión de ejecuciones en entornos HPC.
- **TensorFlow / Keras y Horovod** en las cargas de entrenamiento que los requieren.
- **HDF5, JPEG, NPZ y TFRecord** como formatos de almacenamiento de datos.
- **Lustre y NFS** como sistemas de archivos evaluados en distintas campañas.

Las versiones, dependencias y comandos concretos deben consultarse en la documentación del componente correspondiente.

## Primeros pasos

Clona el repositorio:

```bash
git clone https://github.com/ParragaE/PHD_THESIS.git
cd PHD_THESIS
```

Consulta la documentación del benchmark:

```bash
cat DeepTuneIO/README.md
```

**Importante:** no existe un comando universal de ejecución para todos los componentes. Antes de lanzar un experimento, revisa sus dependencias, rutas de datos, configuración HPC y requisitos de instrumentación.

## Reproducibilidad y validación

Para interpretar o reproducir un resultado es importante conservar, cuando estén disponibles:

- Configuración de hardware, software y sistema de archivos.
- Identificadores de ejecución (*JobID*) y parámetros experimentales.
- Trazas originales Darshan/DXT y salidas de procesamiento.
- Métricas de rendimiento y reglas de cálculo.
- Relación entre tablas, figuras y evidencias originales.
- Resultados de validación frente a referencias experimentales (*Golden Reference*).

**Precaución:** no todas las métricas están necesariamente disponibles en todas las trazas; las conclusiones deben distinguir entre operaciones observadas y actividad total de E/S.

## Alcance y limitaciones

Este repositorio es material de investigación y puede contener componentes en evolución. La reproducibilidad de cada experimento depende de la disponibilidad de datasets, permisos de acceso a infraestructura HPC, versiones de bibliotecas y configuración de instrumentación. No se debe asumir que todos los experimentos son ejecutables en un ordenador personal sin adaptación.

## Autoría y contacto

**Autor:** Edixon Párraga  
**Perfil de GitHub:** [ParragaE](https://github.com/ParragaE)  
**Repositorio:** [PHD_THESIS](https://github.com/ParragaE/PHD_THESIS)  
**Área de investigación:** Computación de altas prestaciones (HPC), caracterización y modelado del rendimiento de E/S, sistemas de almacenamiento distribuidos y cargas de inteligencia artificial.

Este repositorio contiene software de investigación, benchmarks experimentales, herramientas de análisis y recursos de reproducibilidad desarrollados en el contexto de la investigación doctoral del autor.

Para consultas técnicas, incidencias o propuestas de mejora, utiliza la sección [Issues](https://github.com/ParragaE/PHD_THESIS/issues), si está habilitada.

## Citación y licencia

Antes de reutilizar resultados o código en publicaciones, consulta las referencias y condiciones de uso asociadas a cada componente. **No se declara aquí una licencia ni una referencia bibliográfica específica** porque no se han verificado en la raíz del repositorio.

---

*Este README ofrece una visión general del proyecto. Para instrucciones detalladas de DeepTuneIO, consulta [`DeepTuneIO/README.md`](DeepTuneIO/README.md).*
