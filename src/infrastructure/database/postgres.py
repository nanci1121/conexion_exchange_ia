import logging
import os
import uuid
import json

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("Database")


def _normalize_profile_id(profile_id=None):
    return profile_id or get_active_profile_id() or "default"


def _build_email_row_id(profile_id, exchange_id):
    return f"{profile_id}:{exchange_id}"


def _serialize_email_row(email):
    if not email:
        return email
    if email.get('date'):
        email['date'] = email['date'].strftime("%Y-%m-%d %H:%M:%S")
    if email.get('processed_at'):
        email['processed_at'] = email['processed_at'].strftime("%Y-%m-%d %H:%M:%S")
    return email


def _get_legacy_exchange_config():
    settings = get_all_settings()
    return {
        "name": settings.get("EXCHANGE_PROFILE_NAME") or os.getenv("EXCHANGE_PROFILE_NAME", "Perfil principal"),
        "email": settings.get("EXCHANGE_USER") or os.getenv("EXCHANGE_USER", ""),
        "server": settings.get("EXCHANGE_SERVER") or os.getenv("EXCHANGE_SERVER") or os.getenv("EXCHANGE_URL", ""),
        "upn": settings.get("EXCHANGE_UPN") or os.getenv("EXCHANGE_UPN", ""),
        "password_encrypted": settings.get("EXCHANGE_PASS") or os.getenv("EXCHANGE_PASS", ""),
        "folder": settings.get("EXCHANGE_FOLDER") or os.getenv("EXCHANGE_FOLDER", "INBOX"),
    }


