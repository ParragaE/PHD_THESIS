# Input / Processing / Output Matrix

| Stage | Input | Processing | Output |
|---|---|---|---|
| Discovery | campaign `results/` | find PNG/PDF/SVG | figure candidates |
| Logical grouping | figure candidates | collapse same stem | logical figures |
| Provenance | manifests + experiment matrices | resolve JobID/configuration/source | provenance fields |
| Article mapping | logical figure + metadata | deterministic rules | article figure/panel/status |
| Audit | registry | compact projections | provenance/mapping CSVs |

No OCR, plot digitization, pixel similarity, or automatic scientific PASS is performed.
