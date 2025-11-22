# Image Analysis Guide - Version 1.3.0

## Overview

The Image Analysis feature allows you to upload images and have them analyzed by vision-capable LLM models (like LLaVA). Images are stored in MinIO, metadata persists in PostgreSQL, and the LLM generates descriptive text about the image content.

## Features

- **Image Upload**: Support for JPEG, PNG, WebP, and GIF formats
- **LLM Analysis**: Vision-capable models analyze and describe image content
- **Persistent Storage**: Images stored in MinIO, metadata in PostgreSQL
- **Configurable Models**: Use different vision models (LLaVA, BakLLaVA, etc.)
- **Custom Prompts**: Provide specific prompts for targeted analysis
- **Size Validation**: Configurable maximum file size (default: 10MB)
- **Error Handling**: Automatic cleanup on failures to prevent orphaned data

## Architecture

### Storage Strategy

1. **MinIO**: Stores actual image files in the `images` bucket
2. **PostgreSQL**: Stores metadata (filename, description, model used, timestamps)
3. **Ollama**: Provides vision-capable LLM models for image analysis

### Workflow

```
1. User uploads image via API
   ↓
2. Validate image (size, content type)
   ↓
3. Upload to MinIO with unique key
   ↓
4. Send to Ollama for LLM analysis
   ↓
5. Store metadata + description in PostgreSQL
   ↓
6. Return analysis result to user
```

If any step fails after MinIO upload, the uploaded image is automatically cleaned up.

## API Endpoints

### POST /llm/analyze-image

Upload and analyze an image.

**Request** (multipart/form-data):
```bash
curl -X POST http://localhost/logs/proxy/api/v1/llm/analyze-image \
  -F "file=@sunset.jpg" \
  -F "prompt=Describe this image in detail" \
  -F "model=llava:latest"
```

**Parameters**:
- `file` (required): Image file (JPEG, PNG, WebP, GIF)
- `prompt` (optional): Custom prompt (default: "Describe this image")
- `model` (optional): Model name (default: configured `VISION_MODEL_DEFAULT`)

**Response** (200 OK):
```json
{
  "id": 1,
  "filename": "sunset.jpg",
  "llm_description": "The image shows a beautiful sunset over mountains with vibrant orange and pink colors in the sky...",
  "model_used": "llava:latest",
  "metadata": {
    "bucket": "images",
    "object_key": "sunset_1700000000123456.jpg",
    "content_type": "image/jpeg",
    "size_bytes": 245678
  },
  "created_at": "2025-11-22T10:30:00.000000",
  "updated_at": "2025-11-22T10:30:00.000000"
}
```

**Error Responses**:
- `400 Bad Request`: Invalid image or validation error
- `500 Internal Server Error`: Storage, LLM, or database error

### GET /llm/analyze-image/{image_id}

Retrieve a specific image analysis by ID.

**Request**:
```bash
curl http://localhost/logs/proxy/api/v1/llm/analyze-image/1
```

**Response** (200 OK):
```json
{
  "id": 1,
  "filename": "sunset.jpg",
  "llm_description": "The image shows a beautiful sunset...",
  "model_used": "llava:latest",
  "metadata": {
    "bucket": "images",
    "object_key": "sunset_1700000000123456.jpg",
    "content_type": "image/jpeg",
    "size_bytes": 245678
  },
  "created_at": "2025-11-22T10:30:00.000000",
  "updated_at": "2025-11-22T10:30:00.000000"
}
```

**Error Responses**:
- `404 Not Found`: Image analysis not found

### GET /llm/analyze-image

List all image analyses.

**Request**:
```bash
curl http://localhost/logs/proxy/api/v1/llm/analyze-image
```

