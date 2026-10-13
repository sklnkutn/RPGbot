# debug/mode_local.py

def get_local_ollama_models():
    """Возвращает шаблонный список моделей для Ollama"""
    return {
        "models": [
            {"name": "llama3:8b"},
            {"name": "mistral:7b"},
            {"name": "gemma2:9b"}
        ]
    }

def get_local_comfy_models():
    """Возвращает шаблонный список моделей чекпоинтов для ComfyUI"""
    return [
        "WAI.safetensors",
        "nova_furry.safetensors",
        "illustmix.safetensors"
    ]