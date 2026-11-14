"""Calls Claude through the provider an organization chose, using the
official Anthropic SDK: Anthropic's API directly, or the organization's own
Amazon Bedrock, Google Vertex AI or Microsoft Foundry account.

Every call asks for structured JSON (output_config.format) at high effort
with adaptive thinking (the model's default). If the model declines a
request, it's retried on a fallback model: server-side on Anthropic's API,
with the SDK's client-side middleware on Bedrock and Vertex. Foundry
fallback would need a second deployment, so a refusal there is reported as
such. The model that actually answered is always returned, for the log.
"""

import time
from dataclasses import dataclass

import anthropic
from anthropic import BetaFallbackState, BetaRefusalFallbackMiddleware

from app.core.ai.crypto import decrypt_secret
from app.models.ai import OrgAiSettings

PROVIDERS = {
    "anthropic": "Claude on Anthropic's API",
    "bedrock": "Claude on Amazon Bedrock",
    "vertex": "Claude on Google Vertex AI",
    "foundry": "Claude on Microsoft Foundry",
}
DEFAULT_MODEL = "claude-opus-5-5"
FALLBACK_MODEL = "claude-opus-4-8"
MAX_TOKENS = 16000


class AiProviderError(Exception):
    """A call failed in a way worth showing the user (bad key, region, etc.)."""


@dataclass
class ModelResult:
    text: str | None
    stop_reason: str | None
    model_used: str | None
    fallback_used: bool
    input_tokens: int | None
    output_tokens: int | None
    request_id: str | None
    duration_ms: int


def _bedrock_id(model: str) -> str:
    return model if model.startswith("anthropic.") else f"anthropic.{model}"


def _model_id(settings: OrgAiSettings) -> str:
    return _bedrock_id(settings.model) if settings.provider == "bedrock" else settings.model


def missing_configuration(settings: OrgAiSettings) -> str | None:
    """What still has to be filled in before AI can be used, if anything."""
    if settings.provider not in PROVIDERS:
        return "Choose an AI provider."
    if settings.provider in ("anthropic", "foundry") and not settings.api_key_encrypted:
        return "Add the API key for your AI provider."
    if settings.provider == "bedrock" and not settings.region:
        return "Add the AWS region for Amazon Bedrock."
    if settings.provider == "vertex" and not (settings.project_id and settings.region):
        return "Add the Google Cloud project and region for Vertex AI."
    if settings.provider == "foundry" and not settings.resource:
        return "Add the Microsoft Foundry resource name."
    return None


def _api_key(settings: OrgAiSettings) -> str:
    key = decrypt_secret(settings.api_key_encrypted) if settings.api_key_encrypted else None
    if not key:
        raise AiProviderError("The stored API key can't be read. An admin needs to enter it again.")
    return key


def _client(settings: OrgAiSettings):
    if settings.provider == "anthropic":
        return anthropic.Anthropic(api_key=_api_key(settings))
    if settings.provider == "bedrock":
        # Uses the server's AWS credentials (environment or IAM role).
        fallback = BetaRefusalFallbackMiddleware([{"model": _bedrock_id(FALLBACK_MODEL)}])
        return anthropic.AnthropicBedrockMantle(aws_region=settings.region, middleware=[fallback])
    if settings.provider == "vertex":
        # Uses the server's Google Cloud credentials (application default).
        fallback = BetaRefusalFallbackMiddleware([{"model": FALLBACK_MODEL}])
        return anthropic.AnthropicVertex(project_id=settings.project_id, region=settings.region, middleware=[fallback])
    if settings.provider == "foundry":
        return anthropic.AnthropicFoundry(resource=settings.resource, api_key=_api_key(settings))
    raise AiProviderError(f"Unknown AI provider: {settings.provider}")


def call_model(settings: OrgAiSettings, system: str, user: str, schema: dict) -> ModelResult:
    """One structured-output request. Raises AiProviderError with a message
    fit for the user on configuration, auth, permission and network errors."""
    client = _client(settings)
    request = dict(
        model=_model_id(settings),
        max_tokens=MAX_TOKENS,
        system=system,
        messages=[{"role": "user", "content": user}],
        output_config={"effort": "high", "format": {"type": "json_schema", "schema": schema}},
    )
    started = time.monotonic()
    try:
        if settings.provider == "anthropic":
            response = client.beta.messages.create(
                **request, betas=["server-side-fallback-2026-07-01"], fallbacks="default"
            )
        else:
            with BetaFallbackState():
                response = client.beta.messages.create(**request)
    except anthropic.AuthenticationError as exc:
        raise AiProviderError("The AI provider rejected the credentials. Check the API key or cloud credentials.") from exc
    except anthropic.PermissionDeniedError as exc:
        raise AiProviderError("The credentials don't have access to this model. Check the account's model access.") from exc
    except anthropic.NotFoundError as exc:
        raise AiProviderError(f"Model '{settings.model}' wasn't found for this provider or region.") from exc
    except anthropic.RateLimitError as exc:
        raise AiProviderError("The AI provider is rate-limiting requests. Try again in a minute.") from exc
    except anthropic.BadRequestError as exc:
        raise AiProviderError(f"The AI provider rejected the request: {exc.message}") from exc
    except anthropic.APIStatusError as exc:
        raise AiProviderError(f"The AI provider returned an error ({exc.status_code}). Try again later.") from exc
    except anthropic.APIConnectionError as exc:
        raise AiProviderError("Couldn't reach the AI provider. Check the network connection.") from exc

    iterations = getattr(response.usage, "iterations", None) or []
    return ModelResult(
        text=next((block.text for block in response.content if block.type == "text"), None),
        stop_reason=response.stop_reason,
        model_used=response.model,
        fallback_used=any(getattr(entry, "type", None) == "fallback_message" for entry in iterations),
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        request_id=getattr(response, "_request_id", None),
        duration_ms=int((time.monotonic() - started) * 1000),
    )