**Response** (200 OK):
```json
{
  "analyses": [
    {
      "id": 1,
      "filename": "sunset.jpg",
      "llm_description": "The image shows a beautiful sunset...",
      "model_used": "llava:latest",
      "metadata": {
        "bucket": "images",
        "object_key": "sunset_1700000000123456.jpg",
        "content_type": "image/jpeg",
        "size_bytes": 245678
      },
      "created_at": "2025-11-22T10:30:00.000000",
      "updated_at": "2025-11-22T10:30:00.000000"
    }
  ],
  "total": 1
}
```

### DELETE /llm/analyze-image/{image_id}

Delete an image analysis and its associated image file.

**Request**:
```bash
curl -X DELETE http://localhost/logs/proxy/api/v1/llm/analyze-image/1
```

**Response** (200 OK):
```json
{
  "message": "Image analysis 1 deleted successfully"
}
```

**Error Responses**:
- `404 Not Found`: Image analysis not found

## Configuration

Add these environment variables to your `.env` file:

```bash
# Image Analysis Configuration (v1.3.0)
VISION_MODEL_DEFAULT=llava:latest    # Default vision model
IMAGE_BUCKET=images                  # MinIO bucket for images
MAX_IMAGE_SIZE_MB=10                 # Maximum image size in MB
```

### Supported Models

Vision-capable models that work with Ollama:

- **llava:latest** (default) - General-purpose vision model
- **bakllava:latest** - Alternative vision model
- **llava:13b** - Larger, more capable model
- **llava:7b** - Smaller, faster model

### Image Requirements

- **Formats**: JPEG, PNG, WebP, GIF
- **Max Size**: Configurable (default: 10MB)
- **Content Type**: Must be `image/jpeg`, `image/png`, `image/webp`, or `image/gif`

## Usage Examples

### Basic Image Analysis

```python
import requests

# Upload and analyze an image
with open('photo.jpg', 'rb') as f:
    response = requests.post(
        'http://localhost/logs/proxy/api/v1/llm/analyze-image',
        files={'file': ('photo.jpg', f, 'image/jpeg')}
    )

result = response.json()
print(f"Analysis: {result['llm_description']}")
print(f"Image ID: {result['id']}")
```

### Custom Prompt Analysis

```python
import requests

# Ask specific questions about the image
with open('diagram.png', 'rb') as f:
    response = requests.post(
        'http://localhost/logs/proxy/api/v1/llm/analyze-image',
        files={'file': ('diagram.png', f, 'image/png')},
        data={
            'prompt': 'Identify all text and labels in this diagram',
            'model': 'llava:13b'
        }
    )

result = response.json()
print(result['llm_description'])
```

### List All Analyses

```python
import requests

response = requests.get('http://localhost/logs/proxy/api/v1/llm/analyze-image')
analyses = response.json()

for analysis in analyses['analyses']:
    print(f"{analysis['id']}: {analysis['filename']}")
    print(f"  {analysis['llm_description'][:100]}...")
```

### Delete Analysis

```python
import requests

image_id = 1
response = requests.delete(
    f'http://localhost/logs/proxy/api/v1/llm/analyze-image/{image_id}'
)
print(response.json()['message'])
```

## Setting Up Vision Models

### Pull LLaVA Model

Before using image analysis, pull a vision-capable model:

```bash
# Access Ollama container
docker exec -it ollama ollama pull llava:latest

# Or pull a specific version
docker exec -it ollama ollama pull llava:13b
```

### Verify Model Availability

Check that the model is available:

```bash
curl http://localhost/logs/proxy/api/v1/llm/models
```

Look for models with vision capabilities (like "llava").

## Database Schema

The `image_analysis` table stores metadata:

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

## Troubleshooting

### Error: "Invalid image content type"

**Cause**: Uploaded file is not a supported image format.

**Solution**: Ensure file is JPEG, PNG, WebP, or GIF. Check the `Content-Type` header.

### Error: "Image size exceeds maximum size"

**Cause**: Image file is larger than the configured limit.

**Solution**: 
- Compress the image before uploading
- Increase `MAX_IMAGE_SIZE_MB` in configuration

