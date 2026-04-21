from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request

try:
    from google import genai
    from google.genai import types
except ImportError:  # pragma: no cover - optional dependency path
    genai = None
    types = None


@dataclass(frozen=True)
class ResolvedModelRoute:
    alias: str
    provider_mode: str
    model_name: str
    endpoint: str | None = None
    api_key: str | None = None
    api_version: str | None = None
    max_tokens_param: str | None = None


class MultiProviderRouter:
    def __init__(self) -> None:
        self.default_model_alias = os.getenv("COPILOT_DEFAULT_MODEL_ALIAS", "ggl2")

        self.gemini_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.gemini_fast_model = os.getenv("GEMINI_FAST_MODEL", "gemini-2.5-flash")
        self.gemini_client = genai.Client(api_key=self.gemini_api_key) if self.gemini_api_key and genai else None

        self.azure_openai_gpt4_endpoint = os.getenv("AZURE_OPENAI_GPT4_ENDPOINT", "")
        self.azure_openai_gpt4_api_key = os.getenv("AZURE_OPENAI_GPT4_API_KEY", "")
        self.azure_openai_gpt4_deployment = os.getenv("AZURE_OPENAI_GPT4_DEPLOYMENT", "")
        self.azure_openai_gpt4_api_version = os.getenv("AZURE_OPENAI_GPT4_API_VERSION", "2024-02-15-preview")

        self.azure_openai_gpt5_endpoint = os.getenv("AZURE_OPENAI_GPT5_ENDPOINT", "")
        self.azure_openai_gpt5_api_key = os.getenv("AZURE_OPENAI_GPT5_API_KEY", "")
        self.azure_openai_gpt5_deployment = os.getenv("AZURE_OPENAI_GPT5_DEPLOYMENT", "")
        self.azure_openai_gpt5_api_version = os.getenv("AZURE_OPENAI_GPT5_API_VERSION", "2024-12-01-preview")

        self.last_resolution: dict[str, object] | None = None

    def ask_text(
        self,
        prompt: str,
        *,
        model_alias: str | None = None,
        temperature: float = 0.2,
    ) -> str:
        return self._generate(prompt=prompt, model_alias=model_alias, temperature=temperature, json_mode=False)

    def ask_json(
        self,
        prompt: str,
        *,
        model_alias: str | None = None,
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        requested_alias = model_alias or self.default_model_alias
        text = self._generate(prompt=prompt, model_alias=model_alias, temperature=temperature, json_mode=True)
        original_resolution = dict(self.last_resolution or {})

        try:
            return self._parse_json_text(text)
        except json.JSONDecodeError as exc:
            repaired = self._repair_json_response(
                raw_text=text,
                requested_alias=requested_alias,
                parse_error=exc,
            )
            self.last_resolution = {
                **original_resolution,
                "json_repair_used": True,
                "json_repair_model": repaired["repair_model"],
                "json_parse_error": str(exc),
            }
            return repaired["data"]

    def get_last_resolution(self) -> dict[str, object] | None:
        return self.last_resolution

    def _generate(
        self,
        *,
        prompt: str,
        model_alias: str | None,
        temperature: float,
        json_mode: bool,
    ) -> str:
        requested_alias = model_alias or self.default_model_alias
        route = self._resolve_route(requested_alias)

        try:
            text = self._generate_with_route(route=route, prompt=prompt, temperature=temperature, json_mode=json_mode)
            self.last_resolution = {
                "model_requested": requested_alias,
                "model_used": route.alias,
                "provider_mode": route.provider_mode,
                "fallback_used": False,
            }
            return text
        except Exception as exc:
            if route.alias == "ggl2" and self._is_quota_error(exc):
                fallback_route = self._resolve_route("gpt4")
                text = self._generate_with_route(
                    route=fallback_route,
                    prompt=prompt,
                    temperature=temperature,
                    json_mode=json_mode,
                )
                self.last_resolution = {
                    "model_requested": requested_alias,
                    "model_used": fallback_route.alias,
                    "provider_mode": fallback_route.provider_mode,
                    "fallback_used": True,
                }
                return text
            raise

    def _generate_with_route(
        self,
        *,
        route: ResolvedModelRoute,
        prompt: str,
        temperature: float,
        json_mode: bool,
    ) -> str:
        if route.provider_mode == "gemini":
            return self._generate_with_gemini(route=route, prompt=prompt, temperature=temperature, json_mode=json_mode)
        if route.provider_mode == "azure-openai":
            return self._generate_with_azure_openai(route=route, prompt=prompt, temperature=temperature, json_mode=json_mode)
        raise ValueError(f"Unsupported provider mode: {route.provider_mode}")

    def _generate_with_gemini(
        self,
        *,
        route: ResolvedModelRoute,
        prompt: str,
        temperature: float,
        json_mode: bool,
    ) -> str:
        if not self.gemini_client:
            raise ValueError("Set GEMINI_API_KEY or GOOGLE_API_KEY before using the ggl2 route.")
        if not types:
            raise ValueError("google-genai is not installed, so the Gemini route is unavailable in this shell.")

        config_kwargs: dict[str, object] = {
            "temperature": temperature,
            "thinking_config": types.ThinkingConfig(thinking_budget=0),
        }
        if json_mode:
            config_kwargs["response_mime_type"] = "application/json"

        response = self.gemini_client.models.generate_content(
            model=route.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(**config_kwargs),
        )
        return (response.text or "").strip()

    @staticmethod
    def _generate_with_azure_openai(
        *,
        route: ResolvedModelRoute,
        prompt: str,
        temperature: float,
        json_mode: bool,
    ) -> str:
        if not route.endpoint or not route.api_key or not route.api_version:
            raise ValueError(f"Azure route {route.alias} is missing endpoint, api key, or api version.")

        endpoint = route.endpoint.rstrip("/") + "/"
        url = f"{endpoint}openai/deployments/{route.model_name}/chat/completions?api-version={route.api_version}"
        payload: dict[str, object] = {
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        if route.max_tokens_param == "max_completion_tokens":
            payload["max_completion_tokens"] = 800
        else:
            payload["max_tokens"] = 800

        req = urllib_request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "api-key": route.api_key},
            method="POST",
        )

        try:
            with urllib_request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib_error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise ValueError(f"Azure OpenAI request failed ({exc.code}): {body}") from exc
        except urllib_error.URLError as exc:
            raise ValueError(f"Azure OpenAI request failed: {exc}") from exc

        choices = data.get("choices", [])
        if not choices:
            raise ValueError(f"Azure OpenAI returned no choices: {data}")

        content = choices[0].get("message", {}).get("content", "")
        if isinstance(content, list):
            return "".join(part.get("text", "") for part in content if isinstance(part, dict)).strip()
        return str(content).strip()

    def _resolve_route(self, requested_alias: str) -> ResolvedModelRoute:
        alias = self._normalize_alias(requested_alias)

        if alias == "ggl2":
            if not self.gemini_api_key:
                raise ValueError("Model alias ggl2 requires a Gemini API key.")
            return ResolvedModelRoute(alias="ggl2", provider_mode="gemini", model_name=self.gemini_fast_model)

        if alias == "gpt4":
            if not self.azure_openai_gpt4_endpoint or not self.azure_openai_gpt4_api_key or not self.azure_openai_gpt4_deployment:
                raise ValueError("Model alias gpt4 requires Azure GPT-4 settings.")
            return ResolvedModelRoute(
                alias="gpt4",
                provider_mode="azure-openai",
                model_name=self.azure_openai_gpt4_deployment,
                endpoint=self.azure_openai_gpt4_endpoint,
                api_key=self.azure_openai_gpt4_api_key,
                api_version=self.azure_openai_gpt4_api_version,
                max_tokens_param="max_tokens",
            )

        if alias == "gpt5":
            if not self.azure_openai_gpt5_endpoint or not self.azure_openai_gpt5_api_key or not self.azure_openai_gpt5_deployment:
                raise ValueError("Model alias gpt5 requires Azure GPT-5 settings.")
            return ResolvedModelRoute(
                alias="gpt5",
                provider_mode="azure-openai",
                model_name=self.azure_openai_gpt5_deployment,
                endpoint=self.azure_openai_gpt5_endpoint,
                api_key=self.azure_openai_gpt5_api_key,
                api_version=self.azure_openai_gpt5_api_version,
                max_tokens_param="max_completion_tokens",
            )

        raise ValueError(f"Unknown model alias: {requested_alias}")

    @staticmethod
    def _normalize_alias(alias: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", "", alias.lower())
        alias_map = {
            "": "ggl2",
            "default": "ggl2",
            "ggl2": "ggl2",
            "gemini": "ggl2",
            "flash": "ggl2",
            "gemini25flash": "ggl2",
            "gpt4": "gpt4",
            "gpt4o": "gpt4",
            "4o": "gpt4",
            "gpt5": "gpt5",
            "gpt54nano": "gpt5",
            "gpt5nano": "gpt5",
            "nano": "gpt5",
        }
        return alias_map.get(normalized, normalized)

    @staticmethod
    def _is_quota_error(exc: Exception) -> bool:
        message = str(exc).lower()
        return "429" in message or "resource_exhausted" in message or "quota exceeded" in message

    @staticmethod
    def _parse_json_text(text: str) -> dict[str, Any]:
        candidate_errors: list[json.JSONDecodeError] = []
        for candidate in MultiProviderRouter._candidate_json_texts(text):
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError as exc:
                candidate_errors.append(exc)
                continue
            if isinstance(parsed, dict):
                return parsed
            raise json.JSONDecodeError("JSON payload was not an object.", candidate, 0)

        if candidate_errors:
            raise candidate_errors[-1]
        raise json.JSONDecodeError("No JSON object found in model response.", text, 0)

    @staticmethod
    def _candidate_json_texts(text: str) -> list[str]:
        raw_text = (text or "").strip()
        candidates: list[str] = []

        def add_candidate(value: str | None) -> None:
            normalized = (value or "").strip()
            if normalized and normalized not in candidates:
                candidates.append(normalized)

        add_candidate(raw_text)
        add_candidate(MultiProviderRouter._strip_markdown_fences(raw_text))

        extracted_object = MultiProviderRouter._extract_first_json_object(raw_text)
        add_candidate(extracted_object)
        add_candidate(MultiProviderRouter._strip_markdown_fences(extracted_object or ""))

        for candidate in list(candidates):
            add_candidate(MultiProviderRouter._sanitize_json_candidate(candidate))

        return candidates

    @staticmethod
    def _strip_markdown_fences(text: str) -> str:
        stripped = (text or "").strip()
        if stripped.startswith("```"):
            stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.IGNORECASE)
            stripped = re.sub(r"\s*```$", "", stripped)
        return stripped.strip()

    @staticmethod
    def _sanitize_json_candidate(text: str) -> str:
        candidate = text.strip()
        if not candidate:
            return candidate
        candidate = MultiProviderRouter._escape_newlines_inside_strings(candidate)
        candidate = re.sub(r",(\s*[}\]])", r"\1", candidate)
        return candidate

    @staticmethod
    def _escape_newlines_inside_strings(text: str) -> str:
        parts: list[str] = []
        in_string = False
        escape = False

        for char in text:
            if escape:
                parts.append(char)
                escape = False
                continue

            if char == "\\":
                parts.append(char)
                escape = True
                continue

            if char == '"':
                parts.append(char)
                in_string = not in_string
                continue

            if in_string and char == "\n":
                parts.append("\\n")
                continue

            if in_string and char == "\r":
                continue

            parts.append(char)

        return "".join(parts)

    def _repair_json_response(
        self,
        *,
        raw_text: str,
        requested_alias: str,
        parse_error: json.JSONDecodeError,
    ) -> dict[str, Any]:
        repair_alias = self._preferred_json_repair_alias(requested_alias)
        repair_prompt = (
            "Repair the following malformed JSON from a travel-media app.\n"
            "Return ONLY one valid JSON object.\n"
            "Keep the original keys and preserve as much content as possible.\n"
            "If a field is truncated or unclear, keep it short but valid rather than inventing extra structure.\n"
            f"Parser error: {parse_error}\n"
            "Malformed JSON:\n"
            f"{raw_text}"
        )

        repaired_text = self._generate(
            prompt=repair_prompt,
            model_alias=repair_alias,
            temperature=0.0,
            json_mode=True,
        )
        repaired_data = self._parse_json_text(repaired_text)
        return {"data": repaired_data, "repair_model": repair_alias}

    def _preferred_json_repair_alias(self, requested_alias: str) -> str:
        normalized_requested_alias = self._normalize_alias(requested_alias)
        if normalized_requested_alias != "gpt4":
            try:
                self._resolve_route("gpt4")
                return "gpt4"
            except Exception:
                pass
        return normalized_requested_alias or "ggl2"

    @staticmethod
    def _extract_first_json_object(text: str) -> str | None:
        start = -1
        depth = 0
        in_string = False
        escape = False

        for index, char in enumerate(text):
            if start == -1:
                if char == "{":
                    start = index
                    depth = 1
                continue

            if escape:
                escape = False
                continue

            if char == "\\":
                escape = True
                continue

            if char == '"':
                in_string = not in_string
                continue

            if in_string:
                continue

            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[start : index + 1]

        return None
