"""
=============================================================================
AV3 - Parte 2: Cliente de Arquivos TCP com Interface Gráfica (GUI)
=============================================================================
Disciplina: Redes de Computadores I (RCA)
Curso: Ciência da Computação - IFSC Câmpus Lages
Professor: Robson Costa
Ano/Semestre: 2026/1

Descrição:
    Cliente com interface gráfica (tkinter) para comunicação com o servidor
    de arquivos TCP. Utiliza protocolo próprio baseado em JSON sobre TCP.
    
    Funcionalidades:
    - Listar arquivos existentes no servidor
    - Realizar download de arquivos
    - Realizar upload de arquivos
    - Verificação de integridade via SHA-256
    - Aviso de erro em caso de inconsistência do hash

    O servidor opera no modelo de FTP anônimo (sem autenticação).
=============================================================================
"""

import socket
import json
import hashlib
import base64
import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext


def calculate_sha256(data: bytes) -> str:
    """Calcula o hash SHA-256 de um conjunto de bytes."""
    return hashlib.sha256(data).hexdigest()


def recv_json(conn: socket.socket) -> dict:
    """
    Recebe uma mensagem JSON completa do socket.
    Protocolo: os primeiros 8 bytes indicam o tamanho da mensagem JSON em bytes.
    """
    header = b""
    while len(header) < 8:
        chunk = conn.recv(8 - len(header))
        if not chunk:
            raise ConnectionError("Conexão encerrada pelo servidor.")
        header += chunk

    msg_length = int(header.decode("utf-8").strip())

    data = b""
    while len(data) < msg_length:
        chunk = conn.recv(min(4096, msg_length - len(data)))
        if not chunk:
            raise ConnectionError("Conexão encerrada pelo servidor.")
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


