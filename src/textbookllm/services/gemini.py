from __future__ import annotations

import os
from typing import Optional

from ..contracts import LLMClient


class GeminiClient(LLMClient):
	def __init__(self, model: str = "gemini‑2.0‑flash", api_key: Optional[str] = None) -> None:
		self._model_name = model
		self._api_key = api_key or os.environ.get("GEMINI_API_KEY")
		self._genai = None
		self._model = None
		print(f"[DEBUG] GeminiClient.__init__: API key present: {bool(self._api_key)}")
		if self._api_key:
			try:
				import google.generativeai as genai  # type: ignore
				print(f"[DEBUG] Configuring Gemini with model: {self._model_name}")
				genai.configure(api_key=self._api_key)
				self._genai = genai
				# List available models and use the first one that supports generateContent
				try:
					print("[DEBUG] Listing available models...")
					available_models = list(genai.list_models())
					print(f"[DEBUG] Found {len(available_models)} models")
					for model in available_models:
						if 'generateContent' in model.supported_generation_methods:
							model_name = model.name.replace('models/', '')
							print(f"[DEBUG] Trying model: {model_name}")
							try:
								self._model = genai.GenerativeModel(model_name)
								print(f"[DEBUG] Successfully initialized with model: {model_name}")
								self._model_name = model_name
								break
							except Exception as e:
								print(f"[DEBUG] Model {model_name} failed: {e}")
								continue
					if not self._model:
						raise Exception("No suitable model found")
				except Exception as list_error:
					print(f"[DEBUG] Could not list models: {list_error}, trying default...")
					# Fallback: try common model names
					for alt_model in ["gemini-pro", "models/gemini-pro"]:
						try:
							self._model = genai.GenerativeModel(alt_model)
							print(f"[DEBUG] Successfully initialized with fallback model: {alt_model}")
							self._model_name = alt_model
							break
						except:
							continue
					if not self._model:
						raise list_error
			except Exception as e:
				print(f"[DEBUG] Failed to initialize Gemini: {e}")
				self._genai = None
				self._model = None
		else:
			print("[DEBUG] No API key provided to GeminiClient")

	def generate(self, prompt: str) -> str:
		print(f"[DEBUG] GeminiClient.generate called with prompt length: {len(prompt)}")
		if not self._model:
			print("[DEBUG] Gemini model not configured, returning fallback")
			return "[Gemini not configured] " + prompt
		try:
			print("[DEBUG] Calling Gemini API...")
			resp = self._model.generate_content(prompt)
			print("[DEBUG] Received response from Gemini")
			# google-generativeai returns candidates; pick text
			text = getattr(resp, "text", None)
			if text:
				print(f"[DEBUG] Extracted text from response (length: {len(text)})")
				return text
			# fallback to concatenating parts
			parts = []
			for cand in getattr(resp, "candidates", []) or []:
				for part in getattr(cand, "content", {}).get("parts", []):
					val = part.get("text") if isinstance(part, dict) else str(part)
					if val:
						parts.append(val)
			result = "\n".join(parts) if parts else "[No content from Gemini]"
			print(f"[DEBUG] Using fallback text extraction (length: {len(result)})")
			return result
		except Exception as e:
			print(f"[DEBUG] Gemini API error: {e}")
			return f"[Gemini error] {e}"
