# Confluence Integration Architecture (v1.6.0)

## Executive Summary

The Confluence integration in Odin v1.6.0 follows a **strict three-tier architecture** where the web portal acts as a thin client that **never directly contacts external services**. All operations flow through the Odin API service, which serves as the central hub for all business logic and external integrations.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          USER BROWSER                                    │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   │ HTTP (port 80)
                                   ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                        WEB PORTAL (Thin Client)                          │
│                                                                           │
│  • Serves HTML/CSS/JavaScript                                            │
│  • Handles user interactions                                             │
│  • Routes ALL requests to API                                            │
│  • No business logic                                                     │
│  • No direct external service access                                     │
│                                                                           │
│  Routes:                                                                 │
│    GET  /confluence                  → Render UI                         │
│    POST /confluence/convert-to-markdown → Proxy to API                   │
│    POST /confluence/convert-from-markdown → Proxy to API                 │
│    POST /confluence/summarize        → Proxy to API                      │
│    POST /confluence/backup-space     → Proxy to API                      │
│    POST /confluence/statistics       → Proxy to API                      │
│    GET  /confluence/models           → Proxy to API                      │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   │ HTTP (internal network)
                                   ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                    ODIN API SERVICE (Business Logic Hub)                 │
│                                                                           │
│  • All business logic lives here                                         │
│  • Manages all external service integrations                             │
│  • Handles authentication and authorization                              │
│  • Performs data transformations                                         │
│  • Enforces security policies                                            │
│                                                                           │
│  Confluence Endpoints:                                                   │
│    POST /api/confluence/convert-to-markdown                              │
│    POST /api/confluence/convert-from-markdown                            │
│    POST /api/confluence/summarize                                        │
│    POST /api/confluence/backup-space                                     │
│    POST /api/confluence/statistics                                       │
│    POST /api/confluence/backup-file (internal)                           │
│    GET  /api/confluence/models                                           │
│                                                                           │
│  Services:                                                               │
│    • ConfluenceService  → Confluence Cloud API client                    │
│    • VaultService       → Credential management                          │
│    • StorageService     → MinIO object storage                           │
│    • OllamaService      → LLM integration                                │
└─────────────────────────────────────────────────────────────────────────┘
        │                │                │                │
        │                │                │                │
        ↓                ↓                ↓                ↓
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  Confluence  │ │   Vault      │ │   MinIO      │ │   Ollama     │
│  Cloud API   │ │ (port 8200)  │ │ (port 9000)  │ │ (port 11434) │
│  (HTTPS)     │ │              │ │              │ │              │
│              │ │ Credentials  │ │ File Storage │ │ LLM Models   │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
```

## Design Principles

### 1. Separation of Concerns

**Web Portal (Presentation Layer)**
- **Responsibility**: User interface and experience
- **What it does**: Render HTML, handle form submissions, display results
- **What it does NOT do**: Business logic, external service calls, data transformation
- **Technology**: FastAPI, Jinja2 templates, vanilla JavaScript

**Odin API (Business Logic Layer)**
- **Responsibility**: All application logic and external integrations
- **What it does**: 
  - Validate requests
  - Retrieve credentials from Vault
  - Call Confluence Cloud API
  - Transform data formats
  - Store backups in MinIO
  - Generate LLM summaries
- **Technology**: FastAPI, httpx, service layer pattern

**External Services (Data Layer)**
- **Confluence Cloud**: Source data (pages, spaces, content)
- **Vault**: Secure credential storage
- **MinIO**: Object storage for backups and exports
- **Ollama**: LLM inference for summarization

### 2. Single Source of Truth

- **Credentials**: Stored ONLY in HashiCorp Vault
- **Business Logic**: Implemented ONLY in API service
- **State Management**: ONLY in API layer (portal is stateless)

### 3. Security by Design

- **No Credentials in Code**: All secrets stored in Vault
- **Credential Access Control**: Only API service can read Vault secrets
- **Least Privilege**: Web portal has no direct access to external services
- **Authentication Flow**: Portal → API → Vault → Credentials → Confluence

### 4. Testability

Each layer can be tested independently:

- **Portal Tests**: Mock API responses
- **API Tests**: Mock external services (Confluence, Vault, MinIO, Ollama)
- **Integration Tests**: Test entire flow end-to-end

## Data Flow Examples

### Example 1: Convert Page to Markdown

```
1. User clicks "Convert" in browser
   ↓
