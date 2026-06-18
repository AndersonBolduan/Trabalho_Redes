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
DEFAULT_PORT = 50000
DISCOVERY_MESSAGE = "TCP_FILE_SERVER_DISCOVERY_V1"


class TCPClientGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Cliente de Arquivos TCP - Parte 2")
        self.root.geometry("820x560")
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

        self.btn_test = tk.Button(conn_frame, text="Testar Conexão TCP", command=self.test_connection)
        self.btn_test.grid(row=0, column=4, padx=(10, 0), sticky="ew")

        self.btn_discover = tk.Button(conn_frame, text="Localizar Servidor", command=self.discover_server)
        self.btn_discover.grid(row=0, column=5, padx=(8, 0), sticky="ew")

        self.btn_diagnostic = tk.Button(conn_frame, text="Diagnóstico", command=self.show_diagnostic)
        self.btn_diagnostic.grid(row=0, column=6, padx=(8, 0), sticky="ew")

        help_text = (
            "Mesmo computador: 127.0.0.1.  |  "
            "Outro computador: use o IPv4 mostrado no terminal do servidor e clique em Testar Conexão TCP."
        )
        tk.Label(conn_frame, text=help_text, fg="gray").grid(row=1, column=0, columnspan=7, sticky="w", pady=(6, 0))

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
        self.status_var.set("Pronto. Inicie o servidor primeiro. Para outro PC, use o IP mostrado no terminal do servidor.")
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

    def get_broadcast_targets(self):
        targets = {"255.255.255.255"}

        for ip in self.get_local_ips():
            parts = ip.split(".")
            if len(parts) == 4:
                targets.add(f"{parts[0]}.{parts[1]}.{parts[2]}.255")

        return sorted(targets)

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
                "Isso costuma indicar IP errado, computadores em redes diferentes, bloqueio de entrada no servidor ou isolamento do Wi-Fi."
            )

        if "connection refused" in lower_text or "actively refused" in lower_text or "10061" in lower_text:
            return (
                "Conexão recusada. O computador respondeu, mas não existe servidor ouvindo nessa porta. "
                "Confira se o tcp_server.py está aberto e se a porta no cliente é a mesma do servidor."
            )

        if "unreachable" in lower_text or "10065" in lower_text or "10051" in lower_text:
            return (
                "Rede inalcançável. O IP informado provavelmente não pertence à mesma rede acessível pelo seu computador."
            )

        return "Erro de conexão não classificado. Confira IP, porta, rede e se o servidor está em execução."

    def show_connection_error(self, action, error):
        explanation = self.explain_socket_error(error)
        message = (
            f"Erro ao {action}: {error}\n\n"
            f"Interpretação: {explanation}\n\n"
            "Checklist rápido:\n"
            "1. No computador servidor, o terminal mostra algum IP 192.168.x.x, 10.x.x.x ou 172.16-31.x.x?\n"
            "2. Esse IP foi digitado no cliente do outro computador? Não use 127.0.0.1 entre computadores diferentes.\n"
            "3. A porta do cliente é exatamente a mesma porta do servidor?\n"
            "4. Quando você clica em Testar Conexão TCP, aparece alguma linha [TCP] no terminal do servidor?\n"
            "5. Se não aparece nada no servidor, o pacote nem chegou nele; isso indica IP errado, rede isolada ou bloqueio de entrada."
        )
        messagebox.showerror("Erro de conexão", message)

    def test_connection(self):
        tcp_socket = None
        try:
            host = self.get_host()
            port = self.get_port()
            self.status_var.set(f"Testando conexão TCP com {host}:{port}...")
            self.root.update_idletasks()

            tcp_socket = self.get_socket(timeout=8.0)
            self.send_json(tcp_socket, {"cmd": "test_req"})
            response = self.receive_json(tcp_socket)

            if response.get("cmd") == "test_resp" and response.get("status") == "ok":
                self.status_var.set(f"Conexão TCP OK com {host}:{port}.")
                messagebox.showinfo(
                    "Conexão funcionando",
                    "Conexão TCP com o servidor funcionando!\n\n"
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

    def discover_server(self):
        udp_socket = None
        responses = []
        errors = []

        try:
            port = self.get_port()
            targets = self.get_broadcast_targets()

            self.status_var.set("Procurando servidor por broadcast UDP...")
            self.root.update_idletasks()

            udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            udp_socket.settimeout(1.2)

            for target in targets:
                try:
                    udp_socket.sendto(DISCOVERY_MESSAGE.encode("utf-8"), (target, port))
                    errors.append(f"Enviado broadcast para {target}:{port}")
                except Exception as send_error:
                    errors.append(f"Falha ao enviar para {target}:{port}: {send_error}")

            while True:
                try:
                    data, address = udp_socket.recvfrom(4096)
                    response = json.loads(data.decode("utf-8"))
                    if response.get("service") == DISCOVERY_MESSAGE:
                        responses.append((address, response))
                except socket.timeout:
                    break

            if not responses:
                raise TimeoutError(
                    "Nenhum servidor respondeu ao broadcast UDP. Isso não prova que o TCP está bloqueado; "
                    "apenas indica que a descoberta automática não recebeu resposta. Use o IP manual e clique em Testar Conexão TCP."
                )

            address, response = responses[0]
            server_ip = address[0]
            discovered_port = response.get("tcp_port", port)

            self.ent_host.delete(0, tk.END)
            self.ent_host.insert(0, server_ip)
            self.ent_port.delete(0, tk.END)
            self.ent_port.insert(0, str(discovered_port))

            self.status_var.set(f"Servidor localizado em {server_ip}:{discovered_port}. Teste TCP antes de enviar arquivos.")
            messagebox.showinfo(
                "Servidor encontrado",
                f"Servidor localizado em {server_ip}:{discovered_port}.\n\n"
                "Agora clique em Testar Conexão TCP para confirmar se o TCP também passa pela rede."
            )

        except Exception as error:
            self.status_var.set("Descoberta automática não encontrou servidor.")
            messagebox.showwarning(
                "Servidor não encontrado por descoberta automática",
                "Não consegui localizar o servidor automaticamente por broadcast UDP.\n\n"
                "Isso é comum em redes Wi-Fi de laboratório, porque algumas redes bloqueiam broadcast entre clientes.\n\n"
                "Faça o teste manual:\n"
                "1. Veja o IPv4 que aparece no terminal do tcp_server.py.\n"
                "2. Digite esse IPv4 no campo IP do Servidor.\n"
                "3. Clique em Testar Conexão TCP.\n\n"
                f"Detalhe técnico: {error}"
            )
        finally:
            if udp_socket is not None:
                udp_socket.close()

    def show_diagnostic(self):
        host = self.ent_host.get().strip() or "não informado"
        port = self.ent_port.get().strip() or "não informada"
        local_ips = self.get_local_ips()
        targets = self.get_broadcast_targets()

        diagnostic = (
            "DIAGNÓSTICO DE REDE\n"
            "===================\n\n"
            f"IP do servidor configurado no cliente: {host}\n"
            f"Porta configurada no cliente: {port}\n\n"
            "IPs locais detectados neste computador cliente:\n"
            f"{chr(10).join('  - ' + ip for ip in local_ips) if local_ips else '  - Nenhum IP local detectado'}\n\n"
            "Endereços de broadcast que o botão Localizar Servidor tenta usar:\n"
            f"{chr(10).join('  - ' + target for target in targets)}\n\n"
            "Como diagnosticar no terminal do servidor:\n"
            "  - Se aparecer [UDP] Descoberta recebida, o broadcast chegou ao servidor.\n"
            "  - Se aparecer [TCP] Conexão aceita, o TCP chegou ao servidor.\n"
            "  - Se não aparecer nada, o pacote não chegou: IP errado, rede isolada ou bloqueio de entrada.\n\n"
            "Atenção: 127.0.0.1 só serve para o mesmo computador. Entre computadores diferentes, use o IPv4 exibido no servidor."
        )

        diagnostic_window = tk.Toplevel(self.root)
        diagnostic_window.title("Diagnóstico de Rede")
        diagnostic_window.geometry("680x460")

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
