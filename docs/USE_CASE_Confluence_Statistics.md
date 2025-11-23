# Use Case: Confluence Space Statistics

## Overview

**Feature**: Confluence Space Statistics  
**Version**: 1.6.0  
**User Story**: As a Confluence administrator, I want to view statistics about a Confluence space so that I can understand its usage, size, and contributor activity.

---

## Actors

- **Primary Actor**: Confluence Administrator / Space Manager
- **Secondary Actors**: 
  - Odin Web Portal
  - Odin API Service
  - HashiCorp Vault
  - Confluence Cloud API

---

## Preconditions

1. User has access to Odin web portal (http://localhost/confluence)
2. Confluence credentials are stored in Vault at `secret/confluence/credentials`
3. User has read permissions for the target Confluence space
4. All services (Portal, API, Vault, Confluence) are running and accessible

---

## Basic Flow (Happy Path)

### 1. User Navigates to Statistics Page

**Actor**: User  
**Action**: Opens browser and navigates to http://localhost/confluence  
**System**: Renders Confluence integration page with multiple tabs  
**Result**: User sees "Statistics" tab available

### 2. User Selects Statistics Tab

**Actor**: User  
**Action**: Clicks on "Statistics" tab  
**System**: Displays statistics form with space key input field  
**Result**: Form is ready for input

### 3. User Enters Space Key

**Actor**: User  
**Action**: Types space key (e.g., "AIARC") into the input field  
**System**: Validates input (non-empty, alphanumeric)  
**Result**: Input is accepted

### 4. User Submits Request

**Actor**: User  
**Action**: Clicks "Get Statistics" button  
**System Flow**:

```
Browser (JavaScript)
  ↓ POST /confluence/statistics
  ↓ Body: {space_key: "AIARC"}
  
Web Portal (src/web/routes/confluence.py)
  ↓ Reads config.api_base_url
  ↓ POST http://odin-api:8001/confluence/statistics
  ↓ Body: {space_key: "AIARC"}
  
Odin API (src/api/routes/confluence.py)
  ↓ GET http://vault:8200/v1/secret/data/confluence/credentials
  ↓ Retrieves: base_url, email, api_token
  
Odin API - ConfluenceService
  ↓ Initializes httpx.AsyncClient
  ↓ GET https://[domain].atlassian.net/wiki/rest/api/space/AIARC
  ↓ GET https://[domain].atlassian.net/wiki/rest/api/space/AIARC/content
  ↓ Aggregates statistics from responses
  
Confluence Cloud API
  ↓ Returns space metadata and content list
  
Odin API
  ↓ Calculates: total_pages, total_size_bytes, contributors
  ↓ Returns JSON response
  
Web Portal
  ↓ Forwards JSON to browser
  
Browser (JavaScript)
  ↓ Parses JSON
  ↓ Renders statistics table
```

**Result**: Statistics displayed to user

### 5. System Displays Statistics

**System**: Renders statistics table showing:
- **Space Key**: AIARC
- **Space Name**: AI Architecture
- **Total Pages**: 100
- **Total Size**: 613.8 KB (628,775 bytes)
- **Contributors**: Nicolas.Lallier
- **Last Updated**: 2025-11-02 13:26:57

**Result**: User can view comprehensive space statistics

---

## Alternative Flows

### Alternative Flow 1: Space Not Found

**Trigger**: User enters non-existent space key (e.g., "NOTFOUND")  
**Step**: After step 4 in basic flow

**Flow**:
1. Confluence Cloud API returns 404
2. ConfluenceService raises ResourceNotFoundError
3. API endpoint catches exception, returns HTTP 404
4. Portal receives 404, forwards to browser
5. JavaScript displays error: "Error 404: Space 'NOTFOUND' does not exist"

**Result**: User is informed space doesn't exist

---

### Alternative Flow 2: Missing Vault Credentials

**Trigger**: Confluence credentials not stored in Vault  
**Step**: During step 4 in basic flow

**Flow**:
1. API attempts to read `secret/confluence/credentials` from Vault
2. Vault returns 404 (secret not found)
3. API endpoint returns HTTP 404 with message
4. Portal forwards error to browser
5. JavaScript displays: "Error 404: Confluence credentials not found in Vault"
6. User is directed to setup guide

**Result**: User knows credentials need to be configured

**Recovery**:
```bash
docker exec -i odin-vault sh -c 'export VAULT_ADDR=http://127.0.0.1:8200 && \
export VAULT_TOKEN=dev-root-token && \
vault kv put secret/confluence/credentials \
  base_url="https://domain.atlassian.net/wiki" \
  email="user@example.com" \
  api_token="..."'
```

---

### Alternative Flow 3: Invalid Credentials

**Trigger**: Stored credentials are invalid or expired  
**Step**: During step 4 in basic flow

**Flow**:
1. API retrieves credentials from Vault successfully
2. ConfluenceService makes request to Confluence Cloud
3. Confluence returns 401 Unauthorized
4. ConfluenceService raises ServiceUnavailableError
5. API endpoint returns HTTP 503
6. Portal forwards error to browser
7. JavaScript displays: "Error 503: Authentication failed"

**Result**: User knows credentials need to be updated

---

### Alternative Flow 4: API Service Unavailable

**Trigger**: Odin API service is down or unreachable  
**Step**: During step 4 in basic flow

**Flow**:
1. Portal attempts POST to http://odin-api:8001/confluence/statistics
2. httpx.AsyncClient raises ConnectError
3. Portal catches exception, returns HTTP 503
4. JavaScript displays: "Error 503: Failed to connect to API service"

**Result**: User is informed of service outage

---

### Alternative Flow 5: Confluence Cloud Unavailable

**Trigger**: Confluence Cloud is down or rate-limited  
**Step**: During step 4 in basic flow

**Flow**:
1. ConfluenceService makes request to Confluence Cloud
2. Request times out or returns 503
3. ConfluenceService raises ServiceUnavailableError
4. API endpoint returns HTTP 503
5. Portal forwards error to browser
6. JavaScript displays: "Error 503: Confluence service unavailable"

**Result**: User is informed to try again later

---

### Alternative Flow 6: Large Space (10,000+ Pages)

**Trigger**: User requests statistics for very large space  
**Step**: After step 4 in basic flow

**Flow**:
1. Normal flow proceeds
2. Confluence API pagination kicks in
3. ConfluenceService iterates through all pages
4. Processing takes 30-60 seconds
5. Statistics are aggregated
6. Response returns successfully
7. Large numbers displayed (e.g., 10,543 pages, 500 MB)

**Result**: Statistics displayed correctly even for large spaces

---

## Exception Flows

### Exception Flow 1: Network Timeout

**Trigger**: Request takes longer than 60 seconds  
**System**:
1. httpx timeout (60s) expires
2. TimeoutException raised
3. Portal returns 503
4. Error displayed to user

**Recovery**: User can retry request

---

### Exception Flow 2: Invalid JSON Response

**Trigger**: API returns malformed JSON  
**System**:
1. Portal attempts to parse response.json()
2. JSONDecodeError raised
3. Portal returns 500
4. Error displayed to user

**Recovery**: Log error, contact support

---

## Postconditions

### Success Postconditions

1. Statistics are displayed accurately in browser
2. No changes made to Confluence (read-only operation)
3. HTTP connections properly closed
4. ConfluenceService cleaned up (close() called)

### Failure Postconditions

1. Clear error message displayed to user
2. No partial/incorrect data shown
3. HTTP connections properly closed
4. System ready for retry

---

## Data Requirements

### Input Data

**StatisticsRequest**:
```json
{
  "space_key": "string (required, 1-255 chars, alphanumeric + dash/underscore)"
}
```

### Output Data (Success)

**StatisticsResponse**:
```json
{
  "space_key": "AIARC",
  "space_name": "AI Architecture",
  "total_pages": 100,
  "total_size_bytes": 628775,
  "contributors": ["Nicolas.Lallier", "..."],
  "last_updated": "2025-11-02T13:26:57.022Z"
}
```

### Output Data (Error)

**ErrorResponse**:
```json
{
  "detail": "Error description string"
}
```

---

## Performance Requirements

- **Response Time**: < 5 seconds for typical spaces (< 1000 pages)
- **Large Spaces**: < 60 seconds for spaces with 10,000+ pages
- **Timeout**: 60 second timeout enforced
- **Concurrent Requests**: Support 10+ simultaneous statistics requests

---

## Security Requirements

1. **Credential Storage**: Credentials stored only in Vault, never in code
2. **API Access**: Only API service can access Vault credentials
3. **Portal Isolation**: Portal never directly contacts Confluence
4. **HTTPS**: All Confluence API calls use HTTPS
5. **Authentication**: API token-based auth (not username/password)
6. **No Logging of Secrets**: Credentials never logged

---

## Testing Requirements

### Unit Tests (tests/unit/api/routes/test_confluence_statistics.py)

- ✅ Test successful statistics retrieval
- ✅ Test empty space (0 pages)
- ✅ Test large space (10,000+ pages)
- ✅ Test space not found (404)
- ✅ Test missing Vault credentials (404)
- ✅ Test invalid credentials (503)
- ✅ Test Confluence API error (500)
- ✅ Test service unavailable (503)
- ✅ Test service cleanup on error

### Integration Tests (tests/integration/web/test_confluence_statistics.py)

- ✅ Test portal → API communication
- ✅ Test error propagation through layers
- ✅ Test API unreachable scenario
- ✅ Test timeout handling
- ✅ Test E2E flow (browser → Confluence → browser)
- ✅ Test large response handling

### Regression Tests

- ✅ Test Vault credentials missing returns 404 (not 500)
- ✅ Test all statistics fields present in response
- ✅ Test service cleanup on error
- ✅ Test Unicode in space names
- ✅ Test API URL construction (no double prefix)
- ✅ Test error detail extraction

---

## User Interface

### Statistics Form

```
┌─────────────────────────────────────────┐
│         Confluence Statistics            │
├─────────────────────────────────────────┤
│                                          │
│  Space Key: [AIARC              ]       │
│                                          │
│  [ Get Statistics ]                     │
│                                          │
└─────────────────────────────────────────┘
```

### Statistics Display

```
┌─────────────────────────────────────────┐
│         Statistics Results               │
├─────────────────────────────────────────┤
│  Space Key:       AIARC                  │
│  Space Name:      AI Architecture        │
│  Total Pages:     100                    │
│  Total Size:      613.8 KB               │
│  Contributors:    Nicolas.Lallier        │
│  Last Updated:    2025-11-02 13:26:57   │
└─────────────────────────────────────────┘
```

---

## Related Use Cases

- **UC-CF-001**: Convert Confluence Page to Markdown
- **UC-CF-002**: Convert Markdown to Confluence Page
- **UC-CF-003**: Summarize Confluence Page
- **UC-CF-004**: Backup Confluence Space
- **UC-CF-005**: View Confluence Statistics (this document)

---

## Business Rules

1. **Read-Only**: Statistics endpoint never modifies Confluence data
2. **No Caching**: Always fetch fresh data from Confluence
3. **Access Control**: Respect Confluence permissions (users can only see spaces they have access to)
4. **Rate Limiting**: Respect Confluence API rate limits (automatic retry with backoff)
5. **Data Privacy**: Don't log page content, only metadata

---

## Acceptance Criteria

### Feature Acceptance

- [ ] User can view statistics for any accessible space
- [ ] Statistics include: space key, name, page count, size, contributors, last updated
- [ ] Empty spaces (0 pages) handled correctly
- [ ] Large spaces (10,000+ pages) handled correctly
- [ ] Clear error messages for all failure scenarios
- [ ] Response time < 5s for typical spaces
- [ ] All data displayed in human-readable format (KB/MB for size)

### Technical Acceptance

- [ ] Portal never directly contacts Confluence (only through API)
- [ ] All requests flow through Odin API
- [ ] Credentials retrieved from Vault only
- [ ] Proper error handling at each layer
- [ ] HTTP connections properly closed
- [ ] Unit test coverage > 90%
- [ ] Integration tests pass
- [ ] Regression tests pass
- [ ] No linter errors
- [ ] Type hints on all functions

---

## Change History

| Version | Date       | Author           | Description                    |
|---------|------------|------------------|--------------------------------|
| 1.0     | 2025-11-23 | Nicolas Lallier  | Initial use case documentation |
| 1.1     | 2025-11-23 | Nicolas Lallier  | Added regression test cases    |
| 1.2     | 2025-11-23 | Nicolas Lallier  | Architecture refactoring notes |

---

## Notes

- This use case follows the architecture principle: **Portal → API → External Services**
- The portal is a thin client with no business logic
- All Confluence operations are centralized in the API service
- This design enables multiple frontends (web, CLI, mobile) to use the same API

