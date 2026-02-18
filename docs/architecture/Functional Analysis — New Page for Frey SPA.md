# Functional Analysis — Frey SPA — New Page: Standards Catalog (VectorDB)

## 0. Summary
**Objective:** Add a new SPA page that lists all ingested RAG `standard_id` values by calling the VectorDB API endpoint and presenting the IDs with search + copy actions.

**Page name:** Standards Catalog  
**Route:** `/rag/standards`  
**Navigation:** `RAG → Standards Catalog`

---

## 1. Scope

### In scope (v1)
- New route + page in Frey SPA.
- Fetch and display list of `standard_id` values from VectorDB API.
- Client-side search/filter on `standard_id`.
- Copy-to-clipboard action per ID.
- UX states: loading, empty, error, unauthorized.
- Telemetry events (page view, fetch result, copy action).

### Out of scope (v1)
- Viewing standard content, chunks, or source documents.
- Ingestion/management actions (create/update/delete).
- Pagination (unless added by API later).

---

## 2. Users & Permissions

### Personas
- Architect / Analyst / SME: validate what standards exist in the RAG.
- Admin / Platform Ops: verify ingestion coverage.

### Access control
- Page requires authenticated session.
- API requests require `Authorization: Bearer <access_token>`.

---

## 3. User Stories & Acceptance Criteria

### US-1 — View standards list
**As a user**, I can open the page and see the list of available `standard_id` values.
- On page load, calls `GET /api/tools/vectordb/standard-ids`
- Displays:
  - Total count (e.g., `124 standards`)
  - List/table of IDs
- Default sort: ascending by `standard_id` (client-side sort to guarantee deterministic order)

### US-2 — Search/filter
**As a user**, I can filter the list by typing text.
- Filter is case-insensitive contains-match.
- Filtering is client-side; no additional API calls while typing.
- UI shows result count after filtering.

### US-3 — Copy a standard id
**As a user**, I can copy a `standard_id` with one click.
- Copy button per row
- Toast/snackbar confirmation: “Copied”

### US-4 — Resilience & states
**As a user**, I understand what’s happening when loading fails or list is empty.
- Loading: skeleton or spinner + “Loading standards…”
- Empty: “No standards have been ingested yet.”
- Error: “Unable to load standards.” + Retry button
- 401: “Session expired—please sign in again.”

---

## 4. UX / UI Requirements

### Layout
- Header:
  - Title: **Standards Catalog**
  - Subtitle: “Ingested standards available in the RAG vector database”
- Controls row:
  - Search input (label + placeholder: “Filter by ID (e.g., ISO, NIST, STD-)”)
  - Refresh button (forces re-fetch)
- Content:
  - Table/List
    - Column 1: `standard_id`
    - Column 2: Actions (Copy)
- Meta:
  - “Last refreshed at: YYYY-MM-DD HH:mm”

### Accessibility
- Search input has explicit label.
- Copy buttons have `aria-label="Copy standard id <ID>"`.
- Fully keyboard navigable.

---

## 5. API Integration

### Endpoint
`GET /api/tools/vectordb/standard-ids`

### Request headers
- `Authorization: Bearer <ACCESS_TOKEN>`
- `Accept: application/json`

### Response (200)
```json
{
  "items": [
    "STD-ISO-27001-2022",
    "STD-NIST-CSF-2.0"
  ]
}