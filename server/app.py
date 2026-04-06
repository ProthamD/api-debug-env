from fastapi import FastAPI
from openenv.core.env_server import create_app

from models import APIAction, APIObservation
from server.api_debug_environment import APIDebugEnvironment
from server.mock_api import router as mock_router

app = create_app(APIDebugEnvironment, APIAction, APIObservation, env_name="api_debug_env")

app.include_router(mock_router)


@app.get("/health")
async def health():
    return {"status": "ok", "environment": "api-debug-env"}


def main():
    import uvicorn
    uvicorn.run("server.app:app", host="0.0.0.0", port=7860)


if __name__ == "__main__":
    main()
