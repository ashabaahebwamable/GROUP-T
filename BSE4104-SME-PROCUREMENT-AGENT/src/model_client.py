import json
import os
from typing import Any, Dict
from urllib import error, request

from dotenv import load_dotenv

load_dotenv()

MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "google")
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-3.6-flash")


def _parse_gemini_payload(raw_payload: Dict[str, Any]) -> Dict[str, Any]:
    candidates = raw_payload.get("candidates") or []

    if not candidates:
        raise ValueError("No model candidates returned")

    content = candidates[0].get("content") or {}
    parts = content.get("parts") or []

    if not parts:
        raise ValueError("No text parts returned by the model")

    text = parts[0].get("text")

    if not text:
        raise ValueError("Empty model response")

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Model returned non-JSON output: {text[:200]}"
        ) from exc


def call_model(
    prompt: str,
    model_name: str | None = None,
    api_key: str | None = None,
) -> Dict[str, Any]:
    """Call Gemini with a text prompt expecting a JSON response."""

    if not prompt or not str(prompt).strip():
        raise ValueError("Prompt text is required")

    resolved_model = model_name or MODEL_NAME
    resolved_key = api_key or os.getenv("MODEL_API_KEY")

    if not resolved_key:
        raise ValueError(
            "MODEL_API_KEY is not configured. "
            "Add it to the environment or .env file."
        )

    endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{resolved_model}:generateContent"
        f"?key={resolved_key}"
    )

    body = json.dumps(
        {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.0,
                "responseMimeType": "application/json",
            },
        }
    ).encode("utf-8")

    last_error = None

    for attempt in range(3):
        req = request.Request(
            endpoint,
            data=body,
            headers={
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=60) as response:
                payload = json.loads(
                    response.read().decode("utf-8")
                )

                return _parse_gemini_payload(payload)

        except error.HTTPError as exc:
            details = exc.read().decode(
                "utf-8",
                errors="replace",
            )

            last_error = RuntimeError(
                f"Gemini API request failed: {details}"
            )

            if exc.code in {
                429,
                500,
                502,
                503,
                504,
            } and attempt < 2:
                continue

            raise last_error from exc

        except error.URLError as exc:
            last_error = RuntimeError(
                f"Unable to reach Gemini API: {exc.reason}"
            )

            if attempt < 2:
                continue

            raise last_error from exc

    if last_error is not None:
        raise last_error

    raise RuntimeError(
        "Gemini API request failed without a recorded error"
    )


def call_model_with_tools(
    contents: list[dict],
    tools: list[dict],
    model_name: str | None = None,
    api_key: str | None = None,
) -> Dict[str, Any]:
    """Call Gemini generateContent with registered function declarations.

    This function is used by the bounded agentic workflow.

    The model receives:
    - the conversation contents
    - the approved tool/function declarations

    The model may then return a functionCall that is handled by
    the application's tool router.
    """

    if not contents:
        raise ValueError("Model contents are required")

    if not tools:
        raise ValueError("At least one tool declaration is required")

    resolved_model = model_name or MODEL_NAME
    resolved_key = api_key or os.getenv("MODEL_API_KEY")

    if not resolved_key:
        raise ValueError(
            "MODEL_API_KEY is not configured. "
            "Add it to the environment or .env file."
        )

    endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{resolved_model}:generateContent"
    )

    body = json.dumps(
        {
            "contents": contents,
            "tools": [
                {
                    "functionDeclarations": tools,
                }
            ],
            "generationConfig": {
                "temperature": 0.0,
            },
        }
    ).encode("utf-8")

    last_error = None

    for attempt in range(3):
        req = request.Request(
            endpoint,
            data=body,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": resolved_key,
            },
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=60) as response:
                return json.loads(
                    response.read().decode("utf-8")
                )

        except error.HTTPError as exc:
            details = exc.read().decode(
                "utf-8",
                errors="replace",
            )

            last_error = RuntimeError(
                f"Gemini API request failed: {details}"
            )

            if exc.code in {
                429,
                500,
                502,
                503,
                504,
            } and attempt < 2:
                continue

            raise last_error from exc

        except error.URLError as exc:
            last_error = RuntimeError(
                f"Unable to reach Gemini API: {exc.reason}"
            )

            if attempt < 2:
                continue

            raise last_error from exc

    if last_error is not None:
        raise last_error

    raise RuntimeError(
        "Gemini API request failed without a recorded error"
    )


if __name__ == "__main__":
    prompt = (
        "Return JSON with supplier_name and currency for: "
        "Supplier: Demo Trading; Currency: UGX"
    )

    print(
        json.dumps(
            call_model(prompt),
            indent=2,
        )
    )