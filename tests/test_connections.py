import requests
import psycopg2
import sys
import time
from colorama import init, Fore, Style

# Inicializar colorama para textos coloridos en la terminal
init(autoreset=True)

def print_result(service, status, detail=""):
    if status:
        print(f"{Fore.GREEN}[OK] {Style.BRIGHT}{service}: {Style.NORMAL}{detail}")
    else:
        print(f"{Fore.RED}[ERROR] {Style.BRIGHT}{service}: {Style.NORMAL}{detail}")

def test_postgres():
    print(f"\n{Fore.CYAN}--- Testeando Base de Datos PostgreSQL ---")
    try:
        # Intenta conectar usando los datos por defecto (o debes cambiarlos si usas otros en .env)
        conn = psycopg2.connect(
            dbname="knowledge_base",
            user="email_ai_user",
            password="super_secreto",
            host="localhost",
            port="5432"
        )
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()[0]
        print_result("PostgreSQL Vectordb", True, f"Conexión exitosa. ({version.split(',')[0]})")
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print_result("PostgreSQL Vectordb", False, str(e))
        return False

def test_llm_service():
    print(f"\n{Fore.CYAN}--- Testeando Servicio LLM ---")
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "ok":
                print_result("LLM API", True, f"Modelo {data.get('model')} cargado usando {data.get('technology')}")
            else:
                print_result("LLM API", False, f"La API responde pero el status es: {data.get('status')}")
            return True
        else:
            print_result("LLM API", False, f"Error HTTP {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_result("LLM API", False, "No se pudo conectar a localhost:8000. ¿Está corriendo el contenedor?")
        return False
    except Exception as e:
        print_result("LLM API", False, str(e))
        return False

def test_email_app():
    print(f"\n{Fore.CYAN}--- Testeando Aplicación Principal ---")
    try:
        # Probaremos la ruta raíz por defecto o "/docs" si no hay raíz configurada
        response = requests.get("http://localhost:8080/", timeout=5)
        # 200 (OK) o 404 (Not Found, común si no definimos una ruta principal pero FastAPI está levantado) o docs
        if response.status_code in [200, 404]:
            print_result("Email App", True, f"Servicio web respondiendo en el puerto 8080 (HTTP {response.status_code})")
            return True
        else:
            print_result("Email App", False, f"Respondió con código no esperado HTTP {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_result("Email App", False, "No se pudo conectar a localhost:8080. ¿Está corriendo el contenedor?")
        return False
    except Exception as e:
        print_result("Email App", False, str(e))
        return False

def main():
    print(f"{Style.BRIGHT}{Fore.YELLOW}Iniciando Diagnóstico de Contenedores de IA Email...{Style.RESET_ALL}")
    
    db_ok = test_postgres()
    time.sleep(1) # Pequeña pausa
    
    llm_ok = test_llm_service()
    time.sleep(1)
    
    app_ok = test_email_app()
    
    print(f"\n{Style.BRIGHT}{Fore.YELLOW}--- Resumen Final ---{Style.RESET_ALL}")
    if db_ok and llm_ok and app_ok:
        print(f"{Fore.GREEN}¡Todos los servicios están funcionando y respondiendo correctamente!")
        sys.exit(0)
    else:
        print(f"{Fore.RED}Se detectaron problemas en algunos servicios. Revisa los logs de arriba.")
        sys.exit(1)

if __name__ == "__main__":
    main()
