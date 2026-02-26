import os
import sys
import pytest

# Añadir el directorio raíz al path para poder importar desde src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.infrastructure.exchange.connector import test_connection

def test_exchange_connection():
    """
    Prueba básica de conectividad con el servidor Exchange definido en config.yaml
    usando las credenciales del archivo .env.
    """
    print("\nIniciando test de conexión a Exchange...")
    result = test_connection()
    assert result is True, "La conexión a Exchange ha fallado. Revisa los logs arriba."

if __name__ == "__main__":
    # Si se ejecuta manualmente
    pytest.main([__file__])
