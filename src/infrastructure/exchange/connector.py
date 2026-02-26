import os
import yaml
import logging
from exchangelib import Credentials, Account, Configuration, DELEGATE, protocol, Message, Mailbox
from dotenv import load_dotenv

# Desactivar verificación SSL si es necesario (común en entornos internos)
protocol.BaseProtocol.HTTP_ADAPTER_CLS.verify = False

def get_account():
    load_dotenv()
    from ..database.postgres import get_setting
    from ...core.security import decrypt_password
    
    config_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'config', 'config.yaml')
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    ex_config = config['exchange']
    
    # Priorizar valores de Base de Datos, fallback a .env
    email = get_setting('EXCHANGE_USER', os.getenv('EXCHANGE_USER'))
    raw_pass = get_setting('EXCHANGE_PASS', os.getenv('EXCHANGE_PASS'))
    password = decrypt_password(raw_pass)
    server = get_setting('EXCHANGE_SERVER', ex_config.get('server'))
    upn = get_setting('EXCHANGE_UPN', os.getenv('EXCHANGE_UPN')) or email
    
    credentials = Credentials(username=upn, password=password)
    config_obj = Configuration(server=server, credentials=credentials)
    
    return Account(
        primary_smtp_address=email, 
        config=config_obj, 
        autodiscover=False, 
        access_type=DELEGATE
    )

def test_connection():
    try:
        account = get_account()
        print(f"--- Probando conexión a Exchange ---")
        print(f"✅ ¡Conexión exitosa!")
        print(f"Bandeja de entrada: {account.inbox.name}")
        return True
    except Exception as e:
        print(f"❌ Error de conexión: {str(e)}")
        return False

def get_paginated_emails(offset=0, limit=10):
    """
    Recupera correos de la bandeja de entrada con paginación.
    """
    try:
        account = get_account()
        # Solo pedimos los campos necesarios para la lista, evitando el 'body' que es lo más pesado
        query = account.inbox.all().only(
            'subject', 'sender', 'datetime_received', 'is_read'
        ).order_by('-datetime_received')
        
        # El conteo lo hacemos sobre el query optimizado
        total_count = query.count()
        emails = query[offset:offset+limit]
        
        results = []
        for item in emails:
            results.append({
                "id": str(item.id) if item.id else str(item.message_id),
                "subject": item.subject,
                "sender": item.sender.email_address if item.sender else "Sistema",
                "date": item.datetime_received.strftime("%Y-%m-%d %H:%M:%S"),
                "is_read": item.is_read,
                "body_preview": "" # Ya no lo cargamos aquí para ganar velocidad
            })
        return {"emails": results, "total": total_count}
    except Exception as e:
        print(f"Error recuperando emails paginados: {str(e)}")
        return {"emails": [], "total": 0}

def clean_html(html_content):
    if not html_content:
        return ""
    import re
    # Asegurar que es string
    text = str(html_content)
    # Eliminar etiquetas script y style
    text = re.sub(r'<(script|style).*?>.*?</\1>', '', text, flags=re.DOTALL | re.IGNORECASE)
    # Reemplazar <br> y </p> con saltos de línea para mantener estructura
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</p>', '\n', text, flags=re.IGNORECASE)
    # Eliminar todas las etiquetas restantes
    text = re.sub(r'<.*?>', '', text)
    # Decodificar entidades comunes
    text = text.replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
    
    cleaned = text.strip()
    # Si después de limpiar no queda nada pero el original tenía contenido, devolvemos el original truncado o similar
    if not cleaned and len(str(html_content)) > 10:
        return str(html_content)[:1000] # Fallback de seguridad
    return cleaned

def get_email_details(item_id):
    """
    Obtiene el cuerpo completo de un correo específico.
    """
    try:
        account = get_account()
        item = account.inbox.get(id=item_id)
        
        # Intentamos obtener el cuerpo de texto, si no, limpiamos el HTML
        body_content = item.text_body if item.text_body else clean_html(item.body)
        
        return {
            "id": str(item.id),
            "subject": item.subject,
            "sender": item.sender.email_address if item.sender else "Sistema",
            "body": body_content,
            "date": item.datetime_received.strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception as e:
        print(f"Error obteniendo detalle: {str(e)}")
        return None

def save_draft(item_id, body_response):
    """
    Crea una respuesta en borradores vinculada al correo original.
    """
    try:
        account = get_account()
        item = account.inbox.get(id=item_id)
        # Creamos una respuesta pero en lugar de .send(), usamos .save() en la carpeta Drafts
        reply = item.create_reply(
            subject=f"RE: {item.subject}",
            body=body_response
        )
        reply.save(account.drafts)
        return True
    except Exception as e:
        print(f"Error guardando borrador: {str(e)}")
        return False

def send_email(to_email, subject, body, item_id=None):
    """
    Envía un nuevo correo o una respuesta.
    """
    try:
        account = get_account()
        if item_id:
            # Es una respuesta (simplificado, en producción buscaríamos el item original)
            item = account.inbox.get(id=item_id)
            item.reply(
                subject=f"RE: {item.subject}",
                body=body
            )
        else:
            # Nuevo correo
            m = Message(
                account=account,
                folder=account.sent,
                subject=subject,
                body=body,
                to_recipients=[Mailbox(email_address=to_email)]
            )
            m.send()
        return True
    except Exception as e:
        print(f"Error enviando email: {str(e)}")
        return False

def mark_as_read(item_id, read=True):
    """
    Marca un correo como leído o no leído.
    """
    try:
        account = get_account()
        item = account.inbox.get(id=item_id)
        item.is_read = read
        item.save(update_fields=['is_read'])
        return True
    except Exception as e:
        print(f"Error marcando como leído: {str(e)}")
        return False

def delete_email(item_id):
    """
    Mueve un correo a la papelera.
    """
    try:
        account = get_account()
        item = account.inbox.get(id=item_id)
        item.move_to_trash()
        return True
    except Exception as e:
        print(f"Error eliminando email: {str(e)}")
        return False

if __name__ == "__main__":
    test_connection()
