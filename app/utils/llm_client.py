
import json
import re
from typing import Any, Dict, Optional

import google.generativeai as genai
from app.config import google_api_key
import logging

logger = logging.getLogger(__name__)

genai.configure(api_key=google_api_key)


model = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    generation_config=genai.GenerationConfig(
        temperature=0.3,
        max_output_tokens=2048,
    ),
)

json_model = genai.GenerativeModel(
    model_name="gemini-2.0-flash",  # or gemini-1.5-pro for better JSON compliance
    generation_config=genai.GenerationConfig(
        temperature=0.2,
        response_mime_type="application/json",  # This is the magic!
    ),
)


async def invoke_llm_async(
    prompt: str,
    expect_json: bool = True,
    fallback: Optional[Dict[str, Any]] = None
) -> Any:
    """
    Unified async LLM caller with reliable JSON support.
    """
    try:
        response = await (
            json_model.generate_content_async(prompt)
            if expect_json
            else model.generate_content_async(prompt)
        )

        text = response.text.strip()


        if expect_json and (text.startswith("```") or "```" in text):
            text = re.sub(r"^```json\s*|```$", "", text, flags=re.MULTILINE).strip()

        return json.loads(text) if expect_json else text

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}\nRaw output: {text[:500]}")
        return fallback or {"error": "Invalid JSON from AI", "raw": text[:1000]}
    except Exception as e:
        logger.error(f"Gemini error: {e}")
        return fallback or {"error": str(e)}