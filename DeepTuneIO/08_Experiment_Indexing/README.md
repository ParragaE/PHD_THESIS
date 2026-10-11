# DeepTuneIO M08 v1.0.1

## Module
**Experiment Indexing and Metadata Reconstruction**

This is the modularized successor of DeepTuneIO-Indexer v12.1.

### Main package layout

```text
08_Experiment_Indexing/
├── 08_experiment_indexing.ipynb
├── Module/
│   ├── 08_experiment_indexing.py
│   └── Experiment_Indexing/
│       ├── models.py
│       ├── utils.py
│       ├── discovery.py
│       ├── reconstruction.py
│       ├── validation.py
│       ├── signatures.py
│       ├── outputs.py
│       ├── pipeline.py
│       ├── sources/
│       └── adapters/
└── Documentation/
```

### Design

The public entry point is intentionally small. Parsing and application semantics
are isolated from orchestration.

The exact existing validation criterion is preserved:
`execution=PASS AND instrumentation=COMPLETE AND metadata=PASS`.

The exact semantic signature system is preserved.

The v1.0.0 package also preserves the former matrix/coverage/application/training
outputs for compatibility; they are no longer considered the canonical purpose
of the module.


## v1.0.1 fix

Restores the `@dataclass` decorators on `ExperimentRecord` and `ValidationIssue`
that were accidentally lost during the initial modular extraction.

A regression test now verifies that both classes accept keyword arguments as
required by the reconstruction pipeline.
