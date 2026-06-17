import socket
import json
import os
import base64
import hashlib
import threading

class TCPServer:
    def __init__(self, host='0.0.0.0', port=6000, storage_dir='server_storage'):
        self.host = host
        self.port = port
        self.storage_dir = storage_dir
        
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)
            
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        print(f"[*] Servidor TCP (V2) aguardando conexões em {self.host}:{self.port}")

    def get_file_hash(self, file_path):
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def receive_full_message(self, sock):
        """Lê os dados do socket até que um JSON completo seja formado ou a conexão feche."""
        data = b""
        while True:
            part = sock.recv(65536) # 64KB por leitura
            if not part:
                return None
            data += part
            # Tentativa simples de verificar se o JSON fechou (assumindo que termina em '}')
            try:
                if data.strip().endswith(b"}"):
                    return data
            except:
                pass

    def handle_client(self, client_socket, addr):
        print(f"[*] Conexão aceita de {addr}")
        try:
            while True:
                # Usar lógica robusta para receber mensagens grandes (PDFs, etc)
                data = self.receive_full_message(client_socket)
                if not data:
                    break
                
                try:
                    request = json.loads(data.decode('utf-8'))
                    cmd = request.get("cmd")
                    
                    if cmd == "list_req":
                        files = os.listdir(self.storage_dir)
                        response = {"cmd": "list_resp", "files": files}
                        client_socket.sendall(json.dumps(response).encode('utf-8'))
                        
                    elif cmd == "put_req":
                        file_name = request.get("file")
                        received_hash = request.get("hash")
                        file_data_b64 = request.get("value")
                        
                        print(f"[*] Recebendo upload: {file_name}")
                        file_path = os.path.join(self.storage_dir, file_name)
                        file_bytes = base64.b64decode(file_data_b64)
                        
                        with open(file_path, "wb") as f:
                            f.write(file_bytes)
                        
                        calculated_hash = self.get_file_hash(file_path)
                        status = "ok" if calculated_hash == received_hash else "fail"
                        
                        if status == "fail":
                            print(f"[!] Hash inconsistente para {file_name}")
                            os.remove(file_path)
                            
                        response = {"cmd": "put_resp", "file": file_name, "status": status}
                        client_socket.sendall(json.dumps(response).encode('utf-8'))
                        
                    elif cmd == "get_req":
                        file_name = request.get("file")
                        file_path = os.path.join(self.storage_dir, file_name)
                        
                        if os.path.exists(file_path):
                            print(f"[*] Enviando download: {file_name}")
                            file_hash = self.get_file_hash(file_path)
                            with open(file_path, "rb") as f:
                                file_bytes = f.read()
                                file_data_b64 = base64.b64encode(file_bytes).decode('utf-8')
                            
                            response = {
                                "cmd": "get_resp",
                                "file": file_name,
                                "hash": file_hash,
                                "value": file_data_b64
                            }
                        else:
                            response = {"cmd": "get_resp", "file": file_name, "status": "not_found"}
                            
                        client_socket.sendall(json.dumps(response).encode('utf-8'))
                        
                except json.JSONDecodeError as e:
                    print(f"[!] Erro ao decodificar JSON: {e}")
                    break
        except Exception as e:
            print(f"[!] Erro no tratamento do cliente {addr}: {e}")
        finally:
            client_socket.close()
            print(f"[*] Conexão com {addr} encerrada.")

    def run(self):
        try:
            while True:
                client_sock, addr = self.server_socket.accept()
                client_handler = threading.Thread(target=self.handle_client, args=(client_sock, addr))
                client_handler.start()
        except KeyboardInterrupt:
            print("[*] Servidor encerrado pelo usuário.")
        finally:
            self.server_socket.close()

if __name__ == "__main__":
    server = TCPServer()
    server.run()
