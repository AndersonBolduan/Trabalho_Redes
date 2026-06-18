import argparse
import base64
import hashlib
import json
import os
import socket
import struct
import threading

# Tamanho do cabeçalho usado antes de cada JSON.
# O cabeçalho terá 8 bytes e informará quantos bytes existem na mensagem JSON.
HEADER_SIZE = 8
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 50000
DEFAULT_STORAGE_DIR = "server_storage"
DISCOVERY_MESSAGE = "TCP_FILE_SERVER_DISCOVERY_V1"


class TCPServer:
    def __init__(self, host=DEFAULT_HOST, port=DEFAULT_PORT, storage_dir=DEFAULT_STORAGE_DIR):
        self.host = host
        self.port = port
        self.storage_dir = storage_dir
        self.running = True

        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(10)

        print("=" * 70)
        print("SERVIDOR DE ARQUIVOS TCP - PARTE 2")
        print("=" * 70)
        print(f"Servidor escutando em: {self.host}:{self.port}")
        print(f"Pasta de armazenamento: {os.path.abspath(self.storage_dir)}")
        print("\nUse, no cliente, um dos IPs abaixo como IP do servidor:")
        for ip in self.get_local_ips():
            print(f"  - {ip}:{self.port}")
        print("\nSe estiver testando no mesmo computador, use 127.0.0.1.")
        print("Se estiver testando em outro computador da mesma rede, use o IP 192.168.x.x ou 10.x.x.x mostrado acima.")
        print("=" * 70)

    def get_local_ips(self):
        ips = set()

        try:
            hostname = socket.gethostname()
            for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
                ip = info[4][0]
                if not ip.startswith("127."):
                    ips.add(ip)
        except OSError:
            pass

        try:
            temp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            temp_socket.connect(("8.8.8.8", 80))
            ip = temp_socket.getsockname()[0]
            if not ip.startswith("127."):
                ips.add(ip)
            temp_socket.close()
        except OSError:
            pass

        if not ips:
            ips.add("127.0.0.1")

        return sorted(ips)

    def get_file_hash(self, file_path):
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as file:
            for byte_block in iter(lambda: file.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def receive_exactly(self, sock, total_bytes):
        data = b""
        while len(data) < total_bytes:
            chunk = sock.recv(total_bytes - len(data))
            if not chunk:
                return None
            data += chunk
        return data

    def receive_json(self, sock):
        header = self.receive_exactly(sock, HEADER_SIZE)
        if header is None:
            return None

        message_size = struct.unpack("!Q", header)[0]
        payload = self.receive_exactly(sock, message_size)
        if payload is None:
            return None

        return json.loads(payload.decode("utf-8"))

    def send_json(self, sock, message):
        payload = json.dumps(message, ensure_ascii=False).encode("utf-8")
        header = struct.pack("!Q", len(payload))
        sock.sendall(header + payload)

    def list_files(self):
        files = []
        for file_name in os.listdir(self.storage_dir):
            file_path = os.path.join(self.storage_dir, file_name)
            if os.path.isfile(file_path):
                files.append(file_name)
        return sorted(files)

    def handle_list_request(self, client_socket):
        response = {
            "cmd": "list_resp",
            "status": "ok",
            "files": self.list_files()
        }
        self.send_json(client_socket, response)

    def handle_upload_request(self, client_socket, request):
        file_name = os.path.basename(request.get("file", ""))
        received_hash = request.get("hash", "")
        file_data_b64 = request.get("value", "")

        if not file_name or not received_hash or not file_data_b64:
            self.send_json(client_socket, {
                "cmd": "put_resp",
                "file": file_name,
                "status": "fail",
                "message": "Requisição de upload incompleta."
            })
            return

        print(f"[*] Recebendo upload: {file_name}")
        file_path = os.path.join(self.storage_dir, file_name)

        try:
            file_bytes = base64.b64decode(file_data_b64.encode("utf-8"))
            with open(file_path, "wb") as file:
                file.write(file_bytes)

            calculated_hash = self.get_file_hash(file_path)
            if calculated_hash == received_hash:
                status = "ok"
                message = "Upload concluído com sucesso."
                print(f"[OK] Upload concluído: {file_name}")
            else:
                status = "fail"
                message = "Hash inconsistente. O arquivo foi descartado."
                os.remove(file_path)
                print(f"[ERRO] Hash inconsistente em: {file_name}")

        except Exception as error:
            status = "fail"
            message = f"Erro ao salvar arquivo: {error}"
            if os.path.exists(file_path):
                os.remove(file_path)
            print(f"[ERRO] Falha no upload de {file_name}: {error}")

        response = {
            "cmd": "put_resp",
            "file": file_name,
            "status": status,
            "message": message
        }
        self.send_json(client_socket, response)

    def handle_download_request(self, client_socket, request):
        file_name = os.path.basename(request.get("file", ""))
        file_path = os.path.join(self.storage_dir, file_name)

        if not file_name or not os.path.exists(file_path) or not os.path.isfile(file_path):
            self.send_json(client_socket, {
                "cmd": "get_resp",
                "file": file_name,
                "status": "not_found",
                "message": "Arquivo não encontrado no servidor."
            })
            return

        print(f"[*] Enviando download: {file_name}")
        file_hash = self.get_file_hash(file_path)

        with open(file_path, "rb") as file:
            file_bytes = file.read()

        response = {
            "cmd": "get_resp",
            "file": file_name,
            "status": "ok",
            "hash": file_hash,
            "value": base64.b64encode(file_bytes).decode("utf-8")
        }
        self.send_json(client_socket, response)
        print(f"[OK] Download enviado: {file_name}")

    def handle_client(self, client_socket, address):
        print(f"[*] Conexão aceita de {address[0]}:{address[1]}")
        try:
            request = self.receive_json(client_socket)
            if request is None:
                return

            cmd = request.get("cmd")

            if cmd == "list_req":
                self.handle_list_request(client_socket)
            elif cmd == "put_req":
                self.handle_upload_request(client_socket, request)
            elif cmd == "get_req":
                self.handle_download_request(client_socket, request)
            else:
                self.send_json(client_socket, {
                    "cmd": "error_resp",
                    "status": "fail",
                    "message": f"Comando desconhecido: {cmd}"
                })

        except json.JSONDecodeError as error:
            print(f"[ERRO] JSON inválido recebido de {address}: {error}")
        except Exception as error:
            print(f"[ERRO] Falha ao atender {address}: {error}")
        finally:
            client_socket.close()
            print(f"[*] Conexão encerrada com {address[0]}:{address[1]}")

    def discovery_responder(self):
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            udp_socket.bind(("", self.port))
            print(f"[*] Descoberta automática ativa via UDP na porta {self.port}.")
        except OSError as error:
            print(f"[AVISO] Não foi possível ativar descoberta automática UDP: {error}")
            udp_socket.close()
            return

        while self.running:
            try:
                data, client_address = udp_socket.recvfrom(1024)
                message = data.decode("utf-8", errors="ignore")

                if message == DISCOVERY_MESSAGE:
                    response = {
                        "service": DISCOVERY_MESSAGE,
                        "tcp_port": self.port,
                        "server_ips": self.get_local_ips()
                    }
                    udp_socket.sendto(json.dumps(response).encode("utf-8"), client_address)
            except OSError:
                break
            except Exception as error:
                print(f"[AVISO] Erro na descoberta automática: {error}")

        udp_socket.close()

    def run(self):
        discovery_thread = threading.Thread(target=self.discovery_responder, daemon=True)
        discovery_thread.start()

        try:
            while True:
                client_socket, address = self.server_socket.accept()
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, address),
                    daemon=True
                )
                client_thread.start()
        except KeyboardInterrupt:
            print("\n[*] Servidor encerrado pelo usuário.")
        finally:
            self.running = False
            self.server_socket.close()


def parse_arguments():
    parser = argparse.ArgumentParser(description="Servidor de arquivos TCP - Parte 2")
    parser.add_argument("--host", default=DEFAULT_HOST, help="IP em que o servidor deve escutar. Use 0.0.0.0 para aceitar conexões da rede.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Porta TCP/UDP usada pelo servidor.")
    parser.add_argument("--storage", default=DEFAULT_STORAGE_DIR, help="Pasta onde os arquivos serão armazenados.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    server = TCPServer(host=args.host, port=args.port, storage_dir=args.storage)
    server.run()
