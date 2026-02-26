import asyncio
import os
import logging
from ..infrastructure.database.postgres import get_all_settings, save_setting
from ..core.security import encrypt_password

logger = logging.getLogger("ConfigService")

async def get_config():
    """Get current configuration"""
    db_settings = await asyncio.to_thread(get_all_settings)
    
    return {
        "exchange_user": db_settings.get("EXCHANGE_USER", os.getenv("EXCHANGE_USER", "")),
        "exchange_server": db_settings.get("EXCHANGE_SERVER", os.getenv("EXCHANGE_SERVER", "")),
        "exchange_upn": db_settings.get("EXCHANGE_UPN", os.getenv("EXCHANGE_UPN", "")),
        "exchange_pass": "••••••••" if db_settings.get("EXCHANGE_PASS") else "",
        "ai_threads": int(db_settings.get("CPU_THREADS", os.getenv("CPU_THREADS", "4"))),
        "ai_temp": 0.1
    }

async def update_config(
    exchange_user: str,
    exchange_server: str,
    exchange_pass: str = None,
    exchange_upn: str = None,
    ai_threads: int = 4,
    ai_temp: float = 0.1
):
    """Update configuration in DB and .env"""
    try:
        # Save to database
        await asyncio.to_thread(save_setting, "EXCHANGE_USER", exchange_user)
        await asyncio.to_thread(save_setting, "EXCHANGE_SERVER", exchange_server)
        await asyncio.to_thread(save_setting, "CPU_THREADS", str(ai_threads))
        
        if exchange_upn:
            await asyncio.to_thread(save_setting, "EXCHANGE_UPN", exchange_upn)
        if exchange_pass:
            encrypted_pass = encrypt_password(exchange_pass)
            await asyncio.to_thread(save_setting, "EXCHANGE_PASS", encrypted_pass)

        # Update .env file
        env_path = "/app/.env" if os.path.exists("/app/.env") else ".env"
        
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                lines = f.readlines()
            
            new_values = {
                "EXCHANGE_USER": exchange_user,
                "EXCHANGE_SERVER": exchange_server,
                "EXCHANGE_UPN": exchange_upn or "",
                "CPU_THREADS": str(ai_threads)
            }
            if exchange_pass:
                new_values["EXCHANGE_PASS"] = exchange_pass
            
            updated_lines = []
            keys_handled = set()
            
            for line in lines:
                handled = False
                for key, val in new_values.items():
                    if line.startswith(f"{key}="):
                        updated_lines.append(f"{key}={val}\n")
                        keys_handled.add(key)
                        handled = True
                        break
                if not handled:
                    updated_lines.append(line)
            
            # Add missing keys
            for key, val in new_values.items():
                if key not in keys_handled:
                    updated_lines.append(f"{key}={val}\n")
            
            with open(env_path, "w") as f:
                f.writelines(updated_lines)

        logger.info(f"Configuration updated for user: {exchange_user}")
        return {"status": "success", "message": "Configuración guardada en Base de Datos con éxito."}
    
    except Exception as e:
        logger.error(f"Error updating config: {str(e)}")
        return {"status": "error", "message": str(e)}
