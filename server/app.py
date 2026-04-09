try:
    from openenv.core.env_server.http_server import create_app
except Exception as exc:
    raise ImportError(
        "openenv dependencies are required. Install with: pip install -e ."
    ) from exc

try:
    from ..models import ReliabilityTriageAction, ReliabilityTriageObservation
    from .reliability_triage_environment import ReliabilityTriageEnvironment
except ImportError:
    from models import ReliabilityTriageAction, ReliabilityTriageObservation
    from server.reliability_triage_environment import ReliabilityTriageEnvironment


app = create_app(
    ReliabilityTriageEnvironment,
    ReliabilityTriageAction,
    ReliabilityTriageObservation,
    env_name="reliability_triage_env",
    max_concurrent_envs=4,
)


def main(host: str = "0.0.0.0", port: int = 8000) -> None:
    import uvicorn

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
