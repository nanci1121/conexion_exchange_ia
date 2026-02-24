import os
import yaml
import logging
from exchangelib import Credentials, Account, Configuration, DELEGATE, protocol
from dotenv import load_dotenv

# Desactivar verificación SSL si es necesario (común en entornos internos)
protocol.BaseProtocol.HTTP_ADAPTER_CLS.verify = False

def get_account():
    load_dotenv()
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'config.yaml')
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    ex_config = config['exchange']
    email = os.getenv('EXCHANGE_USER')
    password = os.getenv('EXCHANGE_PASS')
    upn = os.getenv('EXCHANGE_UPN') or email
    
    credentials = Credentials(username=upn, password=password)
    config_obj = Configuration(server=ex_config['server'], credentials=credentials)
    
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

def get_latest_emails(count=10):
    """
    Recupera los últimos correos sin leer.
    """
    try:
        account = get_account()
        # Filtrar por no leídos y ordenar por fecha
        emails = account.inbox.filter(is_read=False).order_by('-datetime_received')[:count]
        
        results = []
        for item in emails:
            results.append({
                "id": str(item.message_id),
                "subject": item.subject,
                "sender": item.sender.email_address,
                "date": item.datetime_received.strftime("%Y-%m-%d %H:%M:%S"),
                "body": item.body[:1000] + "..." if item.body else ""
            })
        return results
    except Exception as e:
        print(f"Error recuperando emails: {str(e)}")
        return []

if __name__ == "__main__":
    test_connection()
