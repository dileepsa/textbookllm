"""Gemini LLM client implementation."""

from __future__ import annotations

import os
from typing import Optional

from ..contracts import LLMClient


class GeminiClient(LLMClient):
	"""Client for Google's Gemini LLM using the generativeai SDK."""

	def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None) -> None:
		"""Initialize Gemini client.
		
		Args:
			model: Model name to use. If None, auto-detects from available models.
			api_key: API key. If None, reads from GEMINI_API_KEY environment variable.
		"""
		self._model_name = model
		self._api_key = api_key or os.environ.get("GEMINI_API_KEY")
		self._genai = None
		self._model = None
		
		if not self._api_key:
			return
			
		try:
			import google.generativeai as genai  # type: ignore
			genai.configure(api_key=self._api_key)
			self._genai = genai
			
			# Auto-detect model if not specified
			if not self._model_name:
				self._initialize_model_from_list(genai)
			else:
				try:
					self._model = genai.GenerativeModel(self._model_name)
				except Exception:
					# Fallback to auto-detection
					self._initialize_model_from_list(genai)
		except Exception:
			self._genai = None
			self._model = None
	
	def _initialize_model_from_list(self, genai) -> None:
		"""Initialize model by listing available models.
		
		Args:
			genai: The google.generativeai module.
		"""
		try:
			available_models = list(genai.list_models())
			for model_info in available_models:
				if 'generateContent' in model_info.supported_generation_methods:
					model_name = model_info.name.replace('models/', '')
					try:
						self._model = genai.GenerativeModel(model_name)
						self._model_name = model_name
						return
					except Exception:
						continue
		except Exception:
			pass
		
		# Fallback to common model names
		for alt_model in ["gemini-pro", "models/gemini-pro"]:
			try:
				self._model = genai.GenerativeModel(alt_model)
				self._model_name = alt_model
				return
			except Exception:
				continue

	def generate(self, prompt: str) -> str:
		"""Generate a response using Gemini.
		
		Args:
			prompt: The input prompt.
			
		Returns:
			Generated text response, or error message if generation fails.
		"""
		if not self._model:
			return "[Gemini not configured] " + prompt
		
		try:
			resp = self._model.generate_content(prompt)
			# google-generativeai returns candidates; pick text
			text = getattr(resp, "text", None)
			if text:
				return text
			
			# Fallback to concatenating parts from candidates
			parts = []
			for cand in getattr(resp, "candidates", []) or []:
				for part in getattr(cand, "content", {}).get("parts", []):
					val = part.get("text") if isinstance(part, dict) else str(part)
					if val:
						parts.append(val)
			return "\n".join(parts) if parts else "[No content from Gemini]"
		except Exception as e:
			return f"[Gemini error] {e}"
