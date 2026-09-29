# Mapping Driven Knowledge and Dialogue Plan

**Goal:** Route a report to every XLSX named in the uploaded mapping, rank answerable KPI matches inside that report's packages, then search the common package, and return a grounded conversational answer.

**Architecture:** `knowledge_service.py` owns workbook loading, report mappings, similarity ranking, KPI inventory questions and evidence-bound answer wording. `server.py` exposes only a narrow JSON API. `index.html` renders the dialogue and keeps report-scoped question context. `docs/knowledge-system-design.md` records these contracts and source hashes; a checker fails when code changes without a matching design update.

**Constraints:** No other report's specialized package is searched. The report badge cannot appear fully connected when a mapped package or the asked KPI is missing. Neither API nor HTML exposes source filenames, workbook contents, or raw formulas. No external model is called in this version.

### Task 1: Mapping and multi-package loading

- [x] Test actual mapping row, repeated report rows, deduplication, missing files, and rejected paths.
- [x] Parse the mapping workbook and load supported KPI schemas from every mapped package.
- [x] Verify package status and fallback scope.

### Task 2: Similarity ranking

- [x] Test typo retrieval, strongest candidate across packages, period selection, ambiguity, and low-confidence abstention.
- [x] Rank specialized candidates before common candidates; keep previous-question context bounded to the same report.
- [x] Verify every answer comes from a loaded row or a documented rule over loaded rows.

### Task 3: Conversational presentation

- [x] Test the response shape for matched, generic, ambiguous, and unmatched questions.
- [x] Add local evidence-bound phrasing and update the UI to render it.
- [x] Run browser and API regression checks.

### Task 4: Design synchronization

- [x] Write a code-accurate design document with schemas, scores, thresholds, states, response contract, file boundary, and maintenance steps.
- [x] Add a source-hash sync check and CI gate for code/design co-updates.
- [x] Run all tests, browser checks, syntax checks, and design sync validation.