### Error: "Model not found"

**Cause**: Specified vision model is not available in Ollama.

**Solution**: Pull the model first:
```bash
docker exec -it ollama ollama pull llava:latest
```

### Error: "Ollama service unreachable"

**Cause**: Cannot connect to Ollama service.

**Solution**: 
- Verify Ollama is running: `docker ps | grep ollama`
- Check `OLLAMA_BASE_URL` configuration
- Test Ollama directly: `curl http://ollama:11434/api/tags`

### Error: "Upload failed" (Storage Error)

**Cause**: Cannot connect to MinIO or write to bucket.

**Solution**:
- Verify MinIO is running: `docker ps | grep minio`
- Check `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`
- Ensure `images` bucket exists (auto-created on first upload)

## Performance Considerations

### Image Size vs. Processing Time

- **Small images (< 1MB)**: ~2-5 seconds
- **Medium images (1-5MB)**: ~5-10 seconds
- **Large images (5-10MB)**: ~10-20 seconds

Processing time depends on:
- Image resolution
- Model size (7b vs 13b)
- Ollama hardware resources

### Concurrent Requests

The service handles multiple concurrent uploads:
- Each request is processed independently
- Unique object keys prevent conflicts
- Database transactions ensure consistency

### Storage Cleanup

Failed uploads are automatically cleaned up:
- If LLM analysis fails → Image deleted from MinIO
- If DB save fails → Image deleted from MinIO
- No orphaned images in storage

## Security Considerations

### File Validation

- Content type validation prevents non-image uploads
- Size limits prevent DoS attacks via large files
- Unique object keys prevent file overwrites

### Access Control

- API endpoints should be protected by authentication (implement as needed)
- MinIO buckets use configured access credentials
- Database access requires valid connection credentials

## Best Practices

### 1. Use Appropriate Prompts

Generic prompt:
```
"Describe this image"
```

Specific prompt (better results):
```
"Identify the main objects in this image and their spatial relationships"
```

### 2. Choose the Right Model

- **llava:7b**: Fast, good for simple descriptions
- **llava:13b**: Slower, better for detailed analysis
- **bakllava:latest**: Alternative, may excel at specific tasks

### 3. Handle Errors Gracefully

```python
try:
    response = requests.post(url, files=files)
    response.raise_for_status()
    result = response.json()
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 400:
        print("Invalid image or parameters")
    elif e.response.status_code == 500:
        print("Service error, try again later")
```

### 4. Monitor Storage Usage

Regularly check MinIO storage:
```bash
# List images in bucket
mc ls minio/images/

# Get bucket size
mc du minio/images/
```

## Integration with Other Features

### Combine with Logging

All image analysis operations are logged:
```bash
curl 'http://localhost/logs/proxy/api/v1/logs?service=api&search=image_analysis'
```

### Use with Worker Tasks

Schedule periodic image analysis:
```python
from celery import shared_task

@shared_task
def analyze_images_batch():
    # Process multiple images
    pass
```

## Changelog

### Version 1.3.0 (Current)
- Initial image analysis feature
- Support for JPEG, PNG, WebP, GIF
- LLaVA integration via Ollama
- MinIO storage + PostgreSQL metadata
- Configurable models and size limits
- Automatic cleanup on failures

## Future Enhancements

Potential improvements for future versions:

- **Batch Upload**: Analyze multiple images in one request
- **Image Search**: Search by description content
- **Thumbnail Generation**: Store small previews
- **Direct Image Access**: Download analyzed images via API
- **Analysis History**: Track changes to analysis over time
- **Tagging System**: Auto-generate tags from descriptions
- **Webhook Notifications**: Alert when analysis completes

## Support

For issues or questions:
1. Check this guide
2. Review logs: `docker logs odin-api`
3. Check service health: `http://localhost/health`
4. Verify model availability: `http://localhost/logs/proxy/api/v1/llm/models`

