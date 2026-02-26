import asyncio
import logging
import os
import sys
import time

# Asegurar que el directorio 'src' esté en el path para las importaciones
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from .exchange_connector import test_connection, get_paginated_emails, get_email_details
from .database import init_db, upsert_email, update_email_status, delete_email_db, get_db_connection

logger = logging.getLogger("WorkflowEngine")

def main_loop(state_ref):
    """
    Loop principal de procesamiento.
    Mantiene la base de datos local sincronizada con el Inbox de Exchange.
    """
    state_ref["status"] = "Conectando a Exchange..."
    logger.info("Iniciando el motor de flujo de trabajo de Email AI...")
    
    # Inicializar base de datos
    init_db()
    
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

    from .ai_responder import AIResponder
    ai = AIResponder()

    try:
        while True:
            if state_ref["exchange_connected"]:
                state_ref["status"] = "Sincronizando Inbox..."
                
                # 1. Obtener los correos más recientes de Exchange (Inbox)
                data = get_paginated_emails(offset=0, limit=100)
                nuevos_correos = data.get("emails", [])
                ids_en_exchange = [e["id"] for e in nuevos_correos]
                
                # 2. Asegurarnos de que todos los correos de Exchange estén en nuestra DB
                for email in nuevos_correos:
                    upsert_email(email)
                
                # 3. LIMPIEZA: Si un correo está en DB pero no en los últimos 100 de Exchange, lo borramos.
                # Esto mantiene la DB como un espejo de la bandeja de entrada actual.
                try:
                    conn = get_db_connection()
                    if conn:
                        cur = conn.cursor()
                        cur.execute("SELECT id FROM emails")
                        ids_en_db = [row[0] for row in cur.fetchall()]
                        cur.close()
                        conn.close()
                        
                        for id_db in ids_en_db:
                            if id_db not in ids_en_exchange:
                                delete_email_db(id_db)
                                logger.info(f"Correo {id_db} eliminado de la DB (Ya no está en el Inbox).")
                except Exception as e:
                    logger.error(f"Error en fase de limpieza de DB: {e}")

                # 4. Sincronización de cuerpos (para correos que solo tienen cabeceras)
                try:
                    conn = get_db_connection()
                    if conn:
                        cur = conn.cursor()
                        cur.execute("SELECT id FROM emails WHERE (body = '' OR body IS NULL) LIMIT 10")
                        missing = cur.fetchall()
                        cur.close()
                        conn.close()
                        
                        if missing:
                            for row in missing:
                                m_id = row[0]
                                d = get_email_details(m_id)
                                if d:
                                    upsert_email(d)
                except Exception as e:
                    logger.error(f"Error en fase de descarga de cuerpos: {e}")

                # Actualizar estado global para el dashboard
                state_ref["emails"] = nuevos_correos
                state_ref["status"] = "En espera (Sincronizado)"
            
            time.sleep(30) 
    except Exception as e:
        logger.error(f"Error inesperado en el loop principal: {str(e)}")
        state_ref["status"] = "Fallo Crítico"
        state_ref["last_error"] = str(e)

if __name__ == "__main__":
    main_loop({})
