from models.generation import DEFAULT_GEMINI_MODEL
from services.gemini_service import GeminiService

print("Testing model name...")
try:
    model_name = GeminiService.normalize_model_id(DEFAULT_GEMINI_MODEL)
    print(f"Model name validation successful: {model_name}")
except Exception as e:
    print(f"Model instantiation failed: {e}")
