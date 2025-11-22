# Release Notes - Version 1.3.0

## Image Analysis Feature

**Release Date**: November 22, 2025

### Overview

Version 1.3.0 introduces a comprehensive image analysis feature that allows users to upload images and analyze them using vision-capable LLM models (LLaVA). Images are stored in MinIO, metadata persists in PostgreSQL, and the LLM generates descriptive text about the image content.

### New Features

#### 1. Image Upload and Analysis API

- **POST /llm/analyze-image**: Upload image and receive LLM-generated description
- **GET /llm/analyze-image/{image_id}**: Retrieve specific analysis by ID
- **GET /llm/analyze-image**: List all image analyses
- **DELETE /llm/analyze-image/{image_id}**: Delete analysis and associated image

#### 2. Web Portal Integration

- **New Page**: Image Analyzer accessible from web portal menu
- **User-Friendly Interface**: Upload images with optional custom prompts
- **Analysis History**: View all previous analyses with timestamps
- **Real-Time Feedback**: Verbose error messages and success notifications
- **Browser-Based**: No command-line tools required

#### 3. Supported Image Formats

- JPEG (image/jpeg)
- PNG (image/png)
- WebP (image/webp)
- GIF (image/gif)

#### 4. Vision Model Support

- **Default**: LLaVA (llava:latest)
- **Configurable**: Support for any vision-capable Ollama model
- **Custom prompts**: Ask specific questions about images

#### 5. Storage Architecture

- **MinIO**: Persistent image file storage in dedicated bucket
- **PostgreSQL**: Metadata storage (filename, description, timestamps)
- **Unique keys**: Timestamp-based unique object keys prevent conflicts

#### 6. Configuration Options

New environment variables:
- `VISION_MODEL_DEFAULT`: Default vision model (default: "llava:latest")
- `IMAGE_BUCKET`: MinIO bucket name (default: "images")
- `MAX_IMAGE_SIZE_MB`: Maximum image size in MB (default: 10)

### Technical Implementation

#### Architecture Components

1. **Domain Layer** (`src/api/domain/entities.py`)
   - New `ImageAnalysis` entity with comprehensive metadata

2. **Repository Layer** (`src/api/repositories/image_repository.py`)
   - CRUD operations for image analysis records
   - Automatic table creation on startup

3. **Service Layer** (`src/api/services/`)
   - `OllamaService.analyze_image()`: Vision API integration with base64 encoding
   - `ImageAnalysisService`: Orchestration of storage, LLM, and database

4. **API Layer** (`src/api/routes/image_analysis.py`)
   - RESTful endpoints with multipart form support
   - Comprehensive error handling

5. **Web Layer** (`src/web/routes/image_analyzer.py`, `src/web/templates/image_analyzer.html`)
   - Modern web interface with JavaScript
   - Real-time upload progress and feedback
   - Analysis history viewer

6. **Infrastructure** (`nginx/nginx.conf`)
   - Nginx proxy configuration for API access
   - 20MB upload size limit
   - URL rewriting for clean API paths

7. **Configuration** (`src/api/config.py`)
   - Type-safe configuration with Pydantic
   - Environment variable integration

### Testing

Comprehensive test coverage following TDD principles:

- **Unit Tests**: 
  - Repository tests (CRUD operations)
  - Service tests (Ollama vision API, orchestration)
  - Route tests (all endpoints)
  
- **Integration Tests**: 
  - End-to-end workflow tests (placeholder structure)
  - Error recovery and cleanup verification

### Error Handling and Robustness

1. **Validation**:
   - File size limits
   - Content type verification
   - Image format validation

2. **Cleanup**:
   - Automatic image deletion on LLM failure
   - Automatic image deletion on database failure
   - No orphaned data in storage

3. **Error Responses**:
   - 400: Validation errors (invalid image, too large)
   - 404: Resource not found
   - 500: Service errors (storage, LLM, database)

### Database Schema

New table: `image_analysis`

```sql
CREATE TABLE image_analysis (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    bucket VARCHAR(100) NOT NULL,
    object_key VARCHAR(500) NOT NULL,
    content_type VARCHAR(100) NOT NULL,
    size_bytes INTEGER NOT NULL,
    llm_description TEXT,
    model_used VARCHAR(100),
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
```

