from openenv.core.client import EnvClient
from models import APIAction, APIObservation, APIState


class APIDebugEnv(EnvClient[APIAction, APIObservation, APIState]):

    def __init__(self, base_url: str = "http://localhost:8000"):
        super().__init__(
            base_url=base_url,
            action_type=APIAction,
            observation_type=APIObservation,
        )
