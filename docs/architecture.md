# Architecture

This page documents the current repository architecture and extension seams.

## System Boundaries

Primary responsibilities are split across:
- Ingestion and harmonization of NHANES and BRFSS sources
- Validation and reproducibility support
- Pesticide analyte snippet extraction
- Experimental RAG retrieval over snippet corpora
- Documentation and app-level interaction surfaces

## High-Level Component Map

```text
            +---------------------------+
            | External Data Sources     |
            | - CDC NHANES XPT/HTML     |
            | - BRFSS APIs/files        |
            | - Pesticide raw text      |
            +-------------+-------------+
                          |
                          v
  +------------------------------------------------------+
  | pophealth_observatory package                        |
  |------------------------------------------------------|
  | observatory.py -> orchestration facade               |
  | nhanes_data_access.py -> URL + resilient download    |
  | nhanes_transforms.py -> harmonization transforms     |
  | nhanes_manifest_service.py -> manifest normalization |
  | nhanes_analysis_service.py -> analysis/reporting     |
  | core/nhanes_adapters.py -> protocol composition      |
  | logging_config.py -> centralized logger              |
  +----------------------------+-------------------------+
                          |
          +---------------+----------------+
          |                                |
          v                                v
 +---------------------+          +----------------------+
 | Artifacts           |          | Consumer Surfaces    |
 | - manifests/*.json  |          | - apps/streamlit_app |
 | - data/processed/*  |          | - notebooks/*        |
 | - caches            |          | - examples/demo.py   |
 +---------------------+          +----------------------+
```

## Package-Level Responsibilities

| Module | Responsibility | Key Contract Surface |
|--------|----------------|----------------------|
| `observatory.py` | NHANES orchestration facade over service modules | `NHANESExplorer` public methods |
| `nhanes_data_access.py` | NHANES URL pattern generation and resilient XPT download | `build_nhanes_xpt_url_patterns`, `try_download_xpt` |
| `nhanes_transforms.py` | Demographics, BMI, and blood pressure harmonization transforms | `harmonize_*` transform helpers |
| `nhanes_manifest_service.py` | NHANES component-table fetch/parse/normalize utilities | manifest parsing and normalization helpers |
| `nhanes_analysis_service.py` | Analysis helpers, visualization, and summary reporting | analysis/report helper functions |
| `core/nhanes_adapters.py` | Protocol-based composition layer for data + analysis runners | `NHANESDataProviderAdapter`, `NHANESAnalysisAdapter` |
| `core/nhanes_reporting_adapters.py` | Reporting and validation adapter layer | reporting/validation adapter implementations |
| `logging_config.py` | Centralized logging bootstrap and migration helper | `configure_logging`, `log_with_fallback` |
| `brfss.py` | State-level indicator retrieval and filtering | `BRFSSExplorer` |
| `validation.py` | Data integrity and consistency checks | validation helpers + report outputs |
| `laboratory_pesticides.py` | Laboratory pesticide analyte harmonization | pesticide lab loaders |
| `pesticide_ingestion.py` | Text segmentation and analyte snippet extraction | `generate_snippets`, `write_snippets` |
| `pesticide_context.py` | Reference analyte loading and normalization | context/reference loaders |
| `rag/` | Embedding, index/cache handling, retrieval and prompt assembly | `RAGPipeline`, embedder interfaces |
| `core/protocols.py` | Protocol contracts for extensibility | `DataProvider`, `AnalysisRunner`, `ReportGenerator`, `IndicatorProvider` |

## Data Flow: NHANES Path

```text
Cycle request
  -> component URL resolution
  -> multi-attempt download with timeout
  -> XPT parse into DataFrame
  -> standardized column mapping
  -> derived metrics (BMI/BP labels)
  -> participant_id keyed merges
  -> validation/reporting
  -> analysis/app rendering
```

## Data Flow: Pesticide Snippet + RAG Path

```text
Raw pesticide text
  -> sentence segmentation
  -> regex analyte pattern matching
  -> snippet dataclass materialization
  -> JSONL serialization
  -> embedding generation/cache
  -> similarity retrieval (top_k)
  -> prompt formatting
  -> external generator callback
```

## Current Extension Seams

1. Add new NHANES component loaders using existing harmonization patterns.
2. Extend protocol-based abstractions in `core/protocols.py` for modular decomposition.
3. Add retrieval backends in `rag/` without changing prompt assembly contract.
4. Expand validation checks while preserving stable report schema.

## Architecture Constraints

1. Keep retrieval logic decoupled from generation callbacks.
2. Preserve explicit failure behavior (empty DataFrame fallback for acquisition failures).
3. Prefer structured artifacts (JSON/JSONL; planned Parquet for broader interchange).
4. Avoid introducing global mutable singletons beyond scoped caches.

## Decomposition Outcome

The decomposition plan is complete for the NHANES orchestration path.

- Previously monolithic responsibilities in `observatory.py` were split into focused service modules.
- Public API behavior remains stable via adapter-backed composition and compatibility shims.
- Protocol contracts in `core/protocols.py` now define extension seams independent of concrete implementations.
- Centralized package logging in `logging_config.py` now provides a shared diagnostic path across modules.

Net effect: smaller testable units, clearer ownership boundaries, and lower-risk feature extension for 1.x.

## Concrete Decomposition Slices

The recommended implementation order keeps risk low and preserves existing public APIs.

1. Completed: extract NHANES URL pattern + resilient XPT download helpers
  - New module: `pophealth_observatory/nhanes_data_access.py`
  - Call sites updated: `PopHealthObservatory.download_data`, `NHANESExplorer.get_demographics_data`
2. Completed: extract harmonization transforms into dedicated functions
  - Demographics column mapping and label derivations
  - Body measures BMI categorization
  - Blood pressure averaging and stage classification
3. Completed: extract manifest scraping pipeline into a focused service module
  - Fetch, parse, normalize, filter, summarize
  - Keep `NHANESExplorer.get_detailed_component_manifest` as thin orchestration facade
4. Completed: split reporting/analysis helpers from ingestion class
  - `analyze_by_demographics`, visualization, summary reporting
  - Move toward composition over inheritance for explorer workflows
5. Completed: adapter layer over protocol contracts
  - Introduce provider objects implementing protocol interfaces
  - Keep compatibility shims for root imports while deprecating legacy access paths
6. Completed: validation/report orchestration extraction
  - Introduce report and validation adapters implementing protocol-backed composition
  - Delegate `NHANESExplorer.validate` and summary reporting via report adapter

### What Protocol Contracts Enable

1. Swap implementation details without changing public explorer APIs.
2. Test modules in isolation with lightweight adapter or provider doubles.
3. Add new data providers and reporting strategies without inheritance coupling.
4. Keep orchestration classes thin while preserving backwards compatibility.

## Next Hardening Slices

1. Completed: compatibility cleanup and deprecation tightening
  - Remove redundant internal indirection where compatibility is no longer needed
  - Keep explicit, documented adapter defaults for constructor injection points
  - Tighten root export shim deprecation warnings with explicit removal-version guidance
2. Completed: architecture drift guardrails in CI
  - Maintain targeted contract tests for protocol-backed adapters
  - Add focused coverage expectations for decomposition modules (CI fail-under for decomposition slice)