2. JavaScript sends POST to /confluence/convert-to-markdown
   ↓
3. Web Portal receives request
   ↓
4. Portal forwards to API: POST http://api:8001/api/confluence/convert-to-markdown
   ↓
5. API retrieves credentials from Vault
   ↓
6. API creates ConfluenceService instance
   ↓
7. ConfluenceService calls Confluence Cloud API
   ↓
8. API converts HTML to Markdown
   ↓
9. API optionally saves to MinIO (via StorageService)
   ↓
10. API returns JSON response to Portal
    ↓
11. Portal returns JSON response to Browser
    ↓
12. JavaScript displays Markdown in UI
```

### Example 2: Backup Space

```
1. User clicks "Backup Space" in browser
   ↓
2. JavaScript sends POST to /confluence/backup-space
   ↓
3. Web Portal receives request
   ↓
4. Portal forwards to API: POST http://api:8001/api/confluence/backup-space
   ↓
5. API retrieves credentials from Vault
   ↓
6. API creates ConfluenceService instance
   ↓
7. ConfluenceService calls Confluence to list all pages in space
   ↓
8. For each page:
   - ConfluenceService retrieves page content
   - API stores in MinIO (via StorageService)
   ↓
9. API returns backup summary to Portal
   ↓
10. Portal returns summary to Browser
    ↓
11. JavaScript displays success message with stats
```

### Example 3: Summarize Page with LLM

```
1. User clicks "Summarize" in browser
   ↓
2. JavaScript sends POST to /confluence/summarize
   ↓
3. Web Portal receives request
   ↓
4. Portal forwards to API: POST http://api:8001/api/confluence/summarize
   ↓
5. API retrieves Confluence credentials from Vault
   ↓
6. API creates ConfluenceService instance
   ↓
7. ConfluenceService retrieves page from Confluence
   ↓
8. ConfluenceService converts page to Markdown
   ↓
9. API calls OllamaService to generate summary
   ↓
10. OllamaService sends prompt to Ollama
    ↓
11. Ollama generates summary
    ↓
12. API returns summary to Portal
    ↓
13. Portal returns summary to Browser
    ↓
14. JavaScript displays summary in UI
```

## File Structure

### API Service (`src/api/`)

```
src/api/
├── routes/
│   └── confluence.py          # ALL Confluence business logic endpoints
│       ├── POST /confluence/convert-to-markdown
│       ├── POST /confluence/convert-from-markdown
│       ├── POST /confluence/summarize
│       ├── POST /confluence/backup-space
│       ├── POST /confluence/statistics
│       ├── POST /confluence/backup-file (internal)
│       └── GET  /confluence/models
│
├── services/
│   ├── confluence.py          # Confluence Cloud API client
│   │   ├── ConfluenceService
│   │   ├── get_page_by_id()
│   │   ├── convert_page_to_markdown()
│   │   ├── convert_markdown_to_storage()
│   │   ├── create_or_update_page()
│   │   ├── backup_space()
│   │   └── get_space_statistics()
│   │
│   ├── vault.py               # Vault credential management
│   ├── storage.py             # MinIO object storage
│   └── ollama.py              # LLM service integration
│
└── exceptions.py
    └── ConfluenceError        # Custom exception for Confluence operations
```

### Web Portal (`src/web/`)

```
src/web/
├── routes/
│   └── confluence.py          # Thin proxy layer (NO business logic)
│       ├── GET  /confluence                    → Render UI
│       ├── POST /confluence/convert-to-markdown → Proxy to API
│       ├── POST /confluence/convert-from-markdown → Proxy to API
│       ├── POST /confluence/summarize         → Proxy to API
│       ├── POST /confluence/backup-space      → Proxy to API
│       ├── POST /confluence/statistics        → Proxy to API
│       └── GET  /confluence/models            → Proxy to API
│
├── templates/
│   └── confluence.html        # Multi-tab UI for all operations
│
└── static/js/
    └── confluence.js          # Client-side form handling and AJAX
```

## API Contracts

All API endpoints are fully documented with Pydantic models for request/response validation.

### Request Models

```python
class ConvertToMarkdownRequest(BaseModel):
    page_id: str
    save_to_storage: bool = False

class ConvertFromMarkdownRequest(BaseModel):
    space_key: str
    title: str
    markdown: str
    parent_id: str | None = None

