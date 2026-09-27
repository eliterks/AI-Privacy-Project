from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from tests.test_gateway import FakeGemini, gateway
from app.services.gemini import GeminiError


ROOT = Path(__file__).resolve().parents[1]


def test_health_ready_version_and_analyze():
    service = gateway(FakeGemini())
    app = create_app(service.settings, gateway_factory=lambda _: service)
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}
        assert client.get("/ready").status_code == 200
        assert client.get("/version").json()["gateway"] == "0.2.0"
        response = client.post("/api/v1/analyze", json={"text": "Explain hashing"})
        assert response.status_code == 200
        assert response.json()["decision"] == "ALLOW"


def test_missing_model_fails_closed():
    settings = Settings(
        model_path=str(ROOT / "artifacts" / "missing.skops"),
        policy_path=ROOT / "config" / "policy.yaml",
        pii_rules_path=ROOT / "config" / "pii_rules.yaml",
    )
    app = create_app(settings)
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/ready").status_code == 503
        assert client.post("/api/v1/analyze", json={"text": "hello"}).status_code == 503


def test_input_limit_is_enforced():
    service = gateway(FakeGemini())
    app = create_app(service.settings, gateway_factory=lambda _: service)
    with TestClient(app) as client:
        assert client.post("/api/v1/analyze", json={"text": "x" * 5001}).status_code == 422


def test_gemini_failure_returns_controlled_error():
    class FailingGemini:
        async def generate(self, text: str) -> str:
            raise GeminiError("Gemini request timed out")

    service = gateway(FailingGemini())
    app = create_app(service.settings, gateway_factory=lambda _: service)
    with TestClient(app) as client:
        response = client.post("/api/v1/generate", json={"text": "Explain hashing"})
        assert response.status_code == 502
        assert response.json() == {"detail": "Gemini request timed out"}
