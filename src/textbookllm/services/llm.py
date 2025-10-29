"""Echo LLM implementation for testing."""
from __future__ import annotations

from typing import List

from ..contracts import LLMClient
from ..models import Chunk


class EchoLLM(LLMClient):
	"""Simple echo LLM that returns the prompt as-is."""
	
	def generate(self, prompt: str) -> str:
		"""Generate an answer by echoing the prompt."""
		return prompt