class SummarizePageRequest(BaseModel):
    page_id: str
    model: str | None = None  # Default: mistral:latest

class BackupSpaceRequest(BaseModel):
    space_key: str
    format: str = "html"

class StatisticsRequest(BaseModel):
    space_key: str
```

### Response Models

```python
class ConvertToMarkdownResponse(BaseModel):
    markdown: str
    saved_path: str | None = None

class ConvertFromMarkdownResponse(BaseModel):
    page_id: str
    title: str
    url: str

class SummarizePageResponse(BaseModel):
    summary: str
    page_title: str

class BackupSpaceResponse(BaseModel):
    bucket: str
    path: str
    page_count: int

# Statistics response: dict[str, Any] (dynamic structure)

class ModelsResponse(BaseModel):
    models: list[dict[str, Any]]
```

## Benefits of This Architecture

### ✅ Maintainability

- Clear separation of concerns makes code easier to understand
- Changes to business logic don't affect UI code
- Each layer can be refactored independently

### ✅ Security

- Credentials stored in Vault, never in code
- Only API service has access to sensitive operations
- Web portal is a public-facing thin client with no secrets

### ✅ Testability

- Each layer can be unit tested in isolation
- Mock external services for fast, reliable tests
- Integration tests verify end-to-end workflows

### ✅ Scalability

- API service can be scaled independently
- Portal can be cached/CDN-distributed
- External services can be replaced without affecting portal

### ✅ Flexibility

- Easy to add new Confluence operations (just add API endpoints)
- Can support multiple frontends (web, CLI, mobile) using same API
- Can swap external services (e.g., different LLM provider)

## Configuration

### Environment Variables

**Web Portal:**
```bash
API_BASE_URL=http://api:8001/api
```

**API Service:**
```bash
VAULT_ADDR=http://vault:8200
VAULT_TOKEN=dev-root-token
OLLAMA_BASE_URL=http://ollama:11434
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
```

### Vault Secret Structure

```bash
# Path: secret/confluence/credentials
vault kv put secret/confluence/credentials \
  base_url="https://your-domain.atlassian.net/wiki" \
  email="your-email@example.com" \
  api_token="your-api-token"
```

## Error Handling

Errors propagate cleanly through the layers:

```
External Service Error
  ↓
API catches and wraps in HTTPException
  ↓
Portal receives HTTP error
  ↓
Portal forwards error to browser
  ↓
JavaScript displays error message
```

Example error flow:

```python
# In API (src/api/routes/confluence.py):
try:
    result = await confluence_service.get_page_by_id(page_id)
except ConfluenceError as e:
    raise HTTPException(status_code=500, detail=str(e.message))

# In Portal (src/web/routes/confluence.py):
try:
    response = await client.post(f"{api_base_url}/confluence/...", ...)
    if not response.is_success:
        error_detail = response.json().get("detail", response.text)
        raise HTTPException(status_code=response.status_code, detail=error_detail)
except httpx.RequestError as e:
    raise HTTPException(status_code=503, detail=f"Failed to connect to API: {str(e)}")

# In JavaScript (confluence.js):
.catch(error => {
    showError(`Operation failed: ${error.message}`);
});
```

## Future Enhancements

### Potential Additions

1. **Caching Layer**: Add Redis for caching Confluence API responses
2. **Rate Limiting**: Implement rate limiting in API to respect Confluence API limits
3. **Webhook Support**: Add webhook endpoint to receive Confluence events
4. **Batch Operations**: Support bulk operations on multiple pages
5. **Search Integration**: Add Confluence search functionality
6. **Template Management**: Manage Confluence page templates
7. **User Permissions**: Mirror Confluence permissions in Odin

### Architecture Considerations

Any future enhancements should maintain the core principles:

- ✅ Portal remains a thin client (no business logic)
- ✅ All operations go through API service
- ✅ Credentials stay in Vault
- ✅ External services never accessed directly from portal

## Conclusion

The Confluence integration in Odin v1.6.0 demonstrates a **clean, maintainable, and secure architecture** that follows industry best practices:

- **Three-tier architecture** with clear separation of concerns
- **API-first design** enabling multiple client types
- **Secure credential management** via HashiCorp Vault
- **Service layer pattern** for business logic encapsulation
- **Stateless web portal** acting as a thin client

This architecture provides a solid foundation for future enhancements while maintaining code quality, security, and maintainability.

