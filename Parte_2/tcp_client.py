import base64
import hashlib
import json
import os
import socket
import struct
import tkinter as tk
from tkinter import filedialog, messagebox

# Cada mensagem JSON é enviada com um cabeçalho fixo de 8 bytes.
# Esse cabeçalho informa o tamanho exato do JSON que virá depois.
HEADER_SIZE = 8
DEFAULT_HOST = "192.168.56.1"
DEFAULT_PORT = 50000


class TCPClientGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Cliente de Arquivos TCP - Parte 2")
        self.root.geometry("780x540")
        self.setup_ui()

    def setup_ui(self):
        conn_frame = tk.LabelFrame(self.root, text="Conexão Manual com o Servidor", padx=10, pady=10)
        conn_frame.pack(fill="x", padx=10, pady=8)

        tk.Label(conn_frame, text="IP do Servidor:").grid(row=0, column=0, sticky="w", padx=(0, 5))
        self.ent_host = tk.Entry(conn_frame)
        self.ent_host.grid(row=0, column=1, padx=5, sticky="ew")
        self.ent_host.insert(0, DEFAULT_HOST)

        tk.Label(conn_frame, text="Porta:").grid(row=0, column=2, sticky="w", padx=(10, 5))
        self.ent_port = tk.Entry(conn_frame, width=10)
        self.ent_port.grid(row=0, column=3, padx=5, sticky="ew")
        self.ent_port.insert(0, str(DEFAULT_PORT))

        self.btn_test = tk.Button(conn_frame, text="Testar Conexão TCP", command=self.test_connection)
        self.btn_test.grid(row=0, column=4, padx=(10, 0), sticky="ew")

        self.btn_diagnostic = tk.Button(conn_frame, text="Diagnóstico", command=self.show_diagnostic)
        self.btn_diagnostic.grid(row=0, column=5, padx=(8, 0), sticky="ew")

        help_text = (
            "Teste manual: servidor em 192.168.56.1 e porta 50000. "
            "A descoberta automática por UDP foi removida desta versão."
        )
        tk.Label(conn_frame, text=help_text, fg="gray").grid(row=1, column=0, columnspan=6, sticky="w", pady=(6, 0))

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
        self.status_var.set("Pronto. IP padrão de teste: 192.168.56.1:50000. Clique em Testar Conexão TCP.")
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

    def get_host(self):
        host = self.ent_host.get().strip()
        if not host:
            raise ValueError("Informe o IP do servidor.")
        return host

    def get_socket(self, timeout=40.0):
        host = self.get_host()
        port = self.get_port()

        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_socket.settimeout(timeout)
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

    def get_local_ips(self):
        ips = set()

        try:
            hostname = socket.gethostname()
            for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
                ip = info[4][0]
                if not ip.startswith("127.") and not ip.startswith("169.254."):
                    ips.add(ip)
        except OSError:
            pass

        try:
            temp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            temp_socket.connect(("8.8.8.8", 80))
            ip = temp_socket.getsockname()[0]
            if not ip.startswith("127.") and not ip.startswith("169.254."):
                ips.add(ip)
            temp_socket.close()
        except OSError:
            pass

        return sorted(ips)

    def get_file_hash(self, file_path):
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as file:
            for byte_block in iter(lambda: file.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def explain_socket_error(self, error):
        error_text = str(error)
        lower_text = error_text.lower()

        if "timed out" in lower_text or "tempo" in lower_text:
            return (
                "Tempo esgotado. O cliente tentou chegar ao servidor, mas não recebeu resposta. "
                "Isso costuma indicar IP errado, computadores em redes diferentes, bloqueio de entrada no servidor ou isolamento da rede."
            )

        if "connection refused" in lower_text or "actively refused" in lower_text or "10061" in lower_text:
            return (
                "Conexão recusada. O computador respondeu, mas não existe servidor ouvindo nessa porta. "
                "Confira se o tcp_server.py está aberto e se a porta no cliente é a mesma do servidor."
            )

        if "unreachable" in lower_text or "10065" in lower_text or "10051" in lower_text:
            return "Rede inalcançável. O IP informado provavelmente não pertence à mesma rede acessível pelo seu computador."

        return "Erro de conexão não classificado. Confira IP, porta, rede e se o servidor está em execução."

    def show_connection_error(self, action, error):
        explanation = self.explain_socket_error(error)
        message = (
            f"Erro ao {action}: {error}\n\n"
            f"Interpretação: {explanation}\n\n"
            "Checklist rápido:\n"
            "1. No computador servidor, o tcp_server.py está aberto?\n"
            "2. O servidor está escutando na porta 50000?\n"
            "3. No cliente, o IP está como 192.168.56.1 e a porta como 50000?\n"
            "4. Quando você clica em Testar Conexão TCP, aparece alguma linha [TCP] no terminal do servidor?\n"
            "5. Se não aparece nada no servidor, a tentativa não chegou nele: IP errado, rota de rede ou bloqueio de entrada."
        )
        messagebox.showerror("Erro de conexão", message)

    def test_connection(self):
        tcp_socket = None
        try:
            host = self.get_host()
            port = self.get_port()
            self.status_var.set(f"Testando conexão TCP manual com {host}:{port}...")
            self.root.update_idletasks()

            tcp_socket = self.get_socket(timeout=8.0)
            self.send_json(tcp_socket, {"cmd": "test_req"})
            response = self.receive_json(tcp_socket)

            if response.get("cmd") == "test_resp" and response.get("status") == "ok":
                self.status_var.set(f"Conexão TCP OK com {host}:{port}.")
                messagebox.showinfo(
                    "Conexão funcionando",
                    "Conexão TCP manual com o servidor funcionando!\n\n"
                    f"Mensagem do servidor: {response.get('message')}\n"
                    f"Seu IP visto pelo servidor: {response.get('client_ip_seen_by_server')}\n"
                    f"IPs do servidor informados: {', '.join(response.get('server_ips', []))}"
                )
            else:
                raise RuntimeError(response.get("message", "Resposta inesperada no teste de conexão."))

        except Exception as error:
            self.status_var.set("Falha no teste de conexão TCP.")
            self.show_connection_error("testar conexão TCP", error)
        finally:
            if tcp_socket is not None:
                tcp_socket.close()

    def show_diagnostic(self):
        host = self.ent_host.get().strip() or "não informado"
        port = self.ent_port.get().strip() or "não informada"
        local_ips = self.get_local_ips()

        diagnostic = (
            "DIAGNÓSTICO DE CONEXÃO MANUAL\n"
            "=============================\n\n"
            f"IP configurado no cliente: {host}\n"
            f"Porta configurada no cliente: {port}\n\n"
            "Configuração padrão desta versão de teste:\n"
            f"  - IP do servidor: {DEFAULT_HOST}\n"
            f"  - Porta do servidor: {DEFAULT_PORT}\n\n"
            "IPs locais detectados neste computador cliente:\n"
            f"{chr(10).join('  - ' + ip for ip in local_ips) if local_ips else '  - Nenhum IP local detectado'}\n\n"
            "Como diagnosticar no terminal do servidor:\n"
            "  - Se aparecer [TCP] Conexão aceita, a conexão chegou ao servidor.\n"
            "  - Se não aparecer nada, o pacote não chegou ao servidor.\n"
            "  - Nesta versão, não existe descoberta automática por UDP. O teste é somente por IP e porta.\n\n"
            "Atenção: 127.0.0.1 só serve para o mesmo computador. Para o teste solicitado, use 192.168.56.1:50000."
        )

        diagnostic_window = tk.Toplevel(self.root)
        diagnostic_window.title("Diagnóstico de Conexão Manual")
        diagnostic_window.geometry("680x420")

        text = tk.Text(diagnostic_window, wrap="word")
        text.pack(fill="both", expand=True, padx=10, pady=10)
        text.insert("1.0", diagnostic)
        text.config(state="disabled")

    def list_files(self):
        tcp_socket = None
        try:
            self.status_var.set("Conectando ao servidor para listar arquivos...")
            self.root.update_idletasks()

            tcp_socket = self.get_socket(timeout=15.0)
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

            tcp_socket = self.get_socket(timeout=60.0)
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

            tcp_socket = self.get_socket(timeout=60.0)
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
