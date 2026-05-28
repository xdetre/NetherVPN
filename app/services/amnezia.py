import asyncio
import json
import os
import subprocess
from datetime import datetime


CONTAINER_NAME = "amnezia-awg2"
AWG_CONF_PATH = "/opt/amnezia/awg/awg0.conf"
CLIENTS_TABLE_PATH = "/opt/amnezia/awg/clientsTable"

# Параметры сервера (из awg0.conf)
SERVER_ENDPOINT = "84.22.150.68:34274"
SERVER_DNS = "1.1.1.1"
SUBNET = "10.8.1"


def _run(cmd: str) -> str:
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip()


def _get_next_ip() -> str:
    """Найти свободный IP в подсети 10.8.1.x"""
    conf = _run(f"docker exec {CONTAINER_NAME} cat {AWG_CONF_PATH}")
    used = []
    for line in conf.splitlines():
        if "AllowedIPs" in line:
            ip = line.split("=")[1].strip().split("/")[0]
            last = int(ip.split(".")[-1])
            used.append(last)
    for i in range(2, 255):
        if i not in used:
            return f"{SUBNET}.{i}"
    raise Exception("Нет свободных IP адресов")


def _generate_keys() -> tuple[str, str, str]:
    """Генерировать private, public, preshared ключи"""
    private = _run(f"docker exec {CONTAINER_NAME} awg genkey")
    public = _run(f"echo '{private}' | docker exec -i {CONTAINER_NAME} awg pubkey")
    preshared = _run(f"docker exec {CONTAINER_NAME} awg genpsk")
    return private, public, preshared


def _get_server_public_key() -> str:
    return _run(f"docker exec {CONTAINER_NAME} cat /opt/amnezia/awg/wireguard_server_public_key.key")


def _get_server_params() -> dict:
    """Получить obfuscation параметры из awg0.conf"""
    conf = _run(f"docker exec {CONTAINER_NAME} cat {AWG_CONF_PATH}")
    params = {}
    for line in conf.splitlines():
        for key in ["Jc", "Jmin", "Jmax", "S1", "S2", "S3", "S4", "H1", "H2", "H3", "H4"]:
            if line.startswith(f"{key} ="):
                params[key] = line.split("=")[1].strip()
    return params


async def create_client(user_id: int, username: str) -> str | None:
    """Создать нового WireGuard клиента, вернуть содержимое .conf файла"""
    try:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _create_client_sync, user_id, username)
    except Exception as e:
        print(f"Amnezia create_client error: {e}")
        return None


def _create_client_sync(user_id: int, username: str) -> str:
    client_name = f"user_{user_id}"
    client_ip = _get_next_ip()
    private_key, public_key, preshared_key = _generate_keys()
    server_public_key = _get_server_public_key()
    params = _get_server_params()

    # Добавить [Peer] в awg0.conf
    peer_block = f"""
[Peer]
PublicKey = {public_key}
PresharedKey = {preshared_key}
AllowedIPs = {client_ip}/32
"""
    _run(
        f"docker exec {CONTAINER_NAME} sh -c "
        f"\"echo '{peer_block}' >> {AWG_CONF_PATH}\""
    )

    # Применить конфиг без перезапуска
    _run(
        f"docker exec {CONTAINER_NAME} sh -c "
        f"\"awg set awg0 peer {public_key} preshared-key <(echo '{preshared_key}') "
        f"allowed-ips {client_ip}/32\""
    )

    # Обновить clientsTable
    table_raw = _run(f"docker exec {CONTAINER_NAME} cat {CLIENTS_TABLE_PATH}")
    try:
        table = json.loads(table_raw)
    except Exception:
        table = []

    table.append({
        "clientId": public_key,
        "userData": {
            "clientName": client_name,
            "creationDate": datetime.utcnow().strftime("%a %b %d %H:%M:%S %Y")
        }
    })

    table_json = json.dumps(table, indent=4).replace('"', '\\"')
    _run(
        f"docker exec {CONTAINER_NAME} sh -c "
        f"\"echo \\\"{table_json}\\\" > {CLIENTS_TABLE_PATH}\""
    )

    # Сформировать клиентский конфиг
    client_conf = f"""[Interface]
PrivateKey = {private_key}
Address = {client_ip}/32
DNS = {SERVER_DNS}
Jc = {params.get('Jc', '4')}
Jmin = {params.get('Jmin', '10')}
Jmax = {params.get('Jmax', '50')}
S1 = {params.get('S1', '71')}
S2 = {params.get('S2', '119')}
S3 = {params.get('S3', '21')}
S4 = {params.get('S4', '15')}
H1 = {params.get('H1', '1631419395')}
H2 = {params.get('H2', '1988717775')}
H3 = {params.get('H3', '2106666143')}
H4 = {params.get('H4', '2127911742')}

[Peer]
PublicKey = {server_public_key}
PresharedKey = {preshared_key}
Endpoint = {SERVER_ENDPOINT}
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
"""
    return client_conf


async def delete_client(public_key: str) -> bool:
    """Удалить клиента по публичному ключу"""
    try:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _delete_client_sync, public_key)
    except Exception as e:
        print(f"Amnezia delete_client error: {e}")
        return False


def _delete_client_sync(public_key: str) -> bool:
    # Удалить пира из awg0
    _run(f"docker exec {CONTAINER_NAME} awg set awg0 peer {public_key} remove")

    # Удалить из awg0.conf
    conf = _run(f"docker exec {CONTAINER_NAME} cat {AWG_CONF_PATH}")
    lines = conf.splitlines()
    new_lines = []
    skip = False
    for line in lines:
        if line.strip() == "[Peer]":
            skip = False
            peer_lines = [line]
            continue
        if skip:
            continue
        if "PublicKey" in line and public_key in line:
            skip = True
            continue
        new_lines.append(line)

    new_conf = "\n".join(new_lines)
    _run(
        f"docker exec {CONTAINER_NAME} sh -c "
        f"\"cat > {AWG_CONF_PATH} << 'EOF'\n{new_conf}\nEOF\""
    )

    # Удалить из clientsTable
    table_raw = _run(f"docker exec {CONTAINER_NAME} cat {CLIENTS_TABLE_PATH}")
    try:
        table = json.loads(table_raw)
        table = [c for c in table if c.get("clientId") != public_key]
        table_json = json.dumps(table, indent=4)
        _run(
            f"docker exec {CONTAINER_NAME} sh -c "
            f"\"echo '{table_json}' > {CLIENTS_TABLE_PATH}\""
        )
    except Exception:
        pass

    return True