def _get_env_mail_profiles():
    raw = os.getenv("EXCHANGE_PROFILES_JSON", "").strip()
    active_profile_id = os.getenv("EXCHANGE_ACTIVE_PROFILE_ID", "").strip()
    if not raw:
        return [], active_profile_id

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as error:
        logger.error(f"EXCHANGE_PROFILES_JSON invalido: {error}")
        return [], active_profile_id

    if not isinstance(data, list):
        logger.error("EXCHANGE_PROFILES_JSON debe ser una lista JSON")
        return [], active_profile_id

    profiles = []
    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            continue
        email = item.get("email") or item.get("exchange_user") or ""
        server = item.get("server") or item.get("exchange_server") or item.get("url") or ""
        if not email or not server:
            continue
        profiles.append({
            "id": str(item.get("id") or f"env_profile_{index}"),
            "name": item.get("name") or f"Perfil {index}",
            "email": email,
            "server": server,
            "upn": item.get("upn") or item.get("exchange_upn") or email,
            "password": item.get("password") or item.get("exchange_pass") or item.get("exchange_password") or "",
            "folder": item.get("folder") or item.get("exchange_folder") or "INBOX",
            "is_active": bool(item.get("is_active", False)),
        })
    return profiles, active_profile_id

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
        cur.execute("""
            CREATE TABLE IF NOT EXISTS mail_profiles (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                server TEXT NOT NULL,
                upn TEXT,
                password_encrypted TEXT,
                folder TEXT DEFAULT 'INBOX',
                is_active BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            );
        """)
        # Crear tabla de correos si no existe
        cur.execute("""
            CREATE TABLE IF NOT EXISTS emails (
                id TEXT PRIMARY KEY,
                profile_id TEXT,
                exchange_id TEXT,
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
        cur.execute("ALTER TABLE emails ADD COLUMN IF NOT EXISTS profile_id TEXT")
        cur.execute("ALTER TABLE emails ADD COLUMN IF NOT EXISTS exchange_id TEXT")
        cur.execute("UPDATE emails SET profile_id = COALESCE(NULLIF(profile_id, ''), 'default') WHERE profile_id IS NULL OR profile_id = ''")
        cur.execute("UPDATE emails SET exchange_id = COALESCE(NULLIF(exchange_id, ''), id) WHERE exchange_id IS NULL OR exchange_id = ''")
        cur.execute("UPDATE emails SET id = profile_id || ':' || exchange_id WHERE id <> profile_id || ':' || exchange_id")
        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_emails_profile_exchange ON emails(profile_id, exchange_id)")
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

        ensure_default_profile()

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

def ensure_default_profile():
    conn = get_db_connection()
    if not conn:
        return None

    try:
        from ...core.security import encrypt_password

        cur = conn.cursor(cursor_factory=RealDictCursor)
        env_profiles, env_active_id = _get_env_mail_profiles()

        if env_profiles:
            selected_active_id = env_active_id or next((profile["id"] for profile in env_profiles if profile.get("is_active")), env_profiles[0]["id"])
            for profile in env_profiles:
                encrypted_password = encrypt_password(profile["password"]) if profile.get("password") else None
                cur.execute(
                    """
                    INSERT INTO mail_profiles (id, name, email, server, upn, password_encrypted, folder, is_active, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                    ON CONFLICT (id) DO UPDATE SET
                        name = EXCLUDED.name,
                        email = EXCLUDED.email,
                        server = EXCLUDED.server,
                        upn = EXCLUDED.upn,
                        password_encrypted = CASE
                            WHEN EXCLUDED.password_encrypted IS NOT NULL AND EXCLUDED.password_encrypted <> '' THEN EXCLUDED.password_encrypted
                            ELSE mail_profiles.password_encrypted
                        END,
                        folder = EXCLUDED.folder,
                        is_active = EXCLUDED.is_active,
                        updated_at = NOW()
                    """,
                    (
                        profile["id"],
                        profile["name"],
                        profile["email"],
                        profile["server"],
                        profile["upn"],
                        encrypted_password,
                        profile["folder"],
                        profile["id"] == selected_active_id,
                    )
                )

            cur.execute("UPDATE mail_profiles SET is_active = CASE WHEN id = %s THEN TRUE ELSE FALSE END", (selected_active_id,))
            cur.execute(
                "INSERT INTO settings (key, value, updated_at) VALUES (%s, %s, NOW()) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()",
                ("ACTIVE_EXCHANGE_PROFILE_ID", selected_active_id)
            )
            conn.commit()
            cur.close()
            conn.close()
            return selected_active_id

        cur.execute("SELECT COUNT(*) AS total FROM mail_profiles")
        total = cur.fetchone()['total']
        if total > 0:
            cur.execute("SELECT id FROM mail_profiles WHERE is_active = TRUE LIMIT 1")
            active = cur.fetchone()
            if active:
                cur.close()
                conn.close()
                return active['id']

        legacy = _get_legacy_exchange_config()
        if not legacy['email'] or not legacy['server']:
            cur.close()
            conn.close()
            return None

        profile_id = 'default'
        cur.execute(
            """
            INSERT INTO mail_profiles (id, name, email, server, upn, password_encrypted, folder, is_active, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE, NOW())
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                email = EXCLUDED.email,
                server = EXCLUDED.server,
                upn = EXCLUDED.upn,
                password_encrypted = CASE
                    WHEN EXCLUDED.password_encrypted <> '' THEN EXCLUDED.password_encrypted
                    ELSE mail_profiles.password_encrypted
                END,
                folder = EXCLUDED.folder,
                updated_at = NOW()
            """,
            (
                profile_id,
                legacy['name'],
                legacy['email'],
                legacy['server'],
                legacy['upn'] or legacy['email'],
                legacy['password_encrypted'],
                legacy['folder'] or 'INBOX',
            )
        )
        cur.execute("UPDATE mail_profiles SET is_active = CASE WHEN id = %s THEN TRUE ELSE FALSE END", (profile_id,))
        cur.execute(
            "INSERT INTO settings (key, value, updated_at) VALUES (%s, %s, NOW()) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()",
            ("ACTIVE_EXCHANGE_PROFILE_ID", profile_id)
        )
        conn.commit()
        cur.close()
        conn.close()
        return profile_id
    except Exception as e:
        logger.error(f"Error asegurando perfil Exchange por defecto: {e}")
        return None


def list_mail_profiles(include_secret=False):
    conn = get_db_connection()
    if not conn:
        return []

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        columns = "id, name, email, server, upn, folder, is_active, created_at, updated_at"
        if include_secret:
            columns += ", password_encrypted"
        cur.execute(
            f"""
            SELECT {columns}
            FROM mail_profiles
            ORDER BY is_active DESC, name ASC
            """
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error listando perfiles Exchange: {e}")
        return []


def get_mail_profile(profile_id, include_secret=False):
    conn = get_db_connection()
    if not conn:
        return None

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        columns = "id, name, email, server, upn, folder, is_active, created_at, updated_at"
        if include_secret:
            columns += ", password_encrypted"
        cur.execute(f"SELECT {columns} FROM mail_profiles WHERE id = %s", (profile_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"Error obteniendo perfil Exchange {profile_id}: {e}")
        return None


def get_active_profile_id():
    stored = get_setting("ACTIVE_EXCHANGE_PROFILE_ID")
    if stored:
        return stored

    conn = get_db_connection()
    if not conn:
        return None

    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM mail_profiles WHERE is_active = TRUE LIMIT 1")
        row = cur.fetchone()
        cur.close()
        conn.close()
        return row[0] if row else None
    except Exception as e:
        logger.error(f"Error obteniendo perfil Exchange activo: {e}")
        return None


def get_active_mail_profile(include_secret=False):
    profile_id = get_active_profile_id()
    if not profile_id:
        profile_id = ensure_default_profile()
    if not profile_id:
        return None
    return get_mail_profile(profile_id, include_secret=include_secret)


def save_mail_profile(profile_data):
    conn = get_db_connection()
    if not conn:
        return None

    profile_id = profile_data.get('id') or str(uuid.uuid4())
    is_active = bool(profile_data.get('is_active'))

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT COUNT(*) AS total FROM mail_profiles")
        total = cur.fetchone()['total']
        if total == 0:
            is_active = True

        cur.execute(
            """
            INSERT INTO mail_profiles (id, name, email, server, upn, password_encrypted, folder, is_active, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                email = EXCLUDED.email,
                server = EXCLUDED.server,
                upn = EXCLUDED.upn,
                password_encrypted = CASE
                    WHEN EXCLUDED.password_encrypted IS NOT NULL AND EXCLUDED.password_encrypted <> '' THEN EXCLUDED.password_encrypted
                    ELSE mail_profiles.password_encrypted
                END,
                folder = EXCLUDED.folder,
                is_active = EXCLUDED.is_active,
                updated_at = NOW()
            """,
            (
                profile_id,
                profile_data['name'],
                profile_data['email'],
                profile_data['server'],
                profile_data.get('upn') or profile_data['email'],
                profile_data.get('password_encrypted'),
                profile_data.get('folder') or 'INBOX',
                is_active,
            )
        )

        if is_active:
            cur.execute("UPDATE mail_profiles SET is_active = CASE WHEN id = %s THEN TRUE ELSE FALSE END", (profile_id,))
            cur.execute(
                "INSERT INTO settings (key, value, updated_at) VALUES (%s, %s, NOW()) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()",
                ("ACTIVE_EXCHANGE_PROFILE_ID", profile_id)
            )

        conn.commit()
        cur.close()
        conn.close()
        return get_mail_profile(profile_id)
    except Exception as e:
        logger.error(f"Error guardando perfil Exchange: {e}")
        return None


def set_active_mail_profile(profile_id):
    conn = get_db_connection()
    if not conn:
        return None

    try:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM mail_profiles WHERE id = %s", (profile_id,))
        if not cur.fetchone():
            cur.close()
            conn.close()
            return None

        cur.execute("UPDATE mail_profiles SET is_active = CASE WHEN id = %s THEN TRUE ELSE FALSE END", (profile_id,))
        cur.execute(
            "INSERT INTO settings (key, value, updated_at) VALUES (%s, %s, NOW()) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()",
            ("ACTIVE_EXCHANGE_PROFILE_ID", profile_id)
        )
        conn.commit()
        cur.close()
        conn.close()
        return get_mail_profile(profile_id)
    except Exception as e:
        logger.error(f"Error activando perfil Exchange: {e}")
        return None


def delete_mail_profile(profile_id):
    conn = get_db_connection()
    if not conn:
        return False

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT is_active FROM mail_profiles WHERE id = %s", (profile_id,))
        row = cur.fetchone()
        if not row:
            cur.close()
            conn.close()
            return False

        cur.execute("DELETE FROM emails WHERE profile_id = %s", (profile_id,))
        cur.execute("DELETE FROM mail_profiles WHERE id = %s", (profile_id,))

        if row['is_active']:
            cur.execute("SELECT id FROM mail_profiles ORDER BY updated_at DESC LIMIT 1")
            replacement = cur.fetchone()
            if replacement:
                cur.execute("UPDATE mail_profiles SET is_active = CASE WHEN id = %s THEN TRUE ELSE FALSE END", (replacement['id'],))
                cur.execute(
                    "INSERT INTO settings (key, value, updated_at) VALUES (%s, %s, NOW()) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()",
                    ("ACTIVE_EXCHANGE_PROFILE_ID", replacement['id'])
                )
            else:
                cur.execute("DELETE FROM settings WHERE key = %s", ("ACTIVE_EXCHANGE_PROFILE_ID",))

        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error eliminando perfil Exchange: {e}")
        return False


def upsert_email(email_data, profile_id=None):
    conn = get_db_connection()
    if not conn:
        return
    
    try:
        profile_id = _normalize_profile_id(profile_id)
        exchange_id = email_data.get('exchange_id') or email_data['id']
        row_id = _build_email_row_id(profile_id, exchange_id)

        # Extraer y limpiar body si es necesario
        new_body = email_data.get('body', '')
        if '<' in new_body and '>' in new_body:
            new_body = clean_html(new_body)

        cur = conn.cursor()
        # Usamos COALESCE y NULLIF para no machacar un cuerpo existente si el nuevo viene vacío
        cur.execute("""
            INSERT INTO emails (id, profile_id, exchange_id, subject, sender, body, date, is_read)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (profile_id, exchange_id) DO UPDATE SET
                id = EXCLUDED.id,
                profile_id = EXCLUDED.profile_id,
                exchange_id = EXCLUDED.exchange_id,
                subject = EXCLUDED.subject,
                sender = EXCLUDED.sender,
                body = CASE 
                    WHEN EXCLUDED.body <> '' THEN EXCLUDED.body 
                    ELSE emails.body 
                END,
                date = EXCLUDED.date,
                is_read = EXCLUDED.is_read;
        """, (
            row_id,
            profile_id,
            exchange_id,
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

def reset_emails_table(profile_id=None):
    """Borra todos los correos de la base de datos para forzar una resincronización limpia."""
    conn = get_db_connection()
    if not conn: return
    try:
        profile_id = _normalize_profile_id(profile_id)
        cur = conn.cursor()
        cur.execute("DELETE FROM emails WHERE profile_id = %s;", (profile_id,))
        conn.commit()
        cur.close()
        conn.close()
        logger.info(f"Tabla de correos vaciada para perfil {profile_id}.")
    except Exception as e:
        logger.error(f"Error en reset_emails_table: {e}")

def get_emails_from_db(offset=0, limit=10, profile_id=None):
    conn = get_db_connection()
    if not conn:
        return {"emails": [], "total": 0}
    
    try:
        profile_id = _normalize_profile_id(profile_id)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        # Obtener emails
        cur.execute(
            "SELECT * FROM emails WHERE profile_id = %s ORDER BY date DESC LIMIT %s OFFSET %s",
            (profile_id, limit, offset)
        )
        emails = cur.fetchall()
        
        # Obtener total
        cur.execute("SELECT COUNT(*) as total FROM emails WHERE profile_id = %s", (profile_id,))
        res = cur.fetchone()
        total = res['total'] if res else 0
        
        cur.close()
        conn.close()
        
        for email in emails:
            _serialize_email_row(email)
        
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

def get_email_detail_db(email_id, profile_id=None):
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        if profile_id:
            cur.execute("SELECT * FROM emails WHERE id = %s AND profile_id = %s", (email_id, profile_id))
        else:
            cur.execute("SELECT * FROM emails WHERE id = %s", (email_id,))
        email = cur.fetchone()
        cur.close()
        conn.close()
        
        if email:
            _serialize_email_row(email)
        return email
    except Exception as e:
        logger.error(f"Error obteniendo detalle de DB: {e}")
        return None

def delete_email_db(email_id, profile_id=None):
    conn = get_db_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        if profile_id:
            cur.execute("DELETE FROM emails WHERE id = %s AND profile_id = %s", (email_id, profile_id))
        else:
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


def get_profile_email_map(profile_id=None):
    conn = get_db_connection()
    if not conn:
        return []

    try:
        profile_id = _normalize_profile_id(profile_id)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id, exchange_id FROM emails WHERE profile_id = %s", (profile_id,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error obteniendo ids de correos para perfil {profile_id}: {e}")
        return []


def get_emails_missing_body(profile_id=None, limit=50):
    conn = get_db_connection()
    if not conn:
        return []

    try:
        profile_id = _normalize_profile_id(profile_id)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            "SELECT id, exchange_id FROM emails WHERE profile_id = %s AND (body = '' OR body IS NULL) LIMIT %s",
            (profile_id, limit)
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error obteniendo correos sin cuerpo para perfil {profile_id}: {e}")
        return []
