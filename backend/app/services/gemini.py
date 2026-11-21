import json
import logging
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from backend.app.config import get_settings

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


async def generate_structured(
    prompt: str,
    response_model: type[T],
    *,
    temperature: float = 0.2,
) -> T | None:
    settings = get_settings()
    if not settings.gemini_api_key:
        return None

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.gemini_api_key)
        response = await client.aio.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=response_model,
                temperature=temperature,
            ),
        )
        if response.parsed is not None:
            return response_model.model_validate(response.parsed)
        if not response.text:
            raise ValueError("Gemini returned an empty structured response.")
        return response_model.model_validate(json.loads(response.text))
    except (ValidationError, ValueError, json.JSONDecodeError):
        logger.exception("Gemini returned output that did not match the response schema.")
        return None
    except Exception:
        logger.exception("Gemini request failed; using the deterministic fallback.")
        return None
