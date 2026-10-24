"""Gemini conversation extraction with structured output and controlled errors."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from pydantic import ValidationError

from config import Settings, require_api_key
from prompts import PromptSettings, build_system_prompt
from schemas import LeadExtraction


def _gemini_json_schema() -> dict[str, Any]:
    """Return a JSON Schema payload without Pydantic's unsupported extra-field keyword.

    `response_schema=SomePydanticModel` makes some google-genai SDK versions convert
    `additionalProperties` to `additional_properties` inside the legacy Schema type,
    which the Gemini API rejects. `response_json_schema` accepts raw JSON Schema and
    avoids that conversion path. We still validate the returned JSON with Pydantic.
    """
    schema = LeadExtraction.model_json_schema()

    def remove_additional_properties(value: Any) -> None:
        if isinstance(value, dict):
            value.pop("additionalProperties", None)
            value.pop("additional_properties", None)
            for child in value.values():
                remove_additional_properties(child)
        elif isinstance(value, list):
            for child in value:
                remove_additional_properties(child)

    remove_additional_properties(schema)
    return schema


class AgentError(RuntimeError):
    """User-displayable error with an optional troubleshooting diagnostic."""
    def __init__(self, message: str, diagnostic: str | None = None):
        super().__init__(message)
        self.diagnostic = diagnostic


@dataclass(frozen=True)
class AgentConfig:
    settings: Settings
    prompt_settings: PromptSettings = PromptSettings()
    temperature: float = 0.2


def format_conversation(messages: Sequence[dict[str, str]]) -> str:
    """Format only known role/content fields; never accept caller-supplied system roles."""
    lines = []
    for message in messages:
        role = message.get("role", "")
        content = message.get("content", "")
        if role not in {"user", "assistant"}:
            continue
        if not isinstance(content, str) or not content.strip():
            continue
        label = "CUSTOMER" if role == "user" else "ASSISTANT"
        lines.append(f"{label}: {content.strip()}")
    if not lines:
        raise AgentError("No customer conversation was provided.")
    return "\n".join(lines)


def extract_lead(
    messages: Sequence[dict[str, str]],
    config: AgentConfig,
    client: Any = None,
) -> LeadExtraction:
    """
    Extract facts from the conversation using Gemini structured output.

    `client` is injectable so unit tests can run without a live API key.
    Qualification is deliberately performed elsewhere by qualification.py.
    """
    try:
        conversation = format_conversation(messages)
        if not config.settings.gemini_api_key:
            raise AgentError(
                "GEMINI_API_KEY is missing. Copy .env.example to .env and add "
                "your Gemini API key from Google AI Studio."
            )

        system_prompt = build_system_prompt(config.prompt_settings)
        temperature = max(0.0, min(1.0, config.temperature))
        if client is None:
            # Lazy import keeps unit tests usable without the SDK installed and avoids
            # initializing a live provider client until a real API call is requested.
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=config.settings.gemini_api_key)
            generation_config = types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                response_json_schema=_gemini_json_schema(),
                temperature=temperature,
            )
        else:
            # Simple dict configuration for injected test clients.
            generation_config = {
                "system_instruction": system_prompt,
                "response_mime_type": "application/json",
                "response_json_schema": _gemini_json_schema(),
                "temperature": temperature,
            }

        response = client.models.generate_content(
            model=config.settings.gemini_model,
            contents=conversation,
            config=generation_config,
        )

        response_text = getattr(response, "text", None)
        if not response_text:
            raise AgentError(
                "Gemini returned no usable text. Please retry or check the model response."
            )

        try:
            return LeadExtraction.model_validate_json(response_text)
        except ValidationError as exc:
            raise AgentError(
                "Gemini returned data that did not pass lead-schema validation. Please retry."
            ) from exc
    except AgentError:
        raise
    except Exception as exc:
        # Keep raw provider errors out of the UI because they may contain implementation details.
        diagnostic = f"{type(exc).__name__}: {exc}"
        # Avoid accidentally echoing the API key if a provider/library error includes it.
        if config.settings.gemini_api_key:
            diagnostic = diagnostic.replace(config.settings.gemini_api_key, "[REDACTED_API_KEY]")
        raise AgentError(
            "Gemini could not process this conversation. Check the troubleshooting details below.",
            diagnostic=diagnostic[:1200],
        ) from exc
