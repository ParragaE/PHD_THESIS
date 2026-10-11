# DeepTuneIO Analyzer — Contention Analysis v8

Instalar `Contention_Analysis/` junto a `Access_Pattern/` en `10_Visualization/`.
Abrir `Contention_Analysis.ipynb`, configurar la campaña y ejecutar todas las celdas.

**Correcciones v8:** los subtítulos no muestran `auto` y utilizan `data_loading_mode` cuando existe; incluyen filesystem y los metadatos disponibles (epochs, batch size, transfer size, chunking y filtros) sin inventar valores. Se elimina `Not measured slowdown` de los títulos. El límite de pares por defecto es 900000; el detector informa si trunca. El notebook imprime rutas completas y un manifiesto `contention_figures_manifest.json` registra los PNG.

Los mapas de calor de concurrencia son evidencias de coincidencias, no una medición causal de degradación.
