import logging
import os

import yaml
from dotenv import load_dotenv
from exchangelib import Account, Configuration, Credentials, DELEGATE, Mailbox, Message, protocol

# Desactivar verificación SSL si es necesario (común en entornos internos)
protocol.BaseProtocol.HTTP_ADAPTER_CLS.verify = False

logger = logging.getLogger("ExchangeConnector")


def get_profile_config(profile_id=None):
    load_dotenv()
    from ..database.postgres import get_active_mail_profile, get_mail_profile

    profile = get_mail_profile(profile_id, include_secret=True) if profile_id else get_active_mail_profile(include_secret=True)
    if not profile:
        return None

    config_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'config', 'config.yaml')
    with open(config_path, 'r') as file_handle:
        config = yaml.safe_load(file_handle)

    exchange_config = config.get('exchange', {})
    profile['server'] = profile.get('server') or exchange_config.get('server') or os.getenv('EXCHANGE_SERVER') or os.getenv('EXCHANGE_URL')
    profile['folder'] = profile.get('folder') or os.getenv('EXCHANGE_FOLDER', 'INBOX')
    return profile


def get_mail_folder(account, folder_name=None):
    if not folder_name or folder_name.upper() == 'INBOX':
        return account.inbox

    try:
        return account.root / folder_name
    except Exception:
        logger.warning(f"No se pudo acceder a la carpeta {folder_name}. Se usara Inbox.")
        return account.inbox


def get_account(profile_id=None):
    load_dotenv()
    from ...core.security import decrypt_password

    profile = get_profile_config(profile_id)
    if not profile:
        raise ValueError("No hay un perfil Exchange activo configurado")

    email = profile['email']
    raw_password = profile.get('password_encrypted') or os.getenv('EXCHANGE_PASS') or os.getenv('EXCHANGE_PASSWORD')
    password = decrypt_password(raw_password)
    server = profile.get('server')
    upn = profile.get('upn') or email

    if not email or not server or not password:
        raise ValueError("El perfil Exchange activo esta incompleto")

    credentials = Credentials(username=upn, password=password)
    config_obj = Configuration(server=server, credentials=credentials)

    return Account(
        primary_smtp_address=email,
        config=config_obj,
        autodiscover=False,
        access_type=DELEGATE
    )


def test_connection(profile_id=None):
    try:
        profile = get_profile_config(profile_id)
        account = get_account(profile_id)
        folder = get_mail_folder(account, profile.get('folder'))
        print("--- Probando conexión a Exchange ---")
        print("✅ ¡Conexión exitosa!")
        print(f"Bandeja de entrada: {folder.name}")
        return True
    except Exception as error:
        print(f"❌ Error de conexión: {str(error)}")
        return False


def get_paginated_emails(offset=0, limit=10, profile_id=None):
    """Recupera correos de la bandeja configurada con paginación."""
    try:
        profile = get_profile_config(profile_id)
        account = get_account(profile_id)
        folder = get_mail_folder(account, profile.get('folder'))
        query = folder.all().only(
            'subject', 'sender', 'datetime_received', 'is_read'
        ).order_by('-datetime_received')

        total_count = query.count()
        emails = query[offset:offset + limit]

        results = []
        for item in emails:
            exchange_id = str(item.id) if item.id else str(item.message_id)
            results.append({
                'id': exchange_id,
                'exchange_id': exchange_id,
                'subject': item.subject,
                'sender': item.sender.email_address if item.sender else 'Sistema',
                'date': item.datetime_received.strftime("%Y-%m-%d %H:%M:%S"),
                'is_read': item.is_read,
                'body_preview': ''
            })
        return {'emails': results, 'total': total_count}
    except Exception as error:
        print(f"Error recuperando emails paginados: {str(error)}")
        return {'emails': [], 'total': 0}


def clean_html(html_content):
    if not html_content:
        return ''

    import re

    text = str(html_content)
    text = re.sub(r'<(script|style).*?>.*?</\1>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</p>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<.*?>', '', text)
    text = text.replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')

    cleaned = text.strip()
    if not cleaned and len(str(html_content)) > 10:
        return str(html_content)[:1000]
    return cleaned


def get_email_details(item_id, profile_id=None):
    """Obtiene el cuerpo completo de un correo específico."""
    try:
        profile = get_profile_config(profile_id)
        account = get_account(profile_id)
        folder = get_mail_folder(account, profile.get('folder'))
        item = folder.get(id=item_id)
        body_content = item.text_body if item.text_body else clean_html(item.body)

        return {
            'id': str(item.id),
            'exchange_id': str(item.id),
            'subject': item.subject,
            'sender': item.sender.email_address if item.sender else 'Sistema',
            'body': body_content,
            'date': item.datetime_received.strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception as error:
        print(f"Error obteniendo detalle: {str(error)}")
        return None


def save_draft(item_id, body_response, profile_id=None):
    """Crea una respuesta en borradores vinculada al correo original."""
    try:
        profile = get_profile_config(profile_id)
        account = get_account(profile_id)
        folder = get_mail_folder(account, profile.get('folder'))
        item = folder.get(id=item_id)
        reply = item.create_reply(
            subject=f"RE: {item.subject}",
            body=body_response
        )
        reply.save(account.drafts)
        return True
    except Exception as error:
        print(f"Error guardando borrador: {str(error)}")
        return False


def send_email(to_email, subject, body, item_id=None, profile_id=None):
    """Envía un nuevo correo o una respuesta."""
    try:
        profile = get_profile_config(profile_id)
        account = get_account(profile_id)
        if item_id:
            folder = get_mail_folder(account, profile.get('folder'))
            item = folder.get(id=item_id)
            item.reply(
                subject=f"RE: {item.subject}",
                body=body
            )
        else:
            message = Message(
                account=account,
                folder=account.sent,
                subject=subject,
                body=body,
                to_recipients=[Mailbox(email_address=to_email)]
            )
            message.send()
        return True
    except Exception as error:
        print(f"Error enviando email: {str(error)}")
        return False


def mark_as_read(item_id, read=True, profile_id=None):
    """Marca un correo como leído o no leído."""
    try:
        profile = get_profile_config(profile_id)
        account = get_account(profile_id)
        folder = get_mail_folder(account, profile.get('folder'))
        item = folder.get(id=item_id)
        item.is_read = read
        item.save(update_fields=['is_read'])
        return True
    except Exception as error:
        print(f"Error marcando como leído: {str(error)}")
        return False


def delete_email(item_id, profile_id=None):
    """Mueve un correo a la papelera."""
    try:
        profile = get_profile_config(profile_id)
        account = get_account(profile_id)
        folder = get_mail_folder(account, profile.get('folder'))
        item = folder.get(id=item_id)
        item.move_to_trash()
        return True
    except Exception as error:
        print(f"Error eliminando email: {str(error)}")
        return False

if __name__ == "__main__":
    test_connection()
