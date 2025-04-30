import requests
import json
import logging

logger = logging.getLogger(__name__)

class OllamaHandler:
    def __init__(self, base_url="http://localhost:11434"):
        self.base_url = base_url

    def get_models(self):
        """Get list of installed Ollama models."""
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get('models', [])
                return [model['name'] for model in models]
            else:
                logger.error(f"Failed to get models. Status code: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error getting models: {str(e)}")
            return []

    def generate_text(self, model_name, system_prompt, input_text):
        """Generate reformatted text using selected model."""
        try:
            data = {
                "model": model_name,
                "prompt": input_text,
                "system": system_prompt,
                "stream": False
            }
            response = requests.post(f"{self.base_url}/api/generate", json=data)
            if response.status_code == 200:
                return response.json().get('response', '').strip()
            else:
                logger.error(f"Failed to generate text. Status code: {response.status_code}")
                return "Error: Failed to generate text"
        except Exception as e:
            logger.error(f"Error generating text: {str(e)}")
            return f"Error: {str(e)}" 