import asyncio
import json
import logging
import os

from ..core.security import decrypt_password, encrypt_password
from ..infrastructure.database.postgres import (
    delete_mail_profile,
    get_active_mail_profile,
    get_all_settings,
    list_mail_profiles,
    save_mail_profile,
    save_setting,
    set_active_mail_profile,
)

logger = logging.getLogger("ConfigService")


def _rewrite_env_values(env_path: str, new_values: dict):
    if os.path.exists(env_path):
        with open(env_path, "r") as file_handle:
            lines = file_handle.readlines()
    else:
        lines = []

    updated_lines = []
    keys_handled = set()

    for line in lines:
        handled = False
        for key, value in new_values.items():
            if line.startswith(f"{key}="):
                updated_lines.append(f"{key}={value}\n")
                keys_handled.add(key)
                handled = True
                break
        if not handled:
            updated_lines.append(line)

    for key, value in new_values.items():
        if key not in keys_handled:
            updated_lines.append(f"{key}={value}\n")

    with open(env_path, "w") as file_handle:
        file_handle.writelines(updated_lines)


async def sync_profiles_to_env(ai_threads: int = None):
    env_path = "/app/.env" if os.path.exists("/app/.env") else ".env"
    profiles = await asyncio.to_thread(list_mail_profiles, True)
    active_profile = await asyncio.to_thread(get_active_mail_profile, True)

    serialized_profiles = []
    for profile in profiles:
        serialized_profiles.append({
            "id": profile["id"],
            "name": profile["name"],
            "email": profile["email"],
            "server": profile["server"],
            "upn": profile.get("upn") or profile["email"],
            "folder": profile.get("folder") or "INBOX",
            "password": decrypt_password(profile.get("password_encrypted") or "") if profile.get("password_encrypted") else "",
            "is_active": profile.get("is_active", False),
        })

    new_values = {
        "EXCHANGE_PROFILES_JSON": json.dumps(serialized_profiles, ensure_ascii=False),
        "EXCHANGE_ACTIVE_PROFILE_ID": active_profile.get("id", "") if active_profile else "",
    }

    if active_profile:
        new_values.update({
            "EXCHANGE_USER": active_profile.get("email", ""),
            "EXCHANGE_SERVER": active_profile.get("server", ""),
            "EXCHANGE_UPN": active_profile.get("upn", ""),
            "EXCHANGE_FOLDER": active_profile.get("folder", "INBOX"),
            "EXCHANGE_PASS": decrypt_password(active_profile.get("password_encrypted") or "") if active_profile.get("password_encrypted") else "",
        })

    if ai_threads is not None:
        new_values["CPU_THREADS"] = str(ai_threads)

    _rewrite_env_values(env_path, new_values)


async def get_config():
    """Get current configuration"""
    settings = await asyncio.to_thread(get_all_settings)
    active_profile = await asyncio.to_thread(get_active_mail_profile)
    profiles = await asyncio.to_thread(list_mail_profiles)

    return {
        "active_profile_id": active_profile.get("id") if active_profile else None,
        "profile_id": active_profile.get("id") if active_profile else None,
        "profile_name": active_profile.get("name", "") if active_profile else "",
        "exchange_user": active_profile.get("email", "") if active_profile else "",
        "exchange_server": active_profile.get("server", "") if active_profile else "",
        "exchange_upn": active_profile.get("upn", "") if active_profile else "",
        "exchange_folder": active_profile.get("folder", "INBOX") if active_profile else "INBOX",
        "exchange_pass": "••••••••" if active_profile else "",
        "profiles": profiles,
        "ai_threads": int(settings.get("CPU_THREADS", os.getenv("CPU_THREADS", "4"))),
        "ai_temp": float(settings.get("AI_TEMPERATURE", os.getenv("AI_TEMPERATURE", "0.1"))),
    }


async def update_config(
    profile_name: str,
    exchange_user: str,
    exchange_server: str,
    exchange_pass: str = None,
    exchange_upn: str = None,
    exchange_folder: str = 'INBOX',
    ai_threads: int = 4,
    ai_temp: float = 0.1,
    profile_id: str = None,
    set_active: bool = True,
):
    """Create or update the selected Exchange profile and runtime settings."""
    try:
        await asyncio.to_thread(save_setting, "CPU_THREADS", str(ai_threads))
        if ai_temp is not None:
            await asyncio.to_thread(save_setting, "AI_TEMPERATURE", str(ai_temp))

        encrypted_pass = None
        if exchange_pass:
            encrypted_pass = encrypt_password(exchange_pass)

        profile_payload = {
            "id": profile_id,
            "name": profile_name,
            "email": exchange_user,
            "server": exchange_server,
            "upn": exchange_upn or exchange_user,
            "password_encrypted": encrypted_pass,
            "folder": exchange_folder or 'INBOX',
            "is_active": set_active,
        }
        saved_profile = await asyncio.to_thread(save_mail_profile, profile_payload)
        if not saved_profile:
            return {"status": "error", "message": "No se pudo guardar el perfil Exchange."}

        if set_active:
            await asyncio.to_thread(set_active_mail_profile, saved_profile["id"])

        await sync_profiles_to_env(ai_threads)

        logger.info(f"Perfil Exchange guardado: {saved_profile['name']} ({saved_profile['email']})")
        return {
            "status": "success",
            "message": "Perfil Exchange guardado correctamente.",
            "profile": saved_profile,
        }

    except Exception as e:
        logger.error(f"Error updating config: {str(e)}")
        return {"status": "error", "message": str(e)}


async def activate_profile(profile_id: str):
    profile = await asyncio.to_thread(set_active_mail_profile, profile_id)
    if not profile:
        return {"status": "error", "message": "Perfil no encontrado."}
    await sync_profiles_to_env()
    return {"status": "success", "message": "Perfil activado correctamente.", "profile": profile}


async def remove_profile(profile_id: str):
    deleted = await asyncio.to_thread(delete_mail_profile, profile_id)
    if not deleted:
        return {"status": "error", "message": "No se pudo eliminar el perfil."}
    await sync_profiles_to_env()
    return {"status": "success", "message": "Perfil eliminado correctamente."}
