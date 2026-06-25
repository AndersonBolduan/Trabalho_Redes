"""
AV3 - Parte 2: Cliente de Arquivos TCP com GUI
Disciplina: Redes de Computadores I (RCA) - IFSC Câmpus Lages
Professor: Robson Costa | 2026/1
"""

import socket
import json
import hashlib
import base64
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext


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


class ClienteGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Cliente de Arquivos TCP - AV3 Parte 2")
        self.root.geometry("720x550")
        self.conn = None
        self.connected = False
        self._create_widgets()

    def _create_widgets(self):
        # Frame Conexão
        fc = ttk.LabelFrame(self.root, text="Conexão", padding=8)
        fc.pack(fill=tk.X, padx=8, pady=4)

        ttk.Label(fc, text="IP do Servidor:").grid(row=0, column=0)
        self.entry_host = ttk.Entry(fc, width=18)
        self.entry_host.insert(0, "127.0.0.1")
        self.entry_host.grid(row=0, column=1, padx=4)

        ttk.Label(fc, text="Porta:").grid(row=0, column=2)
        self.entry_port = ttk.Entry(fc, width=7)
        self.entry_port.insert(0, "5000")
        self.entry_port.grid(row=0, column=3, padx=4)

        self.btn_conn = ttk.Button(fc, text="Conectar", command=self._connect)
        self.btn_conn.grid(row=0, column=4, padx=6)
        self.btn_disc = ttk.Button(fc, text="Desconectar", command=self._disconnect, state=tk.DISABLED)
        self.btn_disc.grid(row=0, column=5, padx=4)
        self.lbl_status = ttk.Label(fc, text="⬤ Desconectado", foreground="red")
        self.lbl_status.grid(row=0, column=6, padx=8)

        # Frame Operações
        fo = ttk.LabelFrame(self.root, text="Operações", padding=8)
        fo.pack(fill=tk.X, padx=8, pady=4)
        self.btn_list = ttk.Button(fo, text="Listar Arquivos", command=self._list_files, state=tk.DISABLED)
        self.btn_list.pack(side=tk.LEFT, padx=4)
        self.btn_upload = ttk.Button(fo, text="Upload", command=self._upload, state=tk.DISABLED)
        self.btn_upload.pack(side=tk.LEFT, padx=4)
        self.btn_download = ttk.Button(fo, text="Download", command=self._download, state=tk.DISABLED)
        self.btn_download.pack(side=tk.LEFT, padx=4)

        # Lista de arquivos
        fl = ttk.LabelFrame(self.root, text="Arquivos no Servidor", padding=8)
        fl.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)
        sb = ttk.Scrollbar(fl, orient=tk.VERTICAL)
        self.listbox = tk.Listbox(fl, yscrollcommand=sb.set, font=("Courier", 10))
        sb.config(command=self.listbox.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Log
        flog = ttk.LabelFrame(self.root, text="Log", padding=8)
        flog.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)
        self.log = scrolledtext.ScrolledText(flog, height=7, font=("Courier", 9))
        self.log.pack(fill=tk.BOTH, expand=True)
        self.log.config(state=tk.DISABLED)

    def _log(self, msg):
        self.log.config(state=tk.NORMAL)
        self.log.insert(tk.END, msg + "\n")
        self.log.see(tk.END)
        self.log.config(state=tk.DISABLED)

    def _set_connected(self, status):
        self.connected = status
        if status:
            self.lbl_status.config(text="⬤ Conectado", foreground="green")
            self.btn_conn.config(state=tk.DISABLED)
            self.btn_disc.config(state=tk.NORMAL)
            self.btn_list.config(state=tk.NORMAL)
            self.btn_upload.config(state=tk.NORMAL)
            self.btn_download.config(state=tk.NORMAL)
        else:
            self.lbl_status.config(text="⬤ Desconectado", foreground="red")
            self.btn_conn.config(state=tk.NORMAL)
            self.btn_disc.config(state=tk.DISABLED)
            self.btn_list.config(state=tk.DISABLED)
            self.btn_upload.config(state=tk.DISABLED)
            self.btn_download.config(state=tk.DISABLED)

    def _connect(self):
        host = self.entry_host.get().strip()
        try:
            port = int(self.entry_port.get().strip())
        except ValueError:
            messagebox.showerror("Erro", "Porta inválida.")
            return
        try:
            self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.conn.settimeout(10)
            self.conn.connect((host, port))
            self.conn.settimeout(60)
            self._set_connected(True)
            self._log(f"Conectado a {host}:{port}")
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível conectar:\n{e}")
            self._log(f"ERRO ao conectar: {e}")
            self.conn = None

    def _disconnect(self):
        try:
            if self.conn:
                self.conn.close()
        except Exception:
            pass
        self.conn = None
        self._set_connected(False)
        self.listbox.delete(0, tk.END)
        self._log("Desconectado.")

    def _list_files(self):
        if not self.connected:
            return
        try:
            send_json(self.conn, {"cmd": "list_req"})
            resp = recv_json(self.conn)
            files = resp.get("files", [])
            self.listbox.delete(0, tk.END)
            for f in files:
                self.listbox.insert(tk.END, f)
            self._log(f"LIST: {len(files)} arquivo(s)")
        except Exception as e:
            self._log(f"ERRO: {e}")
            messagebox.showerror("Erro", str(e))
            self._disconnect()

    def _upload(self):
        if not self.connected:
            return
        path = filedialog.askopenfilename(title="Selecionar arquivo para upload")
        if not path:
            return
        try:
            name = os.path.basename(path)
            with open(path, "rb") as f:
                data = f.read()
            h = calculate_sha256(data)
            b64 = base64.b64encode(data).decode("utf-8")
            send_json(self.conn, {"cmd": "put_req", "file": name, "hash": h, "value": b64})
            resp = recv_json(self.conn)
            if resp.get("status") == "ok":
                self._log(f"PUT OK: {name} ({len(data)} bytes)")
                messagebox.showinfo("Sucesso", f"Upload de '{name}' concluído!")
            else:
                self._log(f"PUT FAIL: {name}")
                messagebox.showerror("Erro", f"Servidor rejeitou '{name}' (hash inconsistente).")
        except Exception as e:
            self._log(f"ERRO: {e}")
            messagebox.showerror("Erro", str(e))
            self._disconnect()

    def _download(self):
        if not self.connected:
            return
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showwarning("Aviso", "Selecione um arquivo na lista primeiro.")
            return
        name = self.listbox.get(sel[0])
        save_path = filedialog.asksaveasfilename(title="Salvar como", initialfile=name)
        if not save_path:
            return
        try:
            send_json(self.conn, {"cmd": "get_req", "file": name})
            resp = recv_json(self.conn)
            if not resp.get("value"):
                messagebox.showerror("Erro", f"Arquivo '{name}' não encontrado no servidor.")
                return
            data = base64.b64decode(resp["value"])
            h = calculate_sha256(data)
            if h != resp.get("hash", ""):
                self._log(f"HASH INCONSISTENTE: {name}")
                messagebox.showerror("Erro de Integridade",
                    f"HASH INCONSISTENTE para '{name}'!\n\n"
                    f"Esperado: {resp['hash']}\nCalculado: {h}\n\n"
                    "O arquivo pode estar corrompido. Download cancelado.")
                return
            with open(save_path, "wb") as f:
                f.write(data)
            self._log(f"GET OK: {name} ({len(data)} bytes) - hash verificado")
            messagebox.showinfo("Sucesso", f"Download de '{name}' concluído!\nHash SHA-256 OK.")
        except Exception as e:
            self._log(f"ERRO: {e}")
            messagebox.showerror("Erro", str(e))
            self._disconnect()

    def on_closing(self):
        if self.connected:
            self._disconnect()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = ClienteGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
