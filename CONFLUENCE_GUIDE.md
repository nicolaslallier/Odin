# Confluence Integration Guide

## Overview

The Odin Confluence integration (v1.6.0) provides a web interface for managing Confluence Cloud pages, including:

1. **Page to Markdown Conversion** - Export Confluence pages as Markdown files
2. **Markdown to Page Publishing** - Create/update Confluence pages from Markdown
3. **LLM Page Summarization** - Summarize pages using Ollama LLM models
4. **Space Backup** - Backup entire Confluence spaces to MinIO storage
5. **Space Statistics** - View analytics for Confluence spaces

## Architecture

The Confluence integration follows a clean three-tier architecture:

```
┌──────────────────┐         ┌──────────────────┐         ┌──────────────────┐
│   Web Portal     │ ───────→│   Odin API       │ ───────→│   Confluence     │
│   (port 80)      │  HTTP   │   (port 8001)    │  HTTPS  │   Cloud API      │
└──────────────────┘         └──────────────────┘         └──────────────────┘
                                       │
                                       ├──────────→ HashiCorp Vault (credentials)
                                       ├──────────→ MinIO (storage)
                                       └──────────→ Ollama (LLM)
```

**Key Design Principles:**

- **Web Portal Never Contacts Confluence Directly**: All Confluence operations go through the Odin API
- **API as Central Hub**: The API service manages all external integrations (Confluence, Vault, MinIO, Ollama)
- **Separation of Concerns**: Web portal handles UI/UX, API handles business logic and external services
- **Secure Credential Management**: Credentials are stored in Vault and only accessed by the API service
- **Stateless Architecture**: Portal is a thin client; all state management happens in the API layer

## Features

### ✨ Key Capabilities

- **Bidirectional Conversion**: Convert between Confluence and Markdown formats
- **LLM-Powered Summaries**: Automatically summarize pages using local LLM models
- **Bulk Operations**: Backup entire spaces with a single click
- **Storage Integration**: Save converted content to MinIO object storage
- **Analytics**: Get insights into space usage and contributors

### 🔒 Security

- Credentials stored securely in HashiCorp Vault
- API token authentication for Confluence Cloud
- No passwords stored in code or configuration files

## Prerequisites

### Required Services

1. **HashiCorp Vault** - For secure credential storage
2. **MinIO** - For file storage (backups, exports)
3. **Ollama** - For LLM-based summarization
4. **Confluence Cloud** - Source Confluence instance

### Confluence API Token

You need a Confluence Cloud API token:

