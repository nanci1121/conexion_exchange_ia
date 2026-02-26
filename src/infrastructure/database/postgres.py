import psycopg2
from psycopg2.extras import RealDictCursor
import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("Database")

def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            database=os.getenv("DB_NAME", "knowledge_base"),
            user=os.getenv("DB_USER", "email_ai_user"),
            password=os.getenv("DB_PASS", "super_secreto"),
            port=os.getenv("DB_PORT", "5432")
        )
        return conn
    except Exception as e:
        logger.error(f"Error conectando a la base de datos: {e}")
        return None

def init_db():
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        # Habilitar extensión pgvector si no existe
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        
        # Crear tabla de ajustes si no existe
        cur.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT NOW()
            );
        """)
        # Crear tabla de correos si no existe
        cur.execute("""
            CREATE TABLE IF NOT EXISTS emails (
                id TEXT PRIMARY KEY,
                subject TEXT,
                sender TEXT,
                body TEXT,
                date TIMESTAMP,
                is_read BOOLEAN DEFAULT FALSE,
                ai_response TEXT,
                status TEXT DEFAULT 'PENDIENTE',
                processed_at TIMESTAMP
            );
        """)
        # Crear tabla de documentos de conocimiento (RAG)
        # 384 dimensiones es el estándar para el modelo all-MiniLM-L6-v2 que usaremos
        cur.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id SERIAL PRIMARY KEY,
                filename TEXT,
                content TEXT,
                embedding vector(384),
                metadata JSONB,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
        logger.info("Base de datos inicializada correctamente.")
        return True
    except Exception as e:
        logger.error(f"Error inicializando base de datos: {e}")
        return False

def clean_html(html_content):
    if not html_content:
        return ""
    import re
    # Eliminar etiquetas script y style
    clean = re.sub(r'<(script|style).*?>.*?</\1>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    # Eliminar todas las etiquetas HTML
    clean = re.sub(r'<.*?>', '', clean)
    # Decodificar entidades comunes (simplificado)
    clean = clean.replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
    return clean.strip()

def upsert_email(email_data):
    conn = get_db_connection()
    if not conn:
        return
    
    try:
        # Extraer y limpiar body si es necesario
        new_body = email_data.get('body', '')
        if '<' in new_body and '>' in new_body:
            new_body = clean_html(new_body)

        cur = conn.cursor()
        # Usamos COALESCE y NULLIF para no machacar un cuerpo existente si el nuevo viene vacío
        cur.execute("""
            INSERT INTO emails (id, subject, sender, body, date, is_read)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                subject = EXCLUDED.subject,
                sender = EXCLUDED.sender,
                body = CASE 
                    WHEN EXCLUDED.body <> '' THEN EXCLUDED.body 
                    ELSE emails.body 
                END,
                date = EXCLUDED.date,
                is_read = EXCLUDED.is_read;
        """, (
            email_data['id'],
            email_data['subject'],
            email_data['sender'],
            new_body,
            email_data['date'],
            email_data.get('is_read', False)
        ))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"Error haciendo upsert de email: {e}")

def reset_emails_table():
    """Borra todos los correos de la base de datos para forzar una resincronización limpia."""
    conn = get_db_connection()
    if not conn: return
    try:
        cur = conn.cursor()
        cur.execute("TRUNCATE TABLE emails;")
        conn.commit()
        cur.close()
        conn.close()
        logger.info("Tabla de correos vaciada (Reset).")
    except Exception as e:
        logger.error(f"Error en reset_emails_table: {e}")

def get_emails_from_db(offset=0, limit=10):
    conn = get_db_connection()
    if not conn:
        return {"emails": [], "total": 0}
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        # Obtener emails
        cur.execute("SELECT * FROM emails ORDER BY date DESC LIMIT %s OFFSET %s", (limit, offset))
        emails = cur.fetchall()
        
        # Obtener total
        cur.execute("SELECT COUNT(*) as total FROM emails")
        res = cur.fetchone()
        total = res['total'] if res else 0
        
        cur.close()
        conn.close()
        
        # Convertir objetos datetime a string para JSON
        for e in emails:
            if e['date']:
                e['date'] = e['date'].strftime("%Y-%m-%d %H:%M:%S")
            if e['processed_at']:
                e['processed_at'] = e['processed_at'].strftime("%Y-%m-%d %H:%M:%S")
        
        return {"emails": emails, "total": total}
    except Exception as e:
        logger.error(f"Error leyendo de DB: {e}")
        return {"emails": [], "total": 0}

def update_email_status(email_id, status, ai_response=None):
    conn = get_db_connection()
    if not conn:
        return
    
    try:
        cur = conn.cursor()
        if ai_response:
            cur.execute("""
                UPDATE emails 
                SET status = %s, ai_response = %s, processed_at = NOW() 
                WHERE id = %s
            """, (status, ai_response, email_id))
        else:
            cur.execute("UPDATE emails SET status = %s WHERE id = %s", (status, email_id))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"Error actualizando status en DB: {e}")

def get_email_detail_db(email_id):
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM emails WHERE id = %s", (email_id,))
        email = cur.fetchone()
        cur.close()
        conn.close()
        
        if email:
            if email['date']:
                email['date'] = email['date'].strftime("%Y-%m-%d %H:%M:%S")
        return email
    except Exception as e:
        logger.error(f"Error obteniendo detalle de DB: {e}")
        return None

def delete_email_db(email_id):
    conn = get_db_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM emails WHERE id = %s", (email_id,))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error eliminando de DB: {e}")
        return False

# --- Gestión de Ajustes ---

def save_setting(key, value):
    conn = get_db_connection()
    if not conn: return
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO settings (key, value, updated_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (key) DO UPDATE SET
                value = EXCLUDED.value,
                updated_at = EXCLUDED.updated_at;
        """, (key, str(value)))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"Error guardando ajuste {key}: {e}")

def get_setting(key, default=None):
    conn = get_db_connection()
    if not conn: return default
    try:
        cur = conn.cursor()
        cur.execute("SELECT value FROM settings WHERE key = %s", (key,))
        res = cur.fetchone()
        cur.close()
        conn.close()
        return res[0] if res else default
    except Exception as e:
        logger.error(f"Error obteniendo ajuste {key}: {e}")
        return default

def get_all_settings():
    conn = get_db_connection()
    if not conn: return {}
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT key, value FROM settings")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return {r['key']: r['value'] for r in rows}
    except Exception as e:
        logger.error(f"Error obteniendo todos los ajustes: {e}")
        return {}
