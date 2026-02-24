import os
import yaml
import logging
from exchangelib import Credentials, Account, Configuration, DELEGATE, protocol
from dotenv import load_dotenv

# Desactivar verificación SSL si es necesario (común en entornos internos)
protocol.BaseProtocol.HTTP_ADAPTER_CLS.verify = False

def test_connection():
    # Cargar variables de entorno y configuración
    load_dotenv()
    
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'config.yaml')
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    ex_config = config['exchange']
    
    # Obtener credenciales del .env
    email = os.getenv('EXCHANGE_USER')
    password = os.getenv('EXCHANGE_PASS')
    upn = os.getenv('EXCHANGE_UPN') or email # Si no hay UPN, usamos el email como usuario
    
    print(f"--- Probando conexión a Exchange ---")
    print(f"Servidor: {ex_config['server']} ({ex_config.get('ip', 'N/A')})")
    print(f"Email Principal: {email}")
    print(f"Usuario Autenticación (UPN): {upn}")
    
    try:
        # Usamos el UPN para la autenticación y el email para identificar la cuenta
        credentials = Credentials(username=upn, password=password)
        config_obj = Configuration(server=ex_config['server'], credentials=credentials)
        
        # Intentar conectar
        account = Account(
            primary_smtp_address=email, 
            config=config_obj, 
            autodiscover=False, 
            access_type=DELEGATE
        )
        
        print("\n✅ ¡Conexión exitosa!")
        print(f"Bandeja de entrada: {account.inbox.name}")
        print(f"Mensajes totales: {account.inbox.total_count}")
        print(f"Mensajes sin leer: {account.inbox.unread_count}")
        
        return True
    except Exception as e:
        print(f"\n❌ Error de conexión: {str(e)}")
        print("\nPosibles causas:")
        print("1. La IP 10.192.92.24 no es accesible desde donde corre el script.")
        print("2. El servidor requiere una versión de Exchange específica (actualmente configurado como Exchange2019).")
        print("3. El firewall bloquea el puerto 443 (HTTPS).")
        return False

if __name__ == "__main__":
    test_connection()
