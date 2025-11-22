# Odin Worker Service Guide

## Overview

The Odin Worker Service provides a robust background task processing system built with Celery. It supports scheduled tasks, batch processing, and event-driven operations, all integrated with the existing infrastructure services.

## Architecture

### Components

- **Celery Worker**: Executes background tasks asynchronously
- **Celery Beat**: Scheduler for periodic tasks
- **Flower**: Real-time monitoring dashboard
- **RabbitMQ**: Message broker for task distribution
- **PostgreSQL**: Result backend for task state storage

### Task Types

1. **Scheduled Tasks** (`src/worker/tasks/scheduled.py`)
   - Health check services
   - Cleanup old task results
   - Generate daily reports

2. **Batch Processing Tasks** (`src/worker/tasks/batch.py`)
   - Process bulk data
   - Process file batches
   - Send bulk notifications

3. **Event-Driven Tasks** (`src/worker/tasks/events.py`)
   - Handle user registration
   - Process webhooks
   - Send notifications

## Getting Started

### Prerequisites

- Docker and Docker Compose
- All services running (PostgreSQL, RabbitMQ)
- Python 3.12+ (for local development)

### Starting the Worker Services

Start all worker services (worker, beat, and flower):

```bash
make services-up
```

Or start individual services:

```bash
# Start only the worker
make worker-dev

# Start only the beat scheduler
make beat-start

# Start only the flower dashboard
make flower-start
```

### Accessing Services

- **Flower Dashboard**: http://localhost/flower/ (admin/admin)
- **Worker Logs**: `make worker-logs`
- **Beat Logs**: `make beat-logs`
- **Flower Logs**: `make flower-logs`

## Configuration

### Environment Variables

Configure the worker in your `.env` file:

```bash
# Celery Broker (RabbitMQ)
CELERY_BROKER_URL=amqp://odin:odin_dev_password@rabbitmq:5672//

# Result Backend (PostgreSQL)
CELERY_RESULT_BACKEND=db+postgresql://odin:odin_dev_password@postgresql:5432/odin_db

# Task Settings
CELERY_TASK_TRACK_STARTED=true
CELERY_TASK_TIME_LIMIT=3600

# Worker Settings
CELERY_WORKER_CONCURRENCY=4
CELERY_WORKER_MAX_TASKS_PER_CHILD=1000

# Flower Settings
FLOWER_PORT=5555
FLOWER_BASIC_AUTH=admin:admin
```

### Beat Schedule

The Beat schedule is configured in `src/worker/beat_schedule.py`:

- **Health Check**: Every 5 minutes
- **Cleanup**: Daily at 2:00 AM
- **Daily Report**: Daily at midnight

## Creating New Tasks

### 1. Define the Task

Create a new task function in the appropriate module:

```python
# src/worker/tasks/events.py
from src.worker.celery_app import celery_app

@celery_app.task(name="src.worker.tasks.events.my_custom_task")
def my_custom_task(param1: str, param2: int) -> dict[str, Any]:
    """Custom task that does something useful.
    
    Args:
        param1: First parameter
        param2: Second parameter
        
    Returns:
        Dictionary with task results
    """
    # Task logic here
    return {"status": "success", "result": "data"}
```

### 2. Write Tests First (TDD)

Create unit tests before implementing:

```python
# tests/unit/worker/tasks/test_events.py
def test_my_custom_task_success():
    """Test successful task execution."""
    result = my_custom_task("test", 123)
    assert result["status"] == "success"
```

### 3. Add to Beat Schedule (Optional)

For periodic tasks, add to `src/worker/beat_schedule.py`:

```python
"my-custom-task": {
    "task": "src.worker.tasks.events.my_custom_task",
    "schedule": timedelta(hours=1),
    "args": ("param_value", 42),
},
```

### 4. Expose via API/Web (Optional)

Add dispatch method in `src/api/services/task_service.py`:

```python
def dispatch_my_custom_task(self, param1: str, param2: int) -> dict[str, str]:
    """Dispatch my custom task."""
    from src.worker.tasks.events import my_custom_task
    
    task = my_custom_task.delay(param1, param2)
    return {"task_id": task.id, "status": "dispatched"}
```

## Task Best Practices

### 1. Idempotency

Tasks should be idempotent - running the same task multiple times with the same input should produce the same result:

```python
@celery_app.task
def update_user_status(user_id: int, status: str) -> dict:
    """Update user status (idempotent)."""
    # Check current status before updating
    user = get_user(user_id)
    if user.status == status:
        return {"status": "unchanged"}
    
    user.status = status
    user.save()
    return {"status": "updated"}
```

### 2. Error Handling

Always handle errors gracefully and provide meaningful error messages:

```python
@celery_app.task(bind=True, max_retries=3)
def risky_task(self, data: dict) -> dict:
    """Task that might fail."""
    try:
        # Task logic
        result = process_data(data)
        return {"status": "success", "result": result}
    except TemporaryError as exc:
        # Retry on temporary errors
        raise self.retry(exc=exc, countdown=60)
    except Exception as exc:
        # Log permanent errors and fail
        logger.error(f"Task failed: {exc}")
        return {"status": "error", "error": str(exc)}
```

