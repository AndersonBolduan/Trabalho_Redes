"""
=============================================================================
AV3 - Parte 2: Servidor de Arquivos TCP com Protocolo JSON
=============================================================================
Disciplina: Redes de Computadores I (RCA)
Curso: Ciência da Computação - IFSC Câmpus Lages
Professor: Robson Costa
Ano/Semestre: 2026/1

Descrição:
    Servidor de arquivos similar ao FTP, porém utilizando protocolo próprio
    baseado em JSON sobre TCP. O servidor opera no modelo de FTP anônimo
    (sem autenticação de usuários) e suporta os comandos:
    - LIST_REQ / LIST_RESP
    - PUT_REQ / PUT_RESP
    - GET_REQ / GET_RESP

    O hash utilizado para verificação de integridade é o SHA-256.
    Os arquivos são codificados em Base64 para transporte no payload JSON.
=============================================================================
"""

import socket
import threading
import json
import hashlib
import base64
import os
import sys

# Diretório onde os arquivos do servidor são armazenados
SERVER_FILES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server_files")

# Configurações padrão do servidor
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 5000


def ensure_server_dir():
    """Garante que o diretório de arquivos do servidor existe."""
    if not os.path.exists(SERVER_FILES_DIR):
        os.makedirs(SERVER_FILES_DIR)


def calculate_sha256(data: bytes) -> str:
    """Calcula o hash SHA-256 de um conjunto de bytes."""
    return hashlib.sha256(data).hexdigest()


def recv_json(conn: socket.socket) -> dict:
    """
    Recebe uma mensagem JSON completa do socket.
    Protocolo: os primeiros 8 bytes indicam o tamanho da mensagem JSON em bytes.
    """
    # Recebe o cabeçalho de tamanho (8 bytes)
    header = b""
    while len(header) < 8:
        chunk = conn.recv(8 - len(header))
        if not chunk:
            raise ConnectionError("Conexão encerrada pelo cliente.")
        header += chunk

    msg_length = int(header.decode("utf-8").strip())

    # Recebe a mensagem completa
    data = b""
    while len(data) < msg_length:
        chunk = conn.recv(min(4096, msg_length - len(data)))
        if not chunk:
            raise ConnectionError("Conexão encerrada pelo cliente.")
        data += chunk

    return json.loads(data.decode("utf-8"))


def send_json(conn: socket.socket, message: dict):
    """
    Envia uma mensagem JSON pelo socket.
    Protocolo: os primeiros 8 bytes indicam o tamanho da mensagem JSON em bytes.
    """
    json_data = json.dumps(message).encode("utf-8")
    header = f"{len(json_data):8d}".encode("utf-8")
    conn.sendall(header + json_data)


def handle_list_req(conn: socket.socket):
    """Processa o comando LIST_REQ e envia LIST_RESP."""
    files = os.listdir(SERVER_FILES_DIR)
    # Filtra apenas arquivos (não diretórios)
    files = [f for f in files if os.path.isfile(os.path.join(SERVER_FILES_DIR, f))]
    response = {
        "cmd": "list_resp",
        "files": files
    }
    send_json(conn, response)
    print(f"  [LIST] Enviada lista com {len(files)} arquivo(s).")


def handle_put_req(conn: socket.socket, request: dict):
    """Processa o comando PUT_REQ e envia PUT_RESP."""
    file_name = request.get("file", "")
    hash_value = request.get("hash", "")
    file_base64 = request.get("value", "")

    try:
        # Decodifica o conteúdo do arquivo
        file_data = base64.b64decode(file_base64)

        # Verifica integridade com SHA-256
        computed_hash = calculate_sha256(file_data)

        if computed_hash != hash_value:
            response = {
                "cmd": "put_resp",
                "file": file_name,
                "status": "fail"
            }
            send_json(conn, response)
            print(f"  [PUT] FALHA - Hash inconsistente para '{file_name}'.")
            return

        # Salva o arquivo no diretório do servidor
        file_path = os.path.join(SERVER_FILES_DIR, file_name)
        with open(file_path, "wb") as f:
            f.write(file_data)

        response = {
            "cmd": "put_resp",
            "file": file_name,
            "status": "ok"
        }
        send_json(conn, response)
        print(f"  [PUT] OK - Arquivo '{file_name}' salvo ({len(file_data)} bytes).")

    except Exception as e:
        response = {
            "cmd": "put_resp",
            "file": file_name,
            "status": "fail"
        }
        send_json(conn, response)
        print(f"  [PUT] FALHA - Erro ao processar '{file_name}': {e}")


