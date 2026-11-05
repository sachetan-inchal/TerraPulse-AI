import os
import json
import re
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import APIError

from models.base import BaseLLM
from schemas.llm import LLMResponse

load_dotenv()


class GeminiLLM(BaseLLM):
    FALLBACK_MODELS = [
        "gemini-3-flash-preview",
        "gemini-2.5-flash",
        "gemini-2.5-pro",
        "gemini-flash-latest",
        "gemini-3.1-flash-lite-preview",
        "gemini-3.8-flash"
    ]

    def __init__(self, client=None, model: Optional[str] = None):
        configured = model or os.getenv("GEMINI_MODEL")
        # For live client when .env specifies retired gemini-3.7-flash, route to gemini-3-flash-preview
        if client is None and (not configured or "3.7" in configured):
            configured = "gemini-3-flash-preview"
        self.model = configured or "gemini-3-flash-preview"
        self.active_model = self.model

        api_key = os.getenv("GEMINI_API_KEY")
        if client is None and not api_key:
            raise ValueError("GEMINI_API_KEY is missing from environment")

        self.client = client or genai.Client(api_key=api_key)

    def _prepare_contents(self, messages: List[Dict[str, str]]):
        contents = []
        system_instructions = []

        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")

            if role == "system":
                system_instructions.append(content)
                continue

            if role == "assistant":
                role = "model"
            elif role != "user":
                role = "user"

            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=content)]
                )
            )

        return contents, system_instructions

    def generate(self, messages: List[Dict[str, str]], tools: Optional[List[Dict[str, Any]]] = None) -> LLMResponse:
        """
        Generate response from Gemini with automatic resilience to model retirement,
        transient capacity errors, or rate limits.
        """
        contents, system_instructions = self._prepare_contents(messages)
        config = types.GenerateContentConfig(
            system_instruction="\n".join(system_instructions) if system_instructions else None,
            temperature=0.2,
            max_output_tokens=2048
        )

        # Try active/configured model, then fallback candidates if retired/overloaded/rate-limited
        candidate_models = [self.active_model]
        for fb in self.FALLBACK_MODELS:
            if fb not in candidate_models:
                candidate_models.append(fb)

        last_error = None
        for cand in candidate_models:
            try:
                response = self.client.models.generate_content(
                    model=cand,
                    contents=contents,
                    config=config
                )
                if response and response.text:
                    self.active_model = cand
                    return self._parse_llm_output(response.text)
            except Exception as e:
                last_error = e
                err_str = str(e)
                # If error is 404 (retired), 503 (high demand), or 429 (rate limit/quota), try next candidate
                is_recoverable = any(code in err_str for code in [
                    "404", "503", "429", "NOT_FOUND", "UNAVAILABLE", "RESOURCE_EXHAUSTED"
                ]) or "quota" in err_str.lower() or "rate" in err_str.lower()

                if is_recoverable:
                    continue
                else:
                    raise e

        raise RuntimeError(f"All Gemini models exhausted. Last error: {last_error}")

    def generate_stream(self, messages: List[Dict[str, str]], tools: Optional[List[Dict[str, Any]]] = None):
        """Yield live text chunks from Gemini streaming API."""
        contents, system_instructions = self._prepare_contents(messages)
        config = types.GenerateContentConfig(
            system_instruction="\n".join(system_instructions) if system_instructions else None,
            temperature=0.2,
            max_output_tokens=2048
        )

        candidate_models = [self.active_model]
        for fb in self.FALLBACK_MODELS:
            if fb not in candidate_models:
                candidate_models.append(fb)

        for cand in candidate_models:
            try:
                for chunk in self.client.models.generate_content_stream(
                    model=cand,
                    contents=contents,
                    config=config
                ):
                    if chunk.text:
                        self.active_model = cand
                        yield {"type": "content", "text": chunk.text}
                return
            except Exception:
                continue

    def _parse_llm_output(self, text: str) -> LLMResponse:
        """Parse model output into either a tool_call or final response."""
        trimmed = text.strip()

        # 1. Check for fenced code block ```json ... ```
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', trimmed, re.DOTALL)
        candidate_json = json_match.group(1) if json_match else None

        # 2. If not fenced, extract JSON substring from outermost { and }
        if not candidate_json:
            start_idx = trimmed.find("{")
            end_idx = trimmed.rfind("}")
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                candidate_json = trimmed[start_idx:end_idx + 1]

        if candidate_json:
            parsed = None
            try:
                parsed = json.loads(candidate_json)
            except Exception:
                try:
                    start_pos = candidate_json.find("{")
                    if start_pos != -1:
                        parsed, _ = json.JSONDecoder().raw_decode(candidate_json[start_pos:])
                except Exception:
                    parsed = None

            if parsed and isinstance(parsed, dict):
                action = parsed.get("action")
                args = (
                    parsed.get("arguments")
                    or parsed.get("parameters")
                    or parsed.get("action_input")
                    or {}
                )
                if action and action != "final_answer":
                    return LLMResponse(
                        type="tool_call",
                        tool_name=action,
                        arguments=args if isinstance(args, dict) else {"input": args}
                    )
                elif action == "final_answer" or "answer" in parsed:
                    ans = (
                        args.get("answer")
                        if isinstance(args, dict) and args.get("answer")
                        else (parsed.get("answer") or parsed.get("summary") or json.dumps(parsed, indent=2))
                    )
                    return LLMResponse(
                        type="final",
                        content=ans
                    )

        # Check for ReAct text pattern
        action_match = re.search(r'Action:\s*([a-zA-Z0-9_]+)', trimmed)
        input_match = re.search(r'Action Input:\s*(\{.*?\})', trimmed, re.DOTALL)

        if action_match:
            action_name = action_match.group(1).strip()
            args = {}
            if input_match:
                try:
                    args = json.loads(input_match.group(1).strip())
                except Exception:
                    args = {"input": input_match.group(1).strip()}

            if action_name.lower() != "final_answer":
                return LLMResponse(
                    type="tool_call",
                    tool_name=action_name,
                    arguments=args
                )

        # Check for Final Answer: prefix
        final_match = re.search(r'Final Answer:\s*(.*)', trimmed, re.DOTALL)
        if final_match:
            return LLMResponse(type="final", content=final_match.group(1).strip())

        return LLMResponse(type="final", content=trimmed)
