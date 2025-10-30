from __future__ import annotations

import os
import tempfile
import base64
import mimetypes
from pathlib import Path
from typing import Optional, Tuple

try:
    import google.generativeai as genai
    from PIL import Image
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    print(f"[WARNING] Multimedia dependencies not available: {e}")
    DEPENDENCIES_AVAILABLE = False
    genai = None
    Image = None


class MultimediaProcessor:
    """Processes multimedia files to extract text content for LLM understanding."""
    
    def __init__(self, api_key: Optional[str] = None, use_base64: bool = False):
        self._api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self._vision_model = None
        self._multimodal_model = None
        self._use_base64 = use_base64  # Toggle between BASE64 and text description
        
        if not DEPENDENCIES_AVAILABLE:
            print("[WARNING] Multimedia processing disabled - missing dependencies")
            return
            
        if self._api_key:
            try:
                genai.configure(api_key=self._api_key)
                # Use the same working model that GeminiClient uses
                # Try to find a working multimodal model
                available_models = list(genai.list_models())
                multimodal_model_name = None
                
                # Look for models that support both generateContent and vision
                for model in available_models:
                    if 'generateContent' in model.supported_generation_methods:
                        model_name = model.name.replace('models/', '')
                        # Try models that are likely to support vision
                        if any(keyword in model_name.lower() for keyword in ['pro', 'vision', 'flash']):
                            try:
                                test_model = genai.GenerativeModel(model_name)
                                multimodal_model_name = model_name
                                print(f"[DEBUG] Found working multimodal model: {model_name}")
                                break
                            except:
                                continue
                
                if multimodal_model_name:
                    self._vision_model = genai.GenerativeModel(multimodal_model_name)
                    self._multimodal_model = genai.GenerativeModel(multimodal_model_name)
                    print(f"[DEBUG] Multimedia processor using model: {multimodal_model_name}")
                else:
                    print("[WARNING] No suitable multimodal model found")
                    
            except Exception as e:
                print(f"[WARNING] Failed to initialize Gemini for multimedia: {e}")
        else:
            print("[WARNING] No Gemini API key - multimedia processing will use fallback")
    
    def encode_file_to_base64(self, file_path: str) -> str:
        """
        Encode a file to BASE64 string.
        
        Args:
            file_path: Path to the file to encode
            
        Returns:
            BASE64 encoded string with data URI format
        """
        try:
            with open(file_path, 'rb') as file:
                file_data = file.read()
                base64_data = base64.b64encode(file_data).decode('utf-8')
                
            # Get MIME type
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                # Fallback MIME types based on extension
                ext = Path(file_path).suffix.lower()
                mime_map = {
                    '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
                    '.png': 'image/png', '.gif': 'image/gif',
                    '.mp3': 'audio/mpeg', '.wav': 'audio/wav',
                    '.mp4': 'video/mp4', '.avi': 'video/x-msvideo'
                }
                mime_type = mime_map.get(ext, 'application/octet-stream')
            
            # Return data URI format
            return f"data:{mime_type};base64,{base64_data}"
            
        except Exception as e:
            return f"[Error encoding {Path(file_path).name}]: {str(e)}"
    
    def process_file_as_base64(self, file_path: str) -> str:
        """
        Process a multimedia file and return BASE64 encoded data.
        
        Args:
            file_path: Path to the file to process
            
        Returns:
            BASE64 encoded data with metadata
        """
        file_type, _ = self.get_file_type(file_path)
        base64_data = self.encode_file_to_base64(file_path)
        
        if base64_data.startswith("[Error"):
            return base64_data
        
        # Add metadata and instructions for the LLM
        file_info = {
            'file_name': Path(file_path).name,
            'file_type': file_type,
            'data': base64_data
        }
        
        instruction = f"""
[{file_type.upper()} FILE: {file_info['file_name']}]
This is a {file_type} file encoded in BASE64 format. Please analyze the content and provide detailed information about what you observe.

File Type: {file_type}
Data: {base64_data}

Instructions:
- If this is an image, describe the visual content, objects, text, colors, and composition
- If this is audio, provide transcription and analysis of the content
- If this is video, describe both visual and audio elements
- Extract any text, numbers, or important information visible/audible in the media
"""
        
        return instruction
    
    def process_image(self, image_path: str) -> str:
        """
        Process an image file and extract descriptive text content.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Descriptive text content of the image
        """
        if not DEPENDENCIES_AVAILABLE:
            return f"[Image file: {Path(image_path).name}] - Multimedia processing not available (missing dependencies)"
        
        if not self._vision_model:
            return f"[Image file: {Path(image_path).name}] - Gemini API not configured for image processing"
        
        try:
            # Load and validate image
            print(f"[DEBUG] Loading image: {image_path}")
            
            # First try to use Gemini directly without PIL processing
            try:
                # Upload image directly to Gemini for processing
                print("[DEBUG] Uploading image directly to Gemini...")
                image_file = genai.upload_file(path=image_path)
                
                # Create a comprehensive prompt for image analysis
                prompt = """
                Analyze this image in detail and provide a comprehensive description that includes:
                
                1. Main subjects/objects in the image
                2. Scene description and setting
                3. Colors, composition, and visual elements
                4. Any text visible in the image (OCR)
                5. Important details that would be useful for understanding the content
                6. Context or purpose if apparent
                
                Make the description detailed enough that someone could understand the key information from the image without seeing it.
                """
                
                print("[DEBUG] Calling Gemini vision model...")
                response = self._vision_model.generate_content([prompt, image_file])
                
                # Clean up uploaded file
                genai.delete_file(image_file.name)
                
                print("[DEBUG] Got response from Gemini vision")
                
                # Extract text from response
                if hasattr(response, 'text') and response.text:
                    result = f"[Image Analysis]\n{response.text}"
                    print(f"[DEBUG] Successfully extracted text (length: {len(result)})")
                    return result
                else:
                    print(f"[DEBUG] No text in response: {response}")
                    # Try to extract from candidates
                    if hasattr(response, 'candidates') and response.candidates:
                        candidate = response.candidates[0]
                        if hasattr(candidate, 'content') and candidate.content:
                            parts = candidate.content.parts
                            if parts and len(parts) > 0:
                                text = parts[0].text
                                result = f"[Image Analysis]\n{text}"
                                print(f"[DEBUG] Extracted from candidates (length: {len(result)})")
                                return result
                    return f"[Image file: {Path(image_path).name}] - Could not generate description (empty response)"
                    
            except Exception as direct_error:
                print(f"[DEBUG] Direct Gemini upload failed: {direct_error}")
                
                # Fallback: Try PIL processing first, then Gemini
                try:
                    image = Image.open(image_path)
                    print(f"[DEBUG] Image loaded with PIL: {image.size}, mode: {image.mode}")
                    
                    # Create a comprehensive prompt for image analysis
                    prompt = """
                    Analyze this image in detail and provide a comprehensive description that includes:
                    
                    1. Main subjects/objects in the image
                    2. Scene description and setting
                    3. Colors, composition, and visual elements
                    4. Any text visible in the image (OCR)
                    5. Important details that would be useful for understanding the content
                    6. Context or purpose if apparent
                    
                    Make the description detailed enough that someone could understand the key information from the image without seeing it.
                    """
                    
                    print("[DEBUG] Calling Gemini vision model with PIL image...")
                    response = self._vision_model.generate_content([prompt, image])
                    print("[DEBUG] Got response from Gemini vision")
                    
                    # Extract text from response
                    if hasattr(response, 'text') and response.text:
                        result = f"[Image Analysis]\n{response.text}"
                        print(f"[DEBUG] Successfully extracted text (length: {len(result)})")
                        return result
                    else:
                        return f"[Image file: {Path(image_path).name}] - Could not generate description (empty response)"
                        
                except Exception as pil_error:
                    print(f"[DEBUG] PIL processing also failed: {pil_error}")
                    return f"[Image file: {Path(image_path).name}] - Error processing: PIL cannot read image format and direct upload failed"
                
        except Exception as e:
            print(f"[DEBUG] Exception in image processing: {e}")
            import traceback
            traceback.print_exc()
            return f"[Image file: {Path(image_path).name}] - Error processing: {str(e)}"
    
    def process_audio(self, audio_path: str) -> str:
        """
        Process an audio file and extract text content (transcription + analysis).
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            Transcribed and analyzed text content of the audio
        """
        if not DEPENDENCIES_AVAILABLE:
            return f"[Audio file: {Path(audio_path).name}] - Multimedia processing not available (missing dependencies)"
            
        if not self._multimodal_model:
            return f"[Audio file: {Path(audio_path).name}] - Gemini API not configured for audio processing"
        
        try:
            # Upload audio file to Gemini
            audio_file = genai.upload_file(path=audio_path)
            
            # Create prompt for audio transcription and analysis
            prompt = """
            Please process this audio file and provide:
            
            1. Complete transcription of all spoken content
            2. Summary of key topics discussed
            3. Important information or insights
            4. Speaker analysis (if multiple speakers)
            5. Context and purpose of the audio
            
            Format the output clearly with sections for transcription and analysis.
            """
            
            response = self._multimodal_model.generate_content([prompt, audio_file])
            
            # Clean up uploaded file
            genai.delete_file(audio_file.name)
            
            if hasattr(response, 'text') and response.text:
                return f"[Audio Analysis]\n{response.text}"
            else:
                return f"[Audio file: {Path(audio_path).name}] - Could not generate transcription"
                
        except Exception as e:
            return f"[Audio file: {Path(audio_path).name}] - Error processing: {str(e)}"
    
    def process_video(self, video_path: str) -> str:
        """
        Process a video file and extract text content (visual + audio analysis).
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Analyzed text content of the video
        """
        if not DEPENDENCIES_AVAILABLE:
            return f"[Video file: {Path(video_path).name}] - Multimedia processing not available (missing dependencies)"
            
        if not self._multimodal_model:
            return f"[Video file: {Path(video_path).name}] - Gemini API not configured for video processing"
        
        try:
            # Upload video file to Gemini
            video_file = genai.upload_file(path=video_path)
            
            # Wait for processing to complete
            import time
            while video_file.state.name == "PROCESSING":
                time.sleep(2)
                video_file = genai.get_file(video_file.name)
            
            if video_file.state.name == "FAILED":
                genai.delete_file(video_file.name)
                return f"[Video file: {Path(video_path).name}] - Processing failed"
            
            # Create comprehensive prompt for video analysis
            prompt = """
            Please analyze this video comprehensively and provide:
            
            1. Complete transcription of all spoken content/dialogue
            2. Detailed description of visual content and scenes
            3. Key actions, events, or demonstrations shown
            4. Important visual information (text, charts, diagrams)
            5. Context and purpose of the video
            6. Summary of main topics and insights
            
            Organize the output with clear sections for transcription, visual analysis, and summary.
            """
            
            response = self._multimodal_model.generate_content([prompt, video_file])
            
            # Clean up uploaded file
            genai.delete_file(video_file.name)
            
            if hasattr(response, 'text') and response.text:
                return f"[Video Analysis]\n{response.text}"
            else:
                return f"[Video file: {Path(video_path).name}] - Could not generate analysis"
                
        except Exception as e:
            return f"[Video file: {Path(video_path).name}] - Error processing: {str(e)}"
    
    def get_file_type(self, file_path: str) -> Tuple[str, str]:
        """
        Determine the file type and appropriate processing method.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Tuple of (file_type, mime_type)
        """
        file_path = Path(file_path)
        extension = file_path.suffix.lower()
        
        # Image extensions
        image_exts = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.svg'}
        # Audio extensions  
        audio_exts = {'.mp3', '.wav', '.aac', '.flac', '.ogg', '.m4a', '.wma'}
        # Video extensions
        video_exts = {'.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv', '.m4v'}
        
        if extension in image_exts:
            return 'image', f'image/{extension[1:]}'
        elif extension in audio_exts:
            return 'audio', f'audio/{extension[1:]}'
        elif extension in video_exts:
            return 'video', f'video/{extension[1:]}'
        else:
            return 'text', 'text/plain'
    
    def process_file(self, file_path: str) -> str:
        """
        Process any multimedia file and return text content.
        
        Args:
            file_path: Path to the file to process
            
        Returns:
            Text content extracted from the file (either BASE64 or description)
        """
        file_type, _ = self.get_file_type(file_path)
        
        # If BASE64 mode is enabled, return BASE64 encoded data
        if self._use_base64 and file_type in ['image', 'audio', 'video']:
            print(f"[DEBUG] Processing {file_type} file in BASE64 mode")
            return self.process_file_as_base64(file_path)
        
        # Otherwise use the traditional approach (Gemini analysis)
        if file_type == 'image':
            return self.process_image(file_path)
        elif file_type == 'audio':
            return self.process_audio(file_path)
        elif file_type == 'video':
            return self.process_video(file_path)
        else:
            # Handle as text file
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
            except Exception as e:
                return f"[Text file: {Path(file_path).name}] - Error reading: {str(e)}"