def handle_get_req(conn: socket.socket, request: dict):
    """Processa o comando GET_REQ e envia GET_RESP."""
    file_name = request.get("file", "")
    file_path = os.path.join(SERVER_FILES_DIR, file_name)

    if not os.path.isfile(file_path):
        # Arquivo não encontrado - envia resposta com campos vazios
        response = {
            "cmd": "get_resp",
            "file": file_name,
            "hash": "",
            "value": ""
        }
        send_json(conn, response)
        print(f"  [GET] FALHA - Arquivo '{file_name}' não encontrado.")
        return

    try:
        with open(file_path, "rb") as f:
            file_data = f.read()

        hash_value = calculate_sha256(file_data)
        file_base64 = base64.b64encode(file_data).decode("utf-8")

        response = {
            "cmd": "get_resp",
            "file": file_name,
            "hash": hash_value,
            "value": file_base64
        }
        send_json(conn, response)
        print(f"  [GET] OK - Arquivo '{file_name}' enviado ({len(file_data)} bytes).")

    except Exception as e:
        response = {
            "cmd": "get_resp",
            "file": file_name,
            "hash": "",
            "value": ""
        }
        send_json(conn, response)
        print(f"  [GET] FALHA - Erro ao ler '{file_name}': {e}")


def handle_client(conn: socket.socket, addr: tuple):
    """Trata a conexão de um cliente."""
    print(f"\n[CONEXÃO] Cliente conectado: {addr[0]}:{addr[1]}")

    try:
        while True:
            try:
                request = recv_json(conn)
            except ConnectionError:
                break
            except Exception as e:
                print(f"  [ERRO] Erro ao receber mensagem: {e}")
                break

            cmd = request.get("cmd", "")

            if cmd == "list_req":
                handle_list_req(conn)
            elif cmd == "put_req":
                handle_put_req(conn, request)
            elif cmd == "get_req":
                handle_get_req(conn, request)
            else:
                print(f"  [ERRO] Comando desconhecido: '{cmd}'")

    except Exception as e:
        print(f"  [ERRO] Exceção no tratamento do cliente: {e}")
    finally:
        conn.close()
        print(f"[DESCONEXÃO] Cliente desconectado: {addr[0]}:{addr[1]}")


def start_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
    """Inicia o servidor TCP."""
    ensure_server_dir()

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port))
    server_socket.listen(5)

    print("=" * 60)
    print("  SERVIDOR DE ARQUIVOS TCP - AV3 Parte 2")
    print("=" * 60)
    print(f"  Endereço: {host}")
    print(f"  Porta: {port}")
    print(f"  Diretório de arquivos: {SERVER_FILES_DIR}")
    print("=" * 60)
    print("  Aguardando conexões...")
    print("-" * 60)

    try:
        while True:
            conn, addr = server_socket.accept()
            client_thread = threading.Thread(
                target=handle_client,
                args=(conn, addr),
                daemon=True
            )
            client_thread.start()
    except KeyboardInterrupt:
        print("\n\n[SERVIDOR] Encerrando servidor...")
    finally:
        server_socket.close()
        print("[SERVIDOR] Servidor encerrado.")


if __name__ == "__main__":
    host = DEFAULT_HOST
    port = DEFAULT_PORT

    # Permite configurar host e porta via argumentos de linha de comando
    if len(sys.argv) >= 2:
        port = int(sys.argv[1])
    if len(sys.argv) >= 3:
        host = sys.argv[2]

    start_server(host, port)
