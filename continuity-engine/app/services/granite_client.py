"""
IBM Granite / Ollama client for VERSE inference.
"""

import json
import requests


class GraniteClient:
    """
    Client for local Granite models through Ollama.

    Default:
        http://localhost:11434/api/generate
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434/api/generate",
        model: str = "granite3.1-dense:2b",
        timeout: int = 60,
    ):

        self.base_url = base_url
        self.model = model
        self.timeout = timeout


    def generate(self, prompt: str) -> dict:

        response = requests.post(
            self.base_url,
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
            },
            timeout=self.timeout,
        )

        response.raise_for_status()

        data = response.json()

        return self._parse_json(
            data.get("response", "{}")
        )


    def _parse_json(self, text: str) -> dict:
        """
        Repair common Granite JSON issues.
        """

        text = (
            text
            .replace("```json", "")
            .replace("```", "")
            .strip()
        )

        try:
            return json.loads(text)

        except json.JSONDecodeError:

            return {
                "facts": [],
                "raw_output": text
            }