class ClienteGUI:
    """Interface gráfica do cliente de arquivos TCP."""

    def __init__(self, root):
        self.root = root
        self.root.title("Cliente de Arquivos TCP - AV3 Parte 2")
        self.root.geometry("750x600")
        self.root.resizable(True, True)

        self.conn = None
        self.connected = False

        self._create_widgets()

    def _create_widgets(self):
        """Cria todos os widgets da interface gráfica."""

        # ===== Frame de Conexão =====
        frame_conn = ttk.LabelFrame(self.root, text="Conexão com o Servidor", padding=10)
        frame_conn.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(frame_conn, text="Endereço IP:").grid(row=0, column=0, sticky=tk.W)
        self.entry_host = ttk.Entry(frame_conn, width=20)
        self.entry_host.insert(0, "127.0.0.1")
        self.entry_host.grid(row=0, column=1, padx=5)

        ttk.Label(frame_conn, text="Porta:").grid(row=0, column=2, sticky=tk.W)
        self.entry_port = ttk.Entry(frame_conn, width=8)
        self.entry_port.insert(0, "5000")
        self.entry_port.grid(row=0, column=3, padx=5)

        self.btn_connect = ttk.Button(frame_conn, text="Conectar", command=self._connect)
        self.btn_connect.grid(row=0, column=4, padx=10)

        self.btn_disconnect = ttk.Button(frame_conn, text="Desconectar",
                                         command=self._disconnect, state=tk.DISABLED)
        self.btn_disconnect.grid(row=0, column=5, padx=5)

        self.lbl_status = ttk.Label(frame_conn, text="● Desconectado", foreground="red")
        self.lbl_status.grid(row=0, column=6, padx=10)

        # ===== Frame de Operações =====
        frame_ops = ttk.LabelFrame(self.root, text="Operações", padding=10)
        frame_ops.pack(fill=tk.X, padx=10, pady=5)

        self.btn_list = ttk.Button(frame_ops, text="Listar Arquivos",
                                   command=self._list_files, state=tk.DISABLED)
        self.btn_list.pack(side=tk.LEFT, padx=5)

        self.btn_upload = ttk.Button(frame_ops, text="Upload de Arquivo",
                                     command=self._upload_file, state=tk.DISABLED)
        self.btn_upload.pack(side=tk.LEFT, padx=5)

        self.btn_download = ttk.Button(frame_ops, text="Download de Arquivo",
                                       command=self._download_file, state=tk.DISABLED)
        self.btn_download.pack(side=tk.LEFT, padx=5)

        # ===== Frame da Lista de Arquivos =====
        frame_files = ttk.LabelFrame(self.root, text="Arquivos no Servidor", padding=10)
        frame_files.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Listbox com scrollbar
        scrollbar = ttk.Scrollbar(frame_files, orient=tk.VERTICAL)
        self.listbox_files = tk.Listbox(frame_files, yscrollcommand=scrollbar.set,
                                        selectmode=tk.SINGLE, font=("Courier", 10))
        scrollbar.config(command=self.listbox_files.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox_files.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # ===== Frame de Log =====
        frame_log = ttk.LabelFrame(self.root, text="Log de Operações", padding=10)
        frame_log.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.text_log = scrolledtext.ScrolledText(frame_log, height=8, font=("Courier", 9))
        self.text_log.pack(fill=tk.BOTH, expand=True)
        self.text_log.config(state=tk.DISABLED)

    def _log(self, message: str):
        """Adiciona uma mensagem ao log."""
        self.text_log.config(state=tk.NORMAL)
        self.text_log.insert(tk.END, message + "\n")
        self.text_log.see(tk.END)
        self.text_log.config(state=tk.DISABLED)

    def _set_connected(self, status: bool):
        """Atualiza o estado de conexão na interface."""
        self.connected = status
        if status:
            self.lbl_status.config(text="● Conectado", foreground="green")
            self.btn_connect.config(state=tk.DISABLED)
            self.btn_disconnect.config(state=tk.NORMAL)
            self.btn_list.config(state=tk.NORMAL)
            self.btn_upload.config(state=tk.NORMAL)
            self.btn_download.config(state=tk.NORMAL)
        else:
            self.lbl_status.config(text="● Desconectado", foreground="red")
            self.btn_connect.config(state=tk.NORMAL)
            self.btn_disconnect.config(state=tk.DISABLED)
            self.btn_list.config(state=tk.DISABLED)
            self.btn_upload.config(state=tk.DISABLED)
            self.btn_download.config(state=tk.DISABLED)

    def _connect(self):
        """Conecta ao servidor TCP."""
        host = self.entry_host.get().strip()
        try:
            port = int(self.entry_port.get().strip())
        except ValueError:
            messagebox.showerror("Erro", "Porta inválida. Informe um número inteiro.")
            return

        try:
            self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.conn.connect((host, port))
            self._set_connected(True)
            self._log(f"[CONECTADO] Conectado ao servidor {host}:{port}")
        except Exception as e:
            messagebox.showerror("Erro de Conexão",
                                 f"Não foi possível conectar ao servidor.\n\n{e}")
            self._log(f"[ERRO] Falha ao conectar: {e}")
            self.conn = None

    def _disconnect(self):
        """Desconecta do servidor."""
        try:
            if self.conn:
                self.conn.close()
        except Exception:
            pass
        self.conn = None
        self._set_connected(False)
        self.listbox_files.delete(0, tk.END)
        self._log("[DESCONECTADO] Conexão encerrada.")

    def _list_files(self):
        """Solicita a lista de arquivos ao servidor (LIST_REQ)."""
        if not self.connected:
            return

        try:
            request = {"cmd": "list_req"}
            send_json(self.conn, request)
            self._log("[ENVIADO] LIST_REQ")

            response = recv_json(self.conn)

            if response.get("cmd") == "list_resp":
                files = response.get("files", [])
                self.listbox_files.delete(0, tk.END)
                for f in files:
                    self.listbox_files.insert(tk.END, f)
                self._log(f"[RECEBIDO] LIST_RESP - {len(files)} arquivo(s) encontrado(s).")
            else:
                self._log("[ERRO] Resposta inesperada do servidor.")

        except Exception as e:
            self._log(f"[ERRO] Falha ao listar arquivos: {e}")
            messagebox.showerror("Erro", f"Falha ao listar arquivos:\n{e}")
            self._disconnect()

    def _upload_file(self):
        """Realiza upload de um arquivo para o servidor (PUT_REQ)."""
        if not self.connected:
            return

        # Abre diálogo para selecionar arquivo
        file_path = filedialog.askopenfilename(title="Selecionar arquivo para upload")
        if not file_path:
            return

        try:
            file_name = os.path.basename(file_path)

            # Lê o conteúdo do arquivo
            with open(file_path, "rb") as f:
                file_data = f.read()

            # Calcula o hash SHA-256
            hash_value = calculate_sha256(file_data)

            # Codifica em Base64
            file_base64 = base64.b64encode(file_data).decode("utf-8")

            # Monta e envia a requisição PUT_REQ
            request = {
                "cmd": "put_req",
                "file": file_name,
                "hash": hash_value,
                "value": file_base64
            }
            send_json(self.conn, request)
            self._log(f"[ENVIADO] PUT_REQ - Arquivo: '{file_name}' "
                      f"({len(file_data)} bytes, SHA-256: {hash_value[:16]}...)")

            # Recebe a resposta
            response = recv_json(self.conn)

            if response.get("cmd") == "put_resp":
                status = response.get("status", "fail")
                if status == "ok":
                    self._log(f"[RECEBIDO] PUT_RESP - Upload de '{file_name}' realizado com sucesso!")
                    messagebox.showinfo("Sucesso",
                                        f"Upload de '{file_name}' realizado com sucesso!")
                else:
                    self._log(f"[RECEBIDO] PUT_RESP - FALHA no upload de '{file_name}'.")
                    messagebox.showerror("Erro",
                                         f"Falha no upload de '{file_name}'.\n"
                                         f"O servidor reportou erro de integridade (hash).")
            else:
                self._log("[ERRO] Resposta inesperada do servidor.")

        except Exception as e:
            self._log(f"[ERRO] Falha no upload: {e}")
            messagebox.showerror("Erro", f"Falha no upload:\n{e}")
            self._disconnect()

    def _download_file(self):
        """Realiza download de um arquivo do servidor (GET_REQ)."""
        if not self.connected:
            return

        # Verifica se há um arquivo selecionado na lista
        selection = self.listbox_files.curselection()
        if not selection:
            messagebox.showwarning("Aviso",
                                   "Selecione um arquivo na lista para realizar o download.\n"
                                   "Use 'Listar Arquivos' primeiro.")
            return

        file_name = self.listbox_files.get(selection[0])

        # Abre diálogo para escolher onde salvar
        save_path = filedialog.asksaveasfilename(
            title="Salvar arquivo como",
            initialfile=file_name
        )
        if not save_path:
            return

        try:
            # Envia GET_REQ
            request = {
                "cmd": "get_req",
                "file": file_name
            }
            send_json(self.conn, request)
            self._log(f"[ENVIADO] GET_REQ - Arquivo: '{file_name}'")

            # Recebe GET_RESP
            response = recv_json(self.conn)

            if response.get("cmd") == "get_resp":
                file_base64 = response.get("value", "")
                hash_received = response.get("hash", "")

                if not file_base64:
                    self._log(f"[ERRO] Arquivo '{file_name}' não encontrado no servidor.")
                    messagebox.showerror("Erro",
                                         f"Arquivo '{file_name}' não encontrado no servidor.")
                    return

                # Decodifica o conteúdo
                file_data = base64.b64decode(file_base64)

                # Verifica integridade com SHA-256
                computed_hash = calculate_sha256(file_data)

                if computed_hash != hash_received:
                    self._log(f"[ERRO] HASH INCONSISTENTE para '{file_name}'!")
                    self._log(f"  Hash recebido:  {hash_received}")
                    self._log(f"  Hash calculado: {computed_hash}")
                    messagebox.showerror(
                        "Erro de Integridade",
                        f"ATENÇÃO: O hash do arquivo '{file_name}' está inconsistente!\n\n"
                        f"Hash recebido do servidor:\n{hash_received}\n\n"
                        f"Hash calculado localmente:\n{computed_hash}\n\n"
                        f"O arquivo pode estar corrompido. Download cancelado."
                    )
                    return

                # Salva o arquivo
                with open(save_path, "wb") as f:
                    f.write(file_data)

                self._log(f"[RECEBIDO] GET_RESP - Arquivo '{file_name}' baixado com sucesso "
                          f"({len(file_data)} bytes, hash OK).")
                messagebox.showinfo("Sucesso",
                                    f"Download de '{file_name}' realizado com sucesso!\n"
                                    f"Salvo em: {save_path}\n"
                                    f"Integridade verificada (SHA-256 OK).")
            else:
                self._log("[ERRO] Resposta inesperada do servidor.")

        except Exception as e:
            self._log(f"[ERRO] Falha no download: {e}")
            messagebox.showerror("Erro", f"Falha no download:\n{e}")
            self._disconnect()

    def on_closing(self):
        """Tratamento ao fechar a janela."""
        if self.connected:
            self._disconnect()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = ClienteGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
