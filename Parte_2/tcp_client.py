import base64
import hashlib
import json
import os
import socket
import struct
import tkinter as tk
from tkinter import filedialog, messagebox

# Tamanho do cabeçalho usado antes de cada JSON.
# O cabeçalho terá 8 bytes e informará quantos bytes existem na mensagem JSON.
HEADER_SIZE = 8
DEFAULT_PORT = 50000
DISCOVERY_MESSAGE = "TCP_FILE_SERVER_DISCOVERY_V1"


class TCPClientGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Cliente de Arquivos TCP - Parte 2")
        self.root.geometry("720x520")
        self.setup_ui()

    def setup_ui(self):
        conn_frame = tk.LabelFrame(self.root, text="Conexão com o Servidor", padx=10, pady=10)
        conn_frame.pack(fill="x", padx=10, pady=8)

        tk.Label(conn_frame, text="IP do Servidor:").grid(row=0, column=0, sticky="w", padx=(0, 5))
        self.ent_host = tk.Entry(conn_frame)
        self.ent_host.grid(row=0, column=1, padx=5, sticky="ew")
        self.ent_host.insert(0, "127.0.0.1")

        tk.Label(conn_frame, text="Porta:").grid(row=0, column=2, sticky="w", padx=(10, 5))
        self.ent_port = tk.Entry(conn_frame, width=10)
        self.ent_port.grid(row=0, column=3, padx=5, sticky="ew")
        self.ent_port.insert(0, str(DEFAULT_PORT))

        self.btn_discover = tk.Button(conn_frame, text="Localizar Servidor na Rede", command=self.discover_server)
        self.btn_discover.grid(row=0, column=4, padx=(10, 0), sticky="ew")

        help_text = (
            "Mesmo computador: use 127.0.0.1.  |  "
            "Computadores diferentes: use o IPv4 exibido no terminal do servidor ou clique em Localizar Servidor."
        )
        tk.Label(conn_frame, text=help_text, fg="gray").grid(row=1, column=0, columnspan=5, sticky="w", pady=(6, 0))

        conn_frame.columnconfigure(1, weight=1)

        action_frame = tk.Frame(self.root, padx=10, pady=5)
        action_frame.pack(fill="x")

        self.btn_list = tk.Button(action_frame, text="Listar Arquivos", command=self.list_files, width=18)
        self.btn_list.pack(side="left", padx=5)

        self.btn_upload = tk.Button(action_frame, text="Fazer Upload", command=self.upload_file, width=18)
        self.btn_upload.pack(side="left", padx=5)

        self.btn_download = tk.Button(action_frame, text="Fazer Download", command=self.download_file, width=18)
        self.btn_download.pack(side="left", padx=5)

        list_frame = tk.LabelFrame(self.root, text="Arquivos no Servidor", padx=10, pady=10)
        list_frame.pack(fill="both", expand=True, padx=10, pady=8)

        self.file_listbox = tk.Listbox(list_frame)
        self.file_listbox.pack(side="left", fill="both", expand=True)

        scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=self.file_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.file_listbox.config(yscrollcommand=scrollbar.set)

        self.status_var = tk.StringVar()
        self.status_var.set("Pronto. Inicie o servidor primeiro e depois conecte o cliente.")
        status_label = tk.Label(self.root, textvariable=self.status_var, anchor="w", relief="sunken", padx=8)
        status_label.pack(fill="x", padx=10, pady=(0, 8))

    def get_port(self):
        try:
            port = int(self.ent_port.get().strip())
            if port <= 0 or port > 65535:
                raise ValueError
            return port
        except ValueError:
            raise ValueError("A porta deve ser um número entre 1 e 65535.")

    def get_socket(self):
        host = self.ent_host.get().strip()
        port = self.get_port()

        if not host:
            raise ValueError("Informe o IP do servidor.")

        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_socket.settimeout(40.0)
        tcp_socket.connect((host, port))
        return tcp_socket

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
            raise ConnectionError("O servidor fechou a conexão antes de enviar o cabeçalho da resposta.")

        message_size = struct.unpack("!Q", header)[0]
        payload = self.receive_exactly(sock, message_size)
        if payload is None:
            raise ConnectionError("O servidor fechou a conexão antes de enviar a resposta completa.")

        return json.loads(payload.decode("utf-8"))

    def send_json(self, sock, message):
        payload = json.dumps(message, ensure_ascii=False).encode("utf-8")
        header = struct.pack("!Q", len(payload))
        sock.sendall(header + payload)

    def get_file_hash(self, file_path):
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as file:
            for byte_block in iter(lambda: file.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def show_connection_error(self, action, error):
        message = (
            f"Erro ao {action}: {error}\n\n"
            "Verifique estes pontos:\n"
            "1. O tcp_server.py está rodando no outro computador?\n"
            "2. O IP no cliente é o IPv4 mostrado no terminal do servidor?\n"
            "3. Os dois computadores estão na mesma rede Wi-Fi/cabeada?\n"
            "4. A porta do cliente é a mesma porta exibida no servidor?\n\n"
            "Observação importante: nenhum código consegue furar uma política de bloqueio total de entrada. "
            "Mas esta versão usa uma porta alta e descoberta automática para funcionar na maioria das redes locais de laboratório."
        )
        messagebox.showerror("Erro de conexão", message)

    def discover_server(self):
        port = None
        udp_socket = None

        try:
            port = self.get_port()
            self.status_var.set("Procurando servidor na rede local...")
            self.root.update_idletasks()

            udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            udp_socket.settimeout(4.0)

            udp_socket.sendto(DISCOVERY_MESSAGE.encode("utf-8"), ("255.255.255.255", port))
            data, address = udp_socket.recvfrom(4096)
            response = json.loads(data.decode("utf-8"))

            if response.get("service") != DISCOVERY_MESSAGE:
                raise ValueError("A resposta recebida não pertence ao servidor esperado.")

            server_ip = address[0]
            self.ent_host.delete(0, tk.END)
            self.ent_host.insert(0, server_ip)

            discovered_port = response.get("tcp_port", port)
            self.ent_port.delete(0, tk.END)
            self.ent_port.insert(0, str(discovered_port))

            self.status_var.set(f"Servidor localizado em {server_ip}:{discovered_port}.")
            messagebox.showinfo("Servidor encontrado", f"Servidor localizado em {server_ip}:{discovered_port}.")

        except Exception as error:
            self.status_var.set("Não foi possível localizar automaticamente o servidor.")
            messagebox.showwarning(
                "Servidor não encontrado",
                "Não consegui localizar o servidor automaticamente.\n\n"
                "Digite manualmente o IPv4 que aparece no terminal do servidor.\n"
                f"Detalhe técnico: {error}"
            )
        finally:
            if udp_socket is not None:
                udp_socket.close()

    def list_files(self):
        tcp_socket = None
        try:
            self.status_var.set("Conectando ao servidor para listar arquivos...")
            self.root.update_idletasks()

            tcp_socket = self.get_socket()
            self.send_json(tcp_socket, {"cmd": "list_req"})
            response = self.receive_json(tcp_socket)

            if response.get("cmd") == "list_resp" and response.get("status") == "ok":
                self.file_listbox.delete(0, tk.END)
                for file_name in response.get("files", []):
                    self.file_listbox.insert(tk.END, file_name)
                self.status_var.set("Lista de arquivos atualizada com sucesso.")
            else:
                raise RuntimeError(response.get("message", "Resposta inesperada do servidor."))

        except Exception as error:
            self.status_var.set("Falha ao listar arquivos.")
            self.show_connection_error("listar arquivos", error)
        finally:
            if tcp_socket is not None:
                tcp_socket.close()

    def upload_file(self):
        file_path = filedialog.askopenfilename()
        if not file_path:
            return

        tcp_socket = None
        file_name = os.path.basename(file_path)

        try:
            self.status_var.set(f"Preparando upload de {file_name}...")
            self.root.update_idletasks()

            file_hash = self.get_file_hash(file_path)
            with open(file_path, "rb") as file:
                file_bytes = file.read()

            request = {
                "cmd": "put_req",
                "file": file_name,
                "hash": file_hash,
                "value": base64.b64encode(file_bytes).decode("utf-8")
            }

            self.status_var.set(f"Enviando {file_name} para o servidor...")
            self.root.update_idletasks()

            tcp_socket = self.get_socket()
            self.send_json(tcp_socket, request)
            response = self.receive_json(tcp_socket)

            if response.get("status") == "ok":
                self.status_var.set(f"Upload concluído: {file_name}.")
                messagebox.showinfo("Sucesso", response.get("message", f"Upload de {file_name} concluído!"))
                self.list_files()
            else:
                raise RuntimeError(response.get("message", "Falha no upload."))

        except Exception as error:
            self.status_var.set("Falha no upload.")
            self.show_connection_error("fazer upload", error)
        finally:
            if tcp_socket is not None:
                tcp_socket.close()

    def download_file(self):
        selected = self.file_listbox.curselection()
        if not selected:
            messagebox.showwarning("Aviso", "Selecione um arquivo na lista antes de baixar.")
            return

        file_name = self.file_listbox.get(selected[0])
        save_path = filedialog.asksaveasfilename(initialfile=file_name)
        if not save_path:
            return

        tcp_socket = None

        try:
            self.status_var.set(f"Solicitando download de {file_name}...")
            self.root.update_idletasks()

            tcp_socket = self.get_socket()
            self.send_json(tcp_socket, {"cmd": "get_req", "file": file_name})
            response = self.receive_json(tcp_socket)

            if response.get("cmd") != "get_resp" or response.get("status") != "ok":
                raise RuntimeError(response.get("message", "Arquivo não encontrado ou resposta inválida."))

            file_bytes = base64.b64decode(response.get("value", "").encode("utf-8"))
            received_hash = response.get("hash", "")

            with open(save_path, "wb") as file:
                file.write(file_bytes)

            calculated_hash = self.get_file_hash(save_path)
            if calculated_hash != received_hash:
                os.remove(save_path)
                raise RuntimeError("Hash inconsistente. O arquivo baixado foi removido.")

            self.status_var.set(f"Download concluído: {file_name}.")
            messagebox.showinfo("Sucesso", f"Download de {file_name} concluído com integridade verificada!")

        except Exception as error:
            self.status_var.set("Falha no download.")
            self.show_connection_error("fazer download", error)
        finally:
            if tcp_socket is not None:
                tcp_socket.close()


if __name__ == "__main__":
    root = tk.Tk()
    app = TCPClientGUI(root)
    root.mainloop()
