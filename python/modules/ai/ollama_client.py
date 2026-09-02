"""
Ollama Client - Wrapper for local Ollama LLM API.
"""

import requests
import json
from typing import Any, Dict, Optional
from logger import get_logger
from config import OLLAMA_API_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT

logger = get_logger('ai.ollama')


class OllamaClient:
    """Client for interacting with local Ollama LLM."""

    def __init__(
        self,
        api_url: str = OLLAMA_API_URL,
        model: str = OLLAMA_MODEL,
        timeout: int = OLLAMA_TIMEOUT
    ):
        """
        Initialize Ollama client.

        Args:
            api_url: Ollama API URL (default: http://localhost:11434)
            model: Model name (default: gemma:7b)
            timeout: Request timeout in seconds
        """
        self.api_url = api_url
        self.model = model
        self.timeout = timeout
        self.logger = logger

    def health_check(self) -> bool:
        """
        Check if Ollama is running and accessible.

        Returns:
            True if Ollama is accessible
        """
        try:
            response = requests.get(
                f"{self.api_url}/api/tags",
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"Ollama health check failed: {e}")
            return False

    def generate_response(
        self,
        prompt: str,
        stream: bool = False
    ) -> Optional[str]:
        """
        Generate response from LLM.

        Args:
            prompt: Input prompt
            stream: Whether to stream response

        Returns:
            Generated text or None if error
        """
        try:
            url = f"{self.api_url}/api/generate"
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": stream,
            }

            response = requests.post(
                url,
                json=payload,
                timeout=self.timeout
            )

            if response.status_code != 200:
                self.logger.error(f"Ollama generation failed: {response.status_code}")
                return None

            if stream:
                # For streaming, join all response parts
                text_parts = []
                for line in response.iter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            if 'response' in data:
                                text_parts.append(data['response'])
                        except json.JSONDecodeError:
                            pass
                return ''.join(text_parts)
            else:
                data = response.json()
                return data.get('response')

        except requests.exceptions.Timeout:
            self.logger.error(f"Ollama request timed out after {self.timeout}s")
            return None
        except Exception as e:
            self.logger.error(f"Error generating response: {e}")
            return None
