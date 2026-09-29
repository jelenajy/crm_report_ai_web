# Knowledge Package Routing Implementation Plan

> **For agentic workers:** Implement inline in this session with test-first checkpoints.

**Goal:** Answer KPI questions from the selected report's package, then the common package, while keeping source files and document metadata off the public page.

**Architecture:** A Python service reads XLSX files on each request and exposes only report status and concise answers. The static page calls that service and never embeds the knowledge records. Production can use `KNOWLEDGE_DIR` for private storage.

**Tech Stack:** Python standard library, OOXML, HTML, JavaScript, unittest.

## Global Constraints

- Search exactly two scopes: the selected report's package, then the common package.
- Missing selected package always displays `知识包未接入` even if a common KPI answers the question.
- Do not serve XLSX files, source document names, raw formulas, or citations to the browser.
- Return an explicit no-answer response for unsupported or ambiguous questions.

---

### Task 1: Server-side knowledge routing

**Files:** Create `knowledge_service.py`; test `tests/test_knowledge.py`; read branch files locally and use `KNOWLEDGE_DIR` for private deployment storage.

- [x] Write tests for precedence, fallback, pending status, ambiguity, and response boundaries.
- [x] Run tests and observe the missing module failure.
- [x] Parse both workbooks and implement exact report scope routing.
- [x] Run unit tests until green.

### Task 2: Public API and UI

**Files:** Create `server.py`; modify `index.html`, `outputs/crm_report_ai_web/index.html`, `README.md`.

- [x] Add API tests that prove XLSX paths are inaccessible and public JSON omits source metadata.
- [x] Expose only `/`, `/api/reports`, and `/api/answer`.
- [x] Replace client-side answer table and citation controls with API calls and safe answer rendering.
- [x] Run the focused tests and browser smoke checks.
