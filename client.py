try:
    from openenv.core.client import EnvClient
except ImportError:
    try:
        from openenv.core.env_client import EnvClient
    except ImportError:
        from openenv.core import EnvClient
from models import APIAction, APIObservation, APIState


class APIDebugEnv(EnvClient[APIAction, APIObservation, APIState]):

    def __init__(self, base_url: str = "http://localhost:7860"):
        super().__init__(
            base_url=base_url,
            action_type=APIAction,
            observation_type=APIObservation,
        )
