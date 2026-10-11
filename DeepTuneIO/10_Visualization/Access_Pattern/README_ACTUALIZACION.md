# DeepTuneIO Analyzer — Módulo 10 v1.8

Copiar `Module/10_access_pattern_visualization.py` y todos los archivos de `Module/Access_Pattern_Visualization/` a las rutas equivalentes del proyecto. Abrir el notebook actualizado y reiniciar el kernel.

Con `PROFILE="contention"` o `"all"` se generan además:

- `13_exact_range_concurrent_io`: seis ejemplos de pares A con misma región de bytes y tiempo concurrente.
- `14_partial_range_concurrent_io`: seis ejemplos de pares B con intersección parcial.
- `15_shared_resource_concurrent_io`: número de ranks distintos activos en operaciones pertenecientes a pares C. NFS se infiere del escenario.

Cada figura se guarda como PNG y PDF. No son pruebas de degradación de rendimiento. Los ejemplos A/B no son una muestra aleatoria ni sustituyen el CSV. El caso C no mide la cola ni saturación del servidor. Si el detector alcanza `MAX_CONTENTION_PAIRS`, los resultados están truncados; revisar `10_contention_three_cases_diagnostics.json` antes de extraer conclusiones.
