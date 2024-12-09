# RenderService

## TODO
- [ ] Add support to render specific camera in the scene.

## Requirements
- Python 3.11

## Run celry worker
```
celery --app src.core.celery worker -P prefork --concurrency=1 --loglevel=info
```
