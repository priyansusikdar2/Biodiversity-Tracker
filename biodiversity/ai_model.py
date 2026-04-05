"""
🌲 Forest Biodiversity AI Detector (ULTIMATE VERSION)
Gemini 2.5 Image Model + .env + Robust + Production Ready
"""

import os
import json
import re
import time
import logging
import traceback
from pathlib import Path
from typing import Dict, Any
from django.conf import settings
from PIL import Image
import tempfile

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

logger = logging.getLogger(__name__)


class DynamicSpeciesDetector:
    """
    Ultimate Species Detector using Google Gemini 2.5 Flash
    Production-ready with fallback mechanisms
    """

    def __init__(self):
        self.api_key = getattr(settings, "GEMINI_API_KEY", None)
        self.model = None
        self.model_name = "mock"
        self.use_mock = True

        print("\n" + "="*60)
        print("[INIT] AI Detector Starting...")
        print("="*60)
        print(f"[INFO] Gemini Library Available: {GEMINI_AVAILABLE}")
        print(f"[INFO] API Key Loaded: {bool(self.api_key)}")

        if not GEMINI_AVAILABLE:
            print("[ERROR] Gemini library not installed. Run: pip install google-generativeai")
            return

        if not self.api_key:
            print("[ERROR] API Key missing in .env file")
            return

        try:
            genai.configure(api_key=self.api_key)

            # ✅ BEST models for IMAGE detection in order of preference
            models = [
                "gemini-2.5-flash",                    # 🔥 Latest Gemini 2.5 Flash
                "gemini-2.0-flash-exp",                # 🚀 Gemini 2.0 Flash Experimental
                "gemini-1.5-flash",                    # ✅ Stable fallback
                "gemini-pro-vision",                   # Legacy vision model
            ]

            for m in models:
                try:
                    print(f"[TRY] Loading model: {m}")
                    model = genai.GenerativeModel(m)

                    # Quick test to verify model works
                    test_response = model.generate_content("Test connection")
                    if test_response:
                        self.model = model
                        self.model_name = m
                        self.use_mock = False
                        print(f"[SUCCESS] ✅ Using model: {m}")
                        break

                except Exception as e:
                    error_msg = str(e)[:60]
                    print(f"[FAIL] {m}: {error_msg}")
                    continue

            if self.use_mock:
                print("[WARNING] ⚠️ All models failed → using MOCK detection")
                print("[INFO] You can still save observations manually")

        except Exception as e:
            print("[ERROR INIT]:", e)
            traceback.print_exc()

        print("="*60 + "\n")

    # ================= PREPROCESS IMAGE =================
    def preprocess(self, path):
        """Preprocess image for optimal API response"""
        try:
            img = Image.open(path).convert("RGB")
            img.thumbnail((1024, 1024))  # Resize for faster processing

            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            img.save(tmp.name, "JPEG", quality=85, optimize=True)
            return tmp.name

        except Exception as e:
            print(f"[ERROR PREPROCESS]: {e}")
            return path

    # ================= MOCK DETECTION (Fallback) =================
    def mock(self, path):
        """Fallback detection when Gemini is unavailable"""
        try:
            filename = Path(path).stem
            common_name = filename.replace('_', ' ').replace('-', ' ').title()
            
            # Try to guess category from filename
            animal_keywords = ['lion', 'tiger', 'elephant', 'deer', 'bird', 'snake', 'monkey', 'fox', 'wolf', 'bear', 'cat', 'dog']
            plant_keywords = ['tree', 'flower', 'plant', 'leaf', 'fern', 'moss', 'grass']
            
            category = 'OT'
            for word in animal_keywords:
                if word in filename.lower():
                    category = 'FA'
                    break
            for word in plant_keywords:
                if word in filename.lower():
                    category = 'FL'
                    break

            return {
                "success": True,
                "common_name": common_name if len(common_name) > 3 else "Unknown Species",
                "scientific_name": common_name.lower().replace(' ', '_') if len(common_name) > 3 else "unknown_species",
                "category": category,
                "confidence": 0.5,
                "description": "Fallback detection (AI model unavailable). Please verify species manually.",
                "provider": "mock",
                "model": self.model_name,
                "message": "Using mock detection. Configure valid GEMINI_API_KEY for real AI detection."
            }
        except Exception as e:
            print(f"[ERROR MOCK]: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Mock analysis failed"
            }

    # ================= GEMINI ANALYSIS =================
    def analyze(self, path):
        """Analyze image using Gemini API"""
        processed = self.preprocess(path)

        try:
            img = Image.open(processed)
            print(f"[INFO] Image size: {img.size}, Mode: {img.mode}")

            prompt = """You are an expert wildlife biologist. Identify the species in this image.

Return ONLY valid JSON in this exact format, no other text:

{
  "common_name": "common name of the species",
  "scientific_name": "genus and species",
  "category": "FA for animal, FL for plant, or OT for other",
  "confidence": 0.95,
  "description": "one sentence description of the species"
}

Rules:
- Give the best possible identification
- Only use "Unknown" if absolutely impossible to identify
- Confidence should reflect how certain you are (0.0 to 1.0)
- No extra text outside JSON
"""

            # 🔁 Retry logic for robustness
            response_text = None
            for attempt in range(2):
                try:
                    print(f"[INFO] Sending request to Gemini (attempt {attempt + 1})...")
                    response = self.model.generate_content([prompt, img])
                    response_text = response.text.strip()
                    print(f"[INFO] Received response ({len(response_text)} chars)")
                    break
                except Exception as e:
                    print(f"[RETRY {attempt + 1}] Error: {e}")
                    time.sleep(1)

            if not response_text:
                raise Exception("No response from Gemini API")

            print(f"\n[DEBUG RAW RESPONSE]:\n{response_text[:500]}...")

            # 🧠 Extract JSON safely using regex
            match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if not match:
                raise Exception("No JSON found in response")

            data = json.loads(match.group())

            # Normalize and validate confidence
            confidence = data.get("confidence", 0)
            if isinstance(confidence, str):
                try:
                    confidence = float(confidence)
                except:
                    confidence = 0
            data["confidence"] = max(0.0, min(float(confidence), 1.0))

            # Validate category
            category = data.get("category", "OT").upper()
            if category not in ["FA", "FL", "OT"]:
                category = "OT"
            data["category"] = category

            # Add metadata
            data.update({
                "success": True,
                "provider": "google_gemini",
                "model": self.model_name
            })

            # ⚠️ Smart fallback for low confidence
            if data["confidence"] < 0.35:
                print(f"[WARNING] Low confidence ({data['confidence']:.2f}) - using fallback")
                fallback = self.mock(path)
                fallback["ai_attempt"] = data
                fallback["message"] = "Low confidence detection - fallback used"
                return fallback

            print(f"[SUCCESS] Identified: {data.get('common_name', 'Unknown')} ({data['confidence']*100:.0f}% confidence)")
            return data

        except json.JSONDecodeError as e:
            print(f"[ERROR JSON PARSE]: {e}")
            print(f"Failed text: {response_text[:200] if response_text else 'N/A'}")
            return self.mock(path)

        except Exception as e:
            print(f"[ERROR ANALYSIS]: {e}")
            traceback.print_exc()
            return self.mock(path)

        finally:
            if processed != path and os.path.exists(processed):
                try:
                    os.unlink(processed)
                    print(f"[INFO] Cleaned up temp file: {processed}")
                except:
                    pass

    # ================= MAIN DETECTION METHOD =================
    def detect(self, path):
        """Main detection method - entry point for single image detection"""
        print(f"\n[INFO] Processing: {Path(path).name}")

        if not os.path.exists(path):
            return {"success": False, "error": "File not found", "message": f"File does not exist: {path}"}

        try:
            img = Image.open(path)
            img.verify()
            print(f"[INFO] Image validated successfully")
        except Exception as e:
            print(f"[ERROR] Invalid image: {e}")
            return {"success": False, "error": "Invalid image", "message": str(e)}

        # Perform detection
        if self.use_mock:
            print(f"[INFO] Using MOCK detection mode")
            result = self.mock(path)
        else:
            print(f"[INFO] Using GEMINI detection mode")
            result = self.analyze(path)

        # Add file metadata
        result.update({
            "filename": os.path.basename(path),
            "file_path": path,
            "size_kb": round(os.path.getsize(path) / 1024, 2)
        })

        print(f"[INFO] Detection complete. Success: {result.get('success', False)}")
        return result

    # ================= BATCH DETECTION =================
    def detect_batch(self, paths):
        """Detect species from multiple images"""
        results = []
        total = len(paths)
        for idx, path in enumerate(paths, 1):
            print(f"\n📸 Processing {idx}/{total}")
            result = self.detect(path)
            results.append(result)
        return results

    # ================= FOLDER DETECTION =================
    def detect_folder(self, folder_path):
        """Detect species from all images in a folder"""
        folder = Path(folder_path)
        if not folder.exists():
            return [{"error": "Folder not found", "message": f"Folder does not exist: {folder_path}"}]

        # Supported image extensions
        extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        images = []
        for ext in extensions:
            images.extend(folder.glob(f"*{ext}"))
            images.extend(folder.glob(f"*{ext.upper()}"))

        if not images:
            return [{"error": "No images found", "message": f"No images found in {folder_path}"}]

        print(f"\n📁 Found {len(images)} images in folder: {folder_path}")
        return self.detect_batch([str(img) for img in images])

    # ================= STATUS =================
    def get_status(self):
        """Get current detector status"""
        return {
            "available": not self.use_mock,
            "provider": "google_gemini" if not self.use_mock else "mock",
            "model": self.model_name,
            "api_key_loaded": bool(self.api_key),
            "gemini_library": GEMINI_AVAILABLE,
            "mode": "production" if not self.use_mock else "fallback"
        }


