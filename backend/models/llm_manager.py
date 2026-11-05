import os
from typing import Dict, Any, Tuple
from models.base import BaseLLM
from models.gemini_provider import GeminiLLM
from models.ollama_provider import OllamaLLM


class LLMManager:
    def __init__(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "granite4.2:3b")

    def get_provider(self, preferred: str = "auto") -> Tuple[BaseLLM, str]:
        """
        Return the primary working LLM provider and its identifier.
        Supports 'auto', 'gemini', or 'ollama'.
        """
        pref = (preferred or "auto").lower()

        # If user explicitly requested Ollama
        if pref in ["ollama", "local", "granite", "granite4.2:3b"]:
            try:
                ollama = OllamaLLM()
                return ollama, f"Ollama ({self.ollama_model})"
            except Exception as e:
                raise RuntimeError(f"Ollama provider requested but failed: {str(e)}")

        # If user explicitly requested Gemini
        if pref in ["gemini", "cloud"]:
            try:
                gemini = GeminiLLM()
                return gemini, f"Gemini ({gemini.active_model})"
            except Exception as e:
                raise RuntimeError(f"Gemini provider requested but failed: {str(e)}")

        # Auto mode: Try Gemini first, fallback seamlessly to Ollama if Gemini fails
        if self.gemini_key:
            try:
                gemini = GeminiLLM()
                return gemini, f"Gemini ({gemini.active_model})"
            except Exception:
                pass

        # Try Ollama if Gemini not available
        try:
            ollama = OllamaLLM()
            return ollama, f"Ollama ({self.ollama_model})"
        except Exception:
            pass

        # Last resort if key exists
        if self.gemini_key:
            gemini = GeminiLLM()
            return gemini, f"Gemini ({gemini.active_model})"

        raise RuntimeError("No LLM provider is available. Please provide GEMINI_API_KEY or ensure local Ollama is running.")

    def get_status(self) -> Dict[str, Any]:
        """Diagnostic check of both LLM providers."""
        gemini_ok = False
        gemini_model = None
        gemini_error = None
        if self.gemini_key:
            try:
                g = GeminiLLM()
                gemini_ok = True
                gemini_model = g.active_model
            except Exception as e:
                gemini_error = str(e)
        else:
            gemini_error = "GEMINI_API_KEY not configured"

        ollama_ok = False
        ollama_error = None
        try:
            import httpx
            r = httpx.get("http://localhost:11434/api/tags", timeout=1.5)
            if r.status_code == 200:
                ollama_ok = True
            else:
                ollama_error = f"Ollama returned HTTP {r.status_code}"
        except Exception as e:
            ollama_error = f"Ollama not running: {str(e)}"

        return {
            "gemini": {
                "available": gemini_ok,
                "model": gemini_model,
                "error": gemini_error
            },
            "ollama": {
                "available": ollama_ok,
                "model": self.ollama_model,
                "error": ollama_error
            },
            "active_recommended": "gemini" if gemini_ok else ("ollama" if ollama_ok else "none")
        }

