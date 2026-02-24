import re
import logging

class EmailProcessor:
    def __init__(self):
        pass

    def clean_text(self, text):
        """
        Limpia el cuerpo del correo, eliminando hilos anteriores, 
        firmas (intentando) y espacios innecesarios.
        """
        if not text:
            return ""
            
        # Intentar eliminar hilos de correos anteriores (patrones comunes)
        patterns = [
            r"From:.*",
            r"De:.*",
            r"Sent:.*",
            r"Enviado el:.*",
            r"--- Original Message ---",
            r"________________________________"
        ]
        
        cleaned = text
        for pattern in patterns:
            cleaned = re.split(pattern, cleaned, flags=re.IGNORECASE)[0]
            
        # Eliminar múltiples saltos de línea y espacios en blanco
        cleaned = re.sub(r'\n\s*\n', '\n', cleaned)
        return cleaned.strip()

    def process_incoming_email(self, email_obj):
        """
        Recibe un objeto de correo (de exchangelib) y extrae la info relevante.
        """
        try:
            raw_body = email_obj.body if hasattr(email_obj, 'body') else ""
            clean_body = self.clean_text(raw_body)
            
            return {
                "subject": email_obj.subject,
                "sender": email_obj.sender.email_address,
                "date": email_obj.datetime_received,
                "body_original": raw_body,
                "body_clean": clean_body,
                "id": getattr(email_obj, 'message_id', None)
            }
        except Exception as e:
            logging.error(f"Error procesando correo individual: {str(e)}")
            return None

if __name__ == "__main__":
    # Prueba rápida con un texto mock
    processor = EmailProcessor()
    test_text = "Hola, necesito información.\n\nDe: alberto@huayi.es\nEnviado el: lunes..."
    print(f"Original:\n{test_text}")
    print("-" * 20)
    print(f"Limpio:\n{processor.clean_text(test_text)}")