1. Go to: https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Give it a name (e.g., "Odin Integration")
4. Copy the token (you won't see it again!)

## Setup Instructions

### Step 1: Configure Credentials in Vault

Store your Confluence credentials in Vault:

```bash
# Set Vault environment variables
export VAULT_ADDR=http://localhost:8200
export VAULT_TOKEN=dev-only-token  # Use your actual token

# Store Confluence credentials (note: 'secret' is the mount point for KV v2)
vault kv put secret/confluence/credentials \
  base_url="https://your-domain.atlassian.net/wiki" \
  email="your-email@example.com" \
  api_token="your-api-token-here"

# Verify the secret was stored correctly
vault kv get secret/confluence/credentials
```

**Important Notes:**
- `base_url` should include `/wiki` suffix
- `email` is your Atlassian account email
- `api_token` is the token you created above

### Step 2: Verify Services are Running

```bash
# Check all services
docker-compose ps

# Should see: vault, minio, ollama running
```

### Step 3: Pull Recommended LLM Model

For page summarization, we recommend `mistral:latest`:

```bash
# Pull the model
docker exec -it odin-ollama ollama pull mistral:latest

# Verify it's available
docker exec -it odin-ollama ollama list
```

**Alternative Models:**
- `llama3.2:latest` - Faster, lighter (3B parameters)
- `llama2:latest` - Good balance of speed and quality
- `phi:latest` - Very fast, smaller model

### Step 4: Access the Interface

Navigate to: http://localhost/confluence

## Usage Guide

### 1️⃣ Page to Markdown Conversion

Convert Confluence pages to clean Markdown format.

**Steps:**
1. Go to the "Page to Markdown" tab
2. Enter the Confluence page ID
   - Find it in the URL: `.../pages/123456/Page+Title` → `123456`
3. Optionally check "Save to MinIO storage"
4. Click "Convert to Markdown"

**Output:**
- Markdown content displayed in the interface
- If saved, stored in MinIO bucket: `confluence-markdown`

**Use Cases:**
- Export documentation for version control (Git)
- Create backups in human-readable format
- Migrate content to other platforms

### 2️⃣ Markdown to Page Publishing

Create or update Confluence pages from Markdown content.

**Steps:**
1. Go to the "Markdown to Page" tab
2. Enter:
   - **Space Key**: e.g., `PROJ`, `TEAM`, `DOC`
   - **Page Title**: Title for the page
   - **Markdown Content**: Your markdown text
   - **Parent Page ID** (optional): To create child pages
3. Click "Create/Update Page"

**Output:**
- Page ID and URL of created/updated page
- Link to view the page in Confluence

**Use Cases:**
- Publish documentation from Git repositories
- Automate page updates from CI/CD pipelines
- Bulk import content from external sources

**Markdown Support:**
- Headings (# ## ###)
- Lists (ordered and unordered)
- Code blocks with syntax highlighting
- Tables
- Bold, italic, links
- Images (by URL)

### 3️⃣ Page Summarization

Generate concise summaries of Confluence pages using LLM.

**Steps:**
1. Go to the "Summarize Page" tab
2. Enter the Confluence page ID
3. Select LLM model (or use default: `mistral:latest`)
4. Click "Summarize Page"

**Output:**
- AI-generated summary highlighting:
  - Key points
  - Important decisions
  - Action items
  - Technical details

**Use Cases:**
- Quick overview of long documentation
- Meeting notes summaries
- Technical specification briefs
- Executive summaries

**Performance:**
- First request may be slow (model download)
- Typical time: 10-30 seconds depending on page length
- Longer pages = longer processing time

### 4️⃣ Space Backup

Backup entire Confluence spaces to object storage.

**Steps:**
1. Go to the "Backup Space" tab
2. Enter the **Space Key** (e.g., `PROJ`)
3. Select format (currently HTML only)
4. Click "Backup Space"

**Output:**
- All pages saved to MinIO bucket: `confluence-backups`
- Organized by space key and timestamp
- Path format: `{space_key}/{timestamp}/{page_id}_{title}.html`

**Example:**
```
confluence-backups/
  PROJ/
    20250115_143000/
      123456_Architecture_Design.html
      123457_API_Documentation.html
      ...
```

**Use Cases:**
- Disaster recovery
- Compliance and archival
- Migration preparation
- Offline documentation access

**Important:**
- Preserves original HTML format
- Includes all page metadata
- Does not backup attachments (files, images)

### 5️⃣ Space Statistics

View analytics and metrics for Confluence spaces.

**Steps:**
1. Go to the "Statistics" tab
2. Enter the **Space Key**
3. Click "Get Statistics"

**Output:**
- **Total Pages**: Number of pages in space
- **Total Size**: Combined size of all content
- **Contributors**: Unique list of page authors
- **Last Updated**: Most recent page modification

**Use Cases:**
- Space health monitoring
- Contributor activity tracking
- Content audit preparation
- Growth analysis

## API Reference

All endpoints are accessible programmatically:

### Convert Page to Markdown

```bash
POST /confluence/convert-to-markdown
Content-Type: application/json

{
  "page_id": "123456",
  "save_to_storage": false
}
```

**Response:**
```json
{
  "markdown": "# Page Title\n\nContent...",
  "saved_path": "confluence-markdown/page_123456_20250115.md"
}
```

### Create/Update Page from Markdown

```bash
POST /confluence/convert-from-markdown
Content-Type: application/json

{
  "space_key": "PROJ",
  "title": "New Page",
  "markdown": "# Heading\n\nContent...",
  "parent_id": null
}
```

**Response:**
```json
{
  "page_id": "789012",
  "title": "New Page",
  "url": "https://your-domain.atlassian.net/wiki/spaces/PROJ/pages/789012/New+Page"
}
```

### Summarize Page

```bash
POST /confluence/summarize
Content-Type: application/json

{
  "page_id": "123456",
  "model": "mistral:latest"
}
```

**Response:**
```json
{
  "summary": "This page describes...",
  "page_title": "Architecture Design"
}
```

### Backup Space

```bash
POST /confluence/backup-space
Content-Type: application/json

{
  "space_key": "PROJ",
  "format": "html"
}
```

**Response:**
```json
{
  "bucket": "confluence-backups",
  "path": "PROJ/20250115_143000",
  "page_count": 42
}
```

### Get Space Statistics

```bash
POST /confluence/statistics
Content-Type: application/json

{
  "space_key": "PROJ"
}
```

**Response:**
```json
{
  "space_key": "PROJ",
  "space_name": "Project Documentation",
  "total_pages": 42,
  "total_size_bytes": 524288,
  "contributors": ["Alice", "Bob", "Charlie"],
  "last_updated": "2025-01-15T14:30:00.000Z"
}
```

### Get Available LLM Models

```bash
GET /confluence/models
```

**Response:**
```json
{
  "models": [
    {"name": "mistral:latest", "size": 4000000000},
    {"name": "llama3.2:latest", "size": 2000000000}
  ]
}
```

## Troubleshooting

### Credentials Not Found Error

**Symptom:** "Confluence credentials not found in Vault"

**Solution:**
1. Verify Vault is running: `docker-compose ps vault`
2. Set correct environment variables:
   ```bash
   export VAULT_ADDR=http://localhost:8200
   export VAULT_TOKEN=dev-only-token
   ```
3. Check credentials exist:
   ```bash
   vault kv get secret/confluence/credentials
   ```
4. If missing, add credentials (see Setup Step 1)

### Permission Denied / Invalid Token Error

**Symptom:** "Permission denied reading secret" or "invalid token"

**Possible Causes:**
1. Vault token not set correctly in environment
2. Token expired or invalid
3. KV secrets engine not enabled at 'secret/' path

**Solution:**
```bash
# For development, ensure you're using the dev token
export VAULT_TOKEN=dev-only-token

# Verify Vault connection
vault status

# Check if you can list secrets
vault kv list secret/

# Enable KV v2 if not already enabled (dev mode usually has this)
vault secrets enable -path=secret kv-v2

# Store credentials again
vault kv put secret/confluence/credentials \
  base_url="https://your-domain.atlassian.net/wiki" \
  email="your-email@example.com" \
  api_token="your-api-token-here"

# Verify it worked
vault kv get secret/confluence/credentials
```

**For Docker deployment:**
Ensure the web service has the correct `VAULT_TOKEN` environment variable set in `docker-compose.yml`:
```yaml
environment:
  VAULT_ADDR: http://vault:8200
  VAULT_TOKEN: dev-only-token
```

### Service Unavailable (503)

**Symptom:** "Confluence service unreachable"

**Possible Causes:**
1. **Network issue**: Check internet connectivity
2. **Invalid base URL**: Verify URL in Vault
3. **API token expired**: Generate new token
4. **Confluence Cloud down**: Check Atlassian status page

**Solution:**
```bash
# Test connectivity
curl -u "your-email@example.com:your-api-token" \
  https://your-domain.atlassian.net/wiki/rest/api/space
```

### Page Not Found (404)

**Symptom:** "Page not found: {page_id}"

**Causes:**
- Invalid page ID
- Page deleted
- No permission to access page

**Solution:**
- Verify page ID in Confluence URL
- Check page exists and you have access
- Ensure API token has correct permissions

### LLM Model Not Available

**Symptom:** "Model not found" or long delays

**Solution:**
```bash
# Pull the model manually
docker exec -it odin-ollama ollama pull mistral:latest

# Check available models
docker exec -it odin-ollama ollama list
```

### Slow Summarization

**Symptom:** Summarization takes > 60 seconds

**Causes:**
- First-time model download
- Large page content
- Resource constraints

**Solutions:**
- Use smaller model (llama3.2:latest or phi:latest)
- Increase Docker memory allocation
- Pre-pull models before use

### Storage Upload Failures

**Symptom:** "Failed to upload file" when saving

**Solution:**
```bash
# Check MinIO is running
docker-compose ps minio

# Verify MinIO health
curl http://localhost:9000/minio/health/live

# Check MinIO credentials in environment
echo $MINIO_ACCESS_KEY
echo $MINIO_SECRET_KEY
```

## Best Practices

### 1. Credential Management

- **Rotate API tokens regularly** (every 90 days)
- **Use dedicated service account** for API access
- **Never commit credentials** to version control
- **Document token purpose** in Atlassian settings

### 2. LLM Model Selection

| Model | Best For | Speed | Quality |
|-------|----------|-------|---------|
| mistral:latest | General use | Medium | High |
| llama3.2:latest | Fast summaries | Fast | Good |
| llama2:latest | Balanced | Medium | Good |
| phi:latest | Quick scans | Very Fast | Fair |

### 3. Backup Strategy

- **Schedule regular backups** (weekly recommended)
- **Test restore procedures** periodically
- **Monitor backup storage** usage
- **Document backup locations** for team

### 4. Performance Optimization

- **Pre-pull LLM models** during setup
- **Use save_to_storage=false** for quick conversions
- **Batch operations** during off-peak hours
- **Monitor Ollama resource** usage

### 5. Security Guidelines

- **Audit Vault access** logs regularly
- **Limit Confluence permissions** to required spaces
- **Review backup access** controls
- **Enable MFA** on Atlassian account

## Environment Variables

Configure these in `docker-compose.yml` or `.env`:

```bash
# Vault Configuration
VAULT_ADDR=http://vault:8200
VAULT_TOKEN=dev-only-token

# MinIO Configuration
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# Ollama Configuration
OLLAMA_BASE_URL=http://ollama:11434

# Confluence Configuration (stored in Vault, not env vars!)
# CONFLUENCE_BASE_URL - stored in Vault
# CONFLUENCE_EMAIL - stored in Vault
# CONFLUENCE_API_TOKEN - stored in Vault
```

## Architecture

```
┌─────────────────┐
│  Web Interface  │  (Port 80)
│  /confluence    │
└────────┬────────┘
         │
         ├──────────────────────────┐
         │                          │
    ┌────▼────┐              ┌──────▼───────┐
    │  Vault  │              │   MinIO      │
    │  :8200  │              │   :9000      │
    └────┬────┘              └──────────────┘
         │
    ┌────▼──────────────┐
    │  Confluence API   │
    │  (Cloud)          │
    └───────────────────┘
         │
    ┌────▼────┐
    │ Ollama  │
    │ :11434  │
    └─────────┘
```

## Support

For issues, feature requests, or questions:

1. Check this guide and troubleshooting section
2. Review logs: `docker-compose logs web`
3. Check service health: http://localhost/health
4. Verify credentials in Vault
5. Test Confluence API access manually

## Version History

### v1.6.0 (Current)
- ✨ Initial Confluence integration release
- 🔄 Bidirectional Markdown conversion
- 🤖 LLM-powered summarization
- 💾 Space backup functionality
- 📊 Space statistics and analytics
- 🔐 Vault-based credential management

## Roadmap

Future enhancements planned:

- [ ] Attachment handling (upload/download)
- [ ] Batch page operations
- [ ] Advanced search and filtering
- [ ] Scheduled backups
- [ ] Confluence Server support
- [ ] Page diff and versioning
- [ ] Multi-format exports (PDF, DOCX)
- [ ] Template management
- [ ] Webhook integration

---

**Last Updated:** January 2025  
**Version:** 1.6.0  
**Status:** Production Ready

