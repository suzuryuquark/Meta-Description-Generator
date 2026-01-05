import google.generativeai as genai
import os

# Try to list models or just instantiate one
# We don't have the API key here, but we can check if the SDK accepts the name
# Or we can ask the user for the error message.
# Actually, without an API key, I can't really test the API.
# But I can check if the string is rejected locally? No, it's usually server-side.

from core_logic import GEMINI_MODEL_NAME

print("Testing model name...")
try:
    model = genai.GenerativeModel(GEMINI_MODEL_NAME)
    print(f"Model instantiation successful: {GEMINI_MODEL_NAME}")
except Exception as e:
    print(f"Model instantiation failed: {e}")