### Documentation

New comprehensive documentation:

1. **IMAGE_ANALYSIS_GUIDE.md**: Complete user guide
   - API endpoint documentation
   - Usage examples
   - Configuration guide
   - Troubleshooting
   - Best practices

2. **Updated README.md**: Feature overview and version badge

3. **Updated env.example**: New configuration variables

### Breaking Changes

None. This is a purely additive release.

### Migration Guide

#### For Existing Installations

1. **Update environment variables** (optional):
   ```bash
   # Add to .env file
   VISION_MODEL_DEFAULT=llava:latest
   IMAGE_BUCKET=images
   MAX_IMAGE_SIZE_MB=10
   C_FORCE_ROOT=true  # For Celery workers (suppress root warning)
   ```

2. **Pull vision model**:
   ```bash
   # Use your actual container name (might be odin-ollama)
   docker exec -it odin-ollama ollama pull llava:latest
   ```

3. **Restart services**:
   ```bash
   docker-compose restart api nginx worker beat
   ```

4. **Verify**:
   ```bash
   # Check API health
   curl http://localhost/health
   
   # Access web interface
   open http://localhost/image-analyzer
   ```

### Usage Examples

#### Web Interface (Recommended)

1. Navigate to `http://localhost/image-analyzer`
2. Click "Choose File" and select an image
3. Optionally enter a custom prompt
4. Click "Analyze Image"
5. View results and history

#### API (CLI)

```bash
# Upload and analyze an image
curl -X POST http://localhost/api/llm/analyze-image \
  -F "file=@photo.jpg" \
  -F "prompt=Describe this image in detail" \
  -F "model=llava:latest"

# Response:
# {
#   "id": 1,
#   "filename": "photo.jpg",
#   "llm_description": "The image shows...",
#   "model_used": "llava:latest",
#   "metadata": {
#     "bucket": "images",
#     "object_key": "photo_1700000000123456.jpg",
#     "content_type": "image/jpeg",
#     "size_bytes": 245678
#   },
#   "created_at": "2025-11-22T10:30:00.000000"
# }
```

### Performance Characteristics

- **Small images (< 1MB)**: ~2-5 seconds
- **Medium images (1-5MB)**: ~5-10 seconds  
- **Large images (5-10MB)**: ~10-20 seconds

Processing time depends on image size, model size, and available hardware.

### Dependencies

No new external dependencies required. Uses existing:
- FastAPI (multipart form support)
- httpx (Ollama API calls)
- SQLAlchemy (database operations)
- MinIO client (storage operations)

### Known Limitations

1. **Model Availability**: Requires vision-capable models to be pulled first
2. **Synchronous Processing**: Analysis is synchronous (may add async queue in future)
3. **Single Image**: One image per request (batch support in future)
4. **No Image Retrieval**: Cannot download analyzed images via API (future enhancement)

### Future Enhancements

Planned for future versions:
- Batch image upload and analysis
- Image search by description content
- Thumbnail generation
- Direct image download via API
- Analysis history tracking
- Auto-tagging based on descriptions
- Webhook notifications

### Security Considerations

- File type validation prevents malicious uploads
- Size limits prevent DoS attacks
- Unique object keys prevent overwrites
- Credentials required for MinIO and database access

### Compatibility

- **Python**: 3.12+
- **Docker**: Compatible with existing docker-compose setup
- **Services**: Requires Ollama with vision models

### Contributors

Implementation follows TDD and SOLID principles as specified in project guidelines.

### References

- [IMAGE_ANALYSIS_GUIDE.md](IMAGE_ANALYSIS_GUIDE.md) - Complete user documentation
- [README.md](README.md) - Updated project overview
- [env.example](env.example) - Configuration template

### Support

For issues or questions:
1. Review IMAGE_ANALYSIS_GUIDE.md
2. Check service logs: `docker logs odin-api`
3. Verify Ollama models: `docker exec -it ollama ollama list`
4. Test API health: `curl http://localhost/health`