# ================= SINGLETON INSTANCE =================
_detector = None


def get_detector():
    """Get or create the global detector instance"""
    global _detector
    if _detector is None:
        _detector = DynamicSpeciesDetector()
    return _detector


# ================= DJANGO HELPER FUNCTIONS =================
def detect_species_from_image(image_file):
    """
    Detect species from uploaded image file (Django compatible)
    
    Args:
        image_file: InMemoryUploadedFile or file path string
    
    Returns:
        Dictionary with detection results
    """
    print("\n" + "="*60)
    print("📸 Processing Uploaded Image")
    print("="*60)

    detector = get_detector()

    # Handle different input types
    if hasattr(image_file, 'temporary_file_path'):
        # Temporary uploaded file
        path = image_file.temporary_file_path()
        print(f"[INFO] Temporary file: {path}")
        cleanup_needed = False
    elif hasattr(image_file, 'chunks'):
        # In-memory file - save temporarily
        print(f"[INFO] Processing uploaded file: {image_file.name}")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            for chunk in image_file.chunks():
                tmp.write(chunk)
            path = tmp.name
        print(f"[INFO] Saved to temp file: {path}")
        cleanup_needed = True
    else:
        # File path string
        path = str(image_file)
        print(f"[INFO] File path: {path}")
        cleanup_needed = False

    # Run detection
    result = detector.detect(path)

    # Cleanup temp file if needed
    if cleanup_needed:
        try:
            os.unlink(path)
            print(f"[INFO] Cleaned up temp file")
        except:
            pass

    return result


