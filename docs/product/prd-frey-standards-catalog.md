# PRD: Frey SPA — Standards Catalog

## Problem

Architects, analysts, and platform operators need a simple way to see which RAG standards have been ingested into the vector database. Today there is no UI to list `standard_id` values; users must rely on backend tools or database access.

## Goals

- Provide a dedicated SPA page that lists all ingested `standard_id` values from the VectorDB API.
- Enable client-side search/filter and copy-to-clipboard for quick reference.
- Surface clear UX states (loading, empty, error, unauthorized) so users understand what is happening.

## Non-Goals

- Viewing standard content, chunks, or source documents.
- Ingestion/management actions (create/update/delete).
- Pagination (unless added by API later).
- Telemetry in v1 (deferred; see Out of Scope).

## Constraints

- Page requires authenticated session (Keycloak).
- API requests require `Authorization: Bearer <access_token>`.
- VectorDB API is served under `/api/tools/vectordb/` and must be proxied correctly by Frey nginx.

## Success Criteria

- Users can open `/rag/standards`, see the list of standard IDs, filter by text, and copy any ID with one click.
- Loading, empty, error, and unauthorized states are clearly communicated.

## Acceptance Criteria

- [ ] **US-1** On page load, calls `GET /api/tools/vectordb/standard-ids` and displays total count + list of IDs, sorted ascending.
- [ ] **US-2** Client-side case-insensitive filter; UI shows filtered result count.
- [ ] **US-3** Copy button per row; confirmation (e.g. "Copied") shown after copy.
- [ ] **US-4** Loading: spinner + "Loading standards…"; Empty: "No standards have been ingested yet."; Error: "Unable to load standards." + Retry; 401: "Session expired—please sign in again."

## Out of Scope

- **Telemetry** (page view, fetch result, copy action): deferred to a follow-up. No telemetry in v1.
- Viewing standard content, chunks, or source documents.
- Ingestion/management actions.

## Test Plan

- **Local (Docker) happy path**: Start Thor tools stack + Frey stack; open `/rag/standards`; verify list loads, filter works, refresh updates "Last refreshed at", copy works.
- **Auth states**: Logged out → "Session expired—please sign in again." + sign-in CTA; expired token → same UX.
- **Error/empty**: Stop vectordb container → error + Retry; empty DB → empty state.

## Rollout / Observability

- Deploy by rebuilding/restarting Frey nginx container so the new `location ^~ /api/tools/vectordb/` is live.
- Verify via nginx access logs + VectorDB API `/health` and endpoint response.

## References

- [Functional Analysis — New Page for Frey SPA](../architecture/Functional%20Analysis%20—%20New%20Page%20for%20Frey%20SPA.md)