### 3. Progress Tracking

For long-running tasks, update task state to track progress:

```python
@celery_app.task(bind=True)
def long_running_task(self, items: list) -> dict:
    """Task with progress tracking."""
    total = len(items)
    for i, item in enumerate(items):
        # Update task progress
        self.update_state(
            state='PROGRESS',
            meta={'current': i, 'total': total, 'percent': (i / total) * 100}
        )
        process_item(item)
    
    return {"status": "complete", "processed": total}
```

### 4. Resource Management

Use context managers for database connections and external resources:

```python
@celery_app.task
def database_task() -> dict:
    """Task that uses database."""
    with session_scope() as session:
        # Database operations here
        results = session.query(Model).all()
        return {"count": len(results)}
```

## Monitoring and Debugging

### Flower Dashboard

Access the Flower dashboard at http://localhost/flower/:

- **Tasks**: View all tasks, their status, and results
- **Workers**: Monitor worker status and configuration
- **Broker**: View message queue status
- **Monitor**: Real-time task execution monitoring

### Viewing Logs

```bash
# Worker logs
make worker-logs

# Beat scheduler logs
make beat-logs

# Flower dashboard logs
make flower-logs

# All services
make services-logs
```

### Checking Worker Status

```bash
# Check worker, beat, and flower status
make worker-status

# View all service status
make services-status
```

### Task Inspection

Check task status via the API:

```python
from src.api.services.task_service import get_task_service

service = get_task_service()
status = service.get_task_status("task-id-here")
print(status)
```

## Testing

### Running Worker Tests

```bash
# All worker tests
make test-worker

# Unit tests only
make test-worker-unit

# Integration tests only
make test-worker-integration

# Coverage report
make coverage-worker
```

### Testing Tasks Locally

Use eager mode for synchronous testing:

```python
from src.worker.celery_app import get_celery_app

app = get_celery_app()
app.conf.task_always_eager = True
app.conf.task_eager_propagates = True

# Tasks now run synchronously
result = my_task.delay(param)
print(result.get())
```

## Common Issues

### Task Not Executing

1. Check if worker is running: `make worker-status`
2. Check RabbitMQ connection: `make services-health`
3. View worker logs: `make worker-logs`
4. Verify task is registered: Check Flower dashboard

### Task Taking Too Long

1. Check `CELERY_TASK_TIME_LIMIT` setting
2. Review task logic for performance issues
3. Consider breaking into smaller sub-tasks
4. Check database connection pool

### Memory Issues

1. Adjust `CELERY_WORKER_MAX_TASKS_PER_CHILD`
2. Reduce `CELERY_WORKER_CONCURRENCY`
3. Review task for memory leaks
4. Use batch processing for large datasets

### Beat Not Scheduling

1. Verify beat container is running: `docker ps`
2. Check beat logs: `make beat-logs`
3. Verify schedule configuration in `beat_schedule.py`
4. Ensure worker is running to execute scheduled tasks

## Performance Tuning

### Worker Concurrency

Adjust based on CPU cores and task type:

```bash
# CPU-bound tasks: concurrency = CPU cores
CELERY_WORKER_CONCURRENCY=4

# I/O-bound tasks: concurrency = 2x CPU cores
CELERY_WORKER_CONCURRENCY=8
```

### Task Time Limits

Set appropriate time limits to prevent hanging tasks:

```python
@celery_app.task(time_limit=300, soft_time_limit=280)
def time_limited_task():
    """Task with 5-minute hard limit."""
    # Task logic
    pass
```

### Rate Limiting

Limit task execution rate:

```python
@celery_app.task(rate_limit='10/m')  # 10 tasks per minute
def rate_limited_task():
    """Task with rate limit."""
    pass
```

## Security

### Authentication

- Flower is protected with basic auth (configured via `FLOWER_BASIC_AUTH`)
- RabbitMQ uses username/password authentication
- PostgreSQL requires credentials for result backend

### Task Validation

Always validate task inputs:

```python
@celery_app.task
def secure_task(data: dict) -> dict:
    """Secure task with input validation."""
    # Validate required fields
    if "user_id" not in data:
        raise ValueError("user_id is required")
    
    # Sanitize inputs
    user_id = int(data["user_id"])
    
    # Process safely
    return process_user(user_id)
```

## Production Deployment

### Docker Compose

For production, use the production Dockerfile target:

```yaml
worker:
  build:
    target: production
  environment:
    - CELERY_WORKER_CONCURRENCY=8
```

### Scaling Workers

Scale workers horizontally:

```bash
docker-compose up --scale worker=4
```

### Monitoring

- Set up log aggregation (ELK, Splunk)
- Configure alerting for task failures
- Monitor Flower dashboard metrics
- Track RabbitMQ queue depth

## Additional Resources

- [Celery Documentation](https://docs.celeryproject.org/)
- [Flower Documentation](https://flower.readthedocs.io/)
- [RabbitMQ Documentation](https://www.rabbitmq.com/documentation.html)
- [Project README](README.md)
- [Release Notes](RELEASES.md)

