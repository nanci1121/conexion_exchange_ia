import asyncio
import logging
import os
import sys

# Asegurar que el directorio 'src' esté en el path para las importaciones
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from .exchange_connector import test_connection

logger = logging.getLogger("WorkflowEngine")

def main_loop(state_ref):
    """
    Loop principal de procesamiento.
    Recibe una referencia al estado global para actualizar el dashboard.
    """
    import time
    state_ref["status"] = "Conectando a Exchange..."
    logger.info("Iniciando el motor de flujo de trabajo de Email AI...")
    
    # Intentar una conexión inicial de prueba
    connection_ok = test_connection()
    
    if connection_ok:
        logger.info("Conexión inicial exitosa.")
        state_ref["exchange_connected"] = True
        state_ref["status"] = "En espera (Polling)"
    else:
        logger.warning("No se pudo establecer la conexión inicial. Revisa tu archivo .env")
        state_ref["exchange_connected"] = False
        state_ref["status"] = "Error de Conexión"
        state_ref["last_error"] = "No se pudo conectar a Exchange"

    # Loop principal
    processed_ids = set()
    from .ai_responder import AIResponder
    ai = AIResponder()

    try:
        while True:
            if state_ref["exchange_connected"]:
                state_ref["status"] = "Buscando nuevos correos..."
                from .exchange_connector import get_latest_emails
                
                # Obtener correos sin leer (ahora necesitamos el cuerpo completo o más largo)
                nuevos_correos = get_latest_emails(count=5)
                
                for email in nuevos_correos:
                    e_id = email["id"]
                    if e_id not in processed_ids:
                        state_ref["status"] = f"IA pensando respuesta para: {email['subject'][:20]}..."
                        logger.info(f"Procesando con IA: {email['subject']}")
                        
                        # Crear prompt limpio para la IA (las instrucciones de rol ya están en el llm_service)
                        prompt = f"Correo recibido de {email['sender']}:\n{email['body']}"
                        
                        ai_response = ai.generate_response(prompt, task='generation')
                        
                        if ai_response:
                            email["ai_response"] = ai_response
                            email["status"] = "PROCESADO"
                            processed_ids.add(e_id)
                            state_ref["emails_processed"] += 1
                        else:
                            email["status"] = "ERROR_IA"

                # Actualizar estado global para el dashboard
                state_ref["emails"] = nuevos_correos
                state_ref["status"] = "En espera (Polling)"
                # logger.info(f"Ciclo completado. {len(nuevos_correos)} correos detectados.")
            
            time.sleep(30) # Reducimos a 30 segundos para que sea más dinámico
    except Exception as e:
        logger.error(f"Error inesperado en el loop principal: {str(e)}")
        state_ref["status"] = "Fallo Crítico"
        state_ref["last_error"] = str(e)

if __name__ == "__main__":
    # Si se ejecuta solo, iniciarlo manualmente
    main_loop({})
