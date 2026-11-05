import os
import json
import re
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from ollama import Client

from models.base import BaseLLM
from schemas.llm import LLMResponse

load_dotenv()


class OllamaLLM(BaseLLM):
    def __init__(self, client=None, host: Optional[str] = None):
        self.model = os.getenv("OLLAMA_MODEL", "granite4.2:3b")
        self.host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.client = client or Client(host=self.host)

    def generate(self, messages: List[Dict[str, str]], tools: Optional[List[Dict[str, Any]]] = None) -> LLMResponse:
        try:
            response = self.client.chat(
                model=self.model,
                messages=messages,
                stream=False
            )
            content = response.message.content
            return self._parse_llm_output(content)
        except Exception as e:
            err_msg = str(e)
            if "refused" in err_msg.lower() or "connection" in err_msg.lower():
                raise ConnectionError(
                    f"Ollama server is not running at {self.host}. Please start Ollama or configure Gemini provider."
                )
            raise e

    def generate_stream(self, messages: List[Dict[str, str]], tools: Optional[List[Dict[str, Any]]] = None):
        """
        Yield live chunks from Ollama streaming API with full support for:
        - `thinking` tokens (internal model reasoning trace)
        - `content` tokens (action JSON or final text)
        """
        try:
            for chunk in self.client.chat(
                model=self.model,
                messages=messages,
                stream=True
            ):
                msg = getattr(chunk, "message", None)
                if msg is None and isinstance(chunk, dict):
                    msg = chunk.get("message", {})

                thinking = getattr(msg, "thinking", None)
                if thinking is None and isinstance(msg, dict):
                    thinking = msg.get("thinking")

                content = getattr(msg, "content", None)
                if content is None and isinstance(msg, dict):
                    content = msg.get("content")

                if thinking:
                    yield {"type": "thinking", "text": thinking}
                if content:
                    yield {"type": "content", "text": content}
        except Exception as e:
            err_msg = str(e)
            if "refused" in err_msg.lower() or "connection" in err_msg.lower():
                raise ConnectionError(
                    f"Ollama server is not running at {self.host}. Please start Ollama or configure Gemini provider."
                )
            raise e

    def _parse_llm_output(self, text: str) -> LLMResponse:
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
                # If multiple concatenated JSON blocks or trailing text, parse the first valid JSON object
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

        final_match = re.search(r'Final Answer:\s*(.*)', trimmed, re.DOTALL)
        if final_match:
            return LLMResponse(type="final", content=final_match.group(1).strip())

        return LLMResponse(type="final", content=trimmed)
