# RenderService
Service for rendering blender scenes. You need to set up it in the GPU server.

## Setup
1. Copy .env.example to .env and set the variables.
```bash
cp .env.example .env
```
2. Create virtual environment and install dependencies.
```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
3. Run the service.
```bash
make run
```
4. Open the [UI](http://localhost:8000/docs) in your browser.

## TODO
- [ ] Add support to render specific camera in the scene.
- [ ] Write tests.

## Requirements
- Python <= 3.11

## Technologies
- [FastAPI](https://fastapi.tiangolo.com/)
- [Redis](https://redis.io/)
- [Blender](https://www.blender.org/)
