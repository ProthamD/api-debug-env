from fastapi import FastAPI
from openenv.core.env_server import create_app

from models import APIAction, APIObservation
from server.api_debug_environment import APIDebugEnvironment
from server.mock_api import router as mock_router

# Pass the CLASS not an instance
app = create_app(APIDebugEnvironment, APIAction, APIObservation, env_name="api_debug_env")

app.include_router(mock_router)


@app.get("/health")
async def health():
    return {"status": "ok", "environment": "api-debug-env"}