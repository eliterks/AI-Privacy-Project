from __future__ import annotations

from app.config import Settings
from app.schemas import AnalysisResponse, ComponentVersions, Decision, GenerateResponse
from app.services.gemini import GeminiClient
from app.services.injection import InjectionDetector
from app.services.pii import PIIEngine
from app.services.policy import PolicyEngine


class GatewayService:
    def __init__(
        self,
        settings: Settings,
        injection: InjectionDetector,
        pii: PIIEngine,
        policy: PolicyEngine,
        gemini: GeminiClient,
    ):
        self.settings = settings
        self.injection = injection
        self.pii = pii
        self.policy = policy
        self.gemini = gemini

    @classmethod
    def build(cls, settings: Settings) -> "GatewayService":
        pii = PIIEngine(settings.pii_rules_path)
        policy = PolicyEngine(settings.policy_path)
        injection = InjectionDetector.from_settings(settings)
        gemini = GeminiClient(settings.gemini_api_key, settings.gemini_model, settings.gemini_timeout_seconds)
        return cls(settings, injection, pii, policy, gemini)

    def versions(self) -> ComponentVersions:
        return ComponentVersions(
            gateway=self.settings.gateway_version,
            injection_model=self.injection.version,
            pii_engine=self.pii.version,
            policy=self.policy.version,
            evaluation_set=self.settings.evaluation_version,
            model_revision=self.injection.revision,
        )

    def analyze(self, text: str) -> AnalysisResponse:
        active_threshold = (
            self.policy.injection_threshold
            if self.policy.injection_threshold is not None
            else self.injection.threshold
        )
        injection = self.injection.predict(text, threshold=active_threshold)
        findings = self.pii.detect(text)
        decision, reasons = self.policy.evaluate(injection.score, findings, active_threshold)
        sanitized = self.pii.redact(text, findings) if decision == Decision.REDACT else text
        return AnalysisResponse(
            decision=decision,
            injection=injection,
            pii=findings,
            sanitized_text=sanitized,
            reasons=reasons,
            versions=self.versions(),
        )

    async def generate(self, text: str) -> GenerateResponse:
        analysis = self.analyze(text)
        if analysis.decision == Decision.BLOCK:
            return GenerateResponse(**analysis.model_dump(), response=None)

        response = await self.gemini.generate(analysis.sanitized_text)
        output_findings = self.pii.detect(response)
        active_threshold = (
            self.policy.injection_threshold
            if self.policy.injection_threshold is not None
            else self.injection.threshold
        )
        output_decision, _ = self.policy.evaluate(0.0, output_findings, active_threshold)
        if output_decision == Decision.BLOCK:
            safe_response = "The generated response was blocked by the output privacy policy."
            sanitized = True
        elif output_decision == Decision.REDACT:
            safe_response = self.pii.redact(response, output_findings)
            sanitized = True
        else:
            safe_response = response
            sanitized = False

        return GenerateResponse(
            **analysis.model_dump(),
            response=safe_response,
            response_pii=output_findings,
            response_sanitized=sanitized,
        )
