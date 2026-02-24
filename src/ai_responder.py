import os
import yaml
import requests
import logging
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

class AIResponder:
    def __init__(self):
        # Cargar configuración
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'config.yaml')
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # URL de la API del modelo (desde .env o valor por defecto)
        self.api_url = os.getenv('LLM_API_URL', 'http://llm_service:8000')
        self.generate_endpoint = f"{self.api_url}/generate"
        
        self.model_config = self.config.get('model', {})
        self.tasks_config = self.model_config.get('tasks', {})

    def generate_response(self, prompt, task='generation'):
        """
        Envía un prompt al servicio LLM y devuelve la respuesta generada.
        Permite especificar el tipo de tarea para ajustar parámetros (temp, tokens).
        """
        # Obtener parámetros específicos de la tarea o los generales del modelo
        task_params = self.tasks_config.get(task, {})
        
        payload = {
            "prompt": prompt,
            "max_tokens": task_params.get('max_tokens', self.model_config.get('max_tokens', 512)),
            "temperature": task_params.get('temperature', self.model_config.get('temperature', 0.7)),
            "top_p": task_params.get('top_p', self.model_config.get('top_p', 0.9))
        }
        
        try:
            logging.info(f"Enviando petición a LLM para tarea: {task}")
            response = requests.post(self.generate_endpoint, json=payload, timeout=300)
            response.raise_for_status()
            
            data = response.json()
            return data.get('response', '')
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Error al comunicar con el servicio LLM: {str(e)}")
            return None

    def classify_email(self, email_body):
        """
        Ejemplo de uso específico: Clasificar un correo.
        """
        # Aquí cargaríamos el prompt de clasificación desde /prompts/email_classifier.txt en el futuro
        prompt = f"Clasifica el siguiente correo y responde solo con la categoría: {email_body}"
        return self.generate_response(prompt, task='classification')

if __name__ == "__main__":
    # Prueba rápida si se ejecuta localmente
    logging.basicConfig(level=logging.INFO)
    responder = AIResponder()
    print("Probando generador de IA (requiere que el contenedor llm_service esté corriendo)...")
    res = responder.generate_response("Hola, ¿cómo puedo ayudarte hoy?", task='generation')
    print(f"Respuesta recibida: {res}")
