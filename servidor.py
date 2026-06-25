"""
AV3 - Parte 2: Servidor de Arquivos TCP com Protocolo JSON
Disciplina: Redes de Computadores I (RCA) - IFSC Câmpus Lages
Professor: Robson Costa | 2026/1
"""

import socket
import threading
import json
import hashlib
import base64
import os
import sys

SERVER_FILES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server_files")
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 5000


def ensure_server_dir():
    if not os.path.exists(SERVER_FILES_DIR):
        os.makedirs(SERVER_FILES_DIR)


def calculate_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def recv_json(conn: socket.socket) -> dict:
    """Recebe JSON delimitado por \\n."""
    buffer = b""
    while True:
        byte = conn.recv(1)
        if not byte:
            raise ConnectionError("Conexão encerrada.")
        if byte == b"\n":
            break
        buffer += byte
    return json.loads(buffer.decode("utf-8"))


def send_json(conn: socket.socket, message: dict):
    """Envia JSON terminado por \\n."""
    data = json.dumps(message, ensure_ascii=False).encode("utf-8") + b"\n"
    conn.sendall(data)


def handle_client(conn: socket.socket, addr):
    print(f"[+] Cliente conectado: {addr[0]}:{addr[1]}")
    conn.settimeout(300)  # 5 min timeout
    try:
        while True:
            try:
                request = recv_json(conn)
            except (ConnectionError, socket.timeout):
                break
            except Exception:
                break

            cmd = request.get("cmd", "")

            if cmd == "list_req":
                files = [f for f in os.listdir(SERVER_FILES_DIR)
                         if os.path.isfile(os.path.join(SERVER_FILES_DIR, f))]
                send_json(conn, {"cmd": "list_resp", "files": files})
                print(f"  LIST -> {len(files)} arquivo(s)")

            elif cmd == "put_req":
                file_name = request.get("file", "")
                hash_value = request.get("hash", "")
                file_data = base64.b64decode(request.get("value", ""))
                if calculate_sha256(file_data) == hash_value:
                    path = os.path.join(SERVER_FILES_DIR, file_name)
                    with open(path, "wb") as f:
                        f.write(file_data)
                    send_json(conn, {"cmd": "put_resp", "file": file_name, "status": "ok"})
                    print(f"  PUT OK: {file_name} ({len(file_data)} bytes)")
                else:
                    send_json(conn, {"cmd": "put_resp", "file": file_name, "status": "fail"})
                    print(f"  PUT FAIL (hash): {file_name}")

            elif cmd == "get_req":
                file_name = request.get("file", "")
                path = os.path.join(SERVER_FILES_DIR, file_name)
                if os.path.isfile(path):
                    with open(path, "rb") as f:
                        file_data = f.read()
                    send_json(conn, {
                        "cmd": "get_resp",
                        "file": file_name,
                        "hash": calculate_sha256(file_data),
                        "value": base64.b64encode(file_data).decode("utf-8")
                    })
                    print(f"  GET OK: {file_name}")
                else:
                    send_json(conn, {"cmd": "get_resp", "file": file_name, "hash": "", "value": ""})
                    print(f"  GET FAIL: {file_name} não encontrado")
    except Exception as e:
        print(f"  Erro: {e}")
    finally:
        conn.close()
        print(f"[-] Cliente desconectado: {addr[0]}:{addr[1]}")


def main():
    ensure_server_dir()
    host = DEFAULT_HOST
    port = DEFAULT_PORT
    if len(sys.argv) >= 2:
        port = int(sys.argv[1])
    if len(sys.argv) >= 3:
        host = sys.argv[2]

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen(5)

    print(f"{'='*50}")
    print(f"  SERVIDOR DE ARQUIVOS TCP - Porta {port}")
    print(f"  Diretório: {SERVER_FILES_DIR}")
    print(f"{'='*50}")
    print("  Aguardando conexões...\n")

    try:
        while True:
            conn, addr = server.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
    except KeyboardInterrupt:
        print("\nServidor encerrado.")
    finally:
        server.close()


if __name__ == "__main__":
    main()