def detect_species_from_multiple_files(image_files):
    """
    Detect species from multiple uploaded files
    
    Args:
        image_files: List of uploaded file objects
    
    Returns:
        List of detection results
    """
    detector = get_detector()
    paths = []

    for f in image_files:
        if hasattr(f, 'temporary_file_path'):
            paths.append(f.temporary_file_path())
        else:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                for chunk in f.chunks():
                    tmp.write(chunk)
                paths.append(tmp.name)

    results = detector.detect_batch(paths)

    # Cleanup temp files
    for path in paths:
        try:
            if os.path.exists(path) and path != getattr(path, 'temporary_file_path', None):
                os.unlink(path)
        except:
            pass

    return results


def auto_scan_media_folder():
    """Auto scan media folder for images"""
    detector = get_detector()
    media_path = os.path.join(settings.MEDIA_ROOT, "observations")
    return detector.detect_folder(media_path)


def get_model_info():
    """Get information about the AI model"""
    detector = get_detector()
    status = detector.get_status()
    return {
        "available": status["available"],
        "provider": status["provider"],
        "model": status["model"],
        "api_key_loaded": status["api_key_loaded"],
        "gemini_library": status["gemini_library"],
        "mode": status["mode"]
    }


def initialize_model():
    """Initialize the AI model (for compatibility)"""
    detector = get_detector()
    return not detector.use_mock


def reset_detector():
    """Reset the detector instance (useful for testing)"""
    global _detector
    _detector = None
    print("[INFO] AI Detector has been reset")