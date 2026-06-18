import socket
import json
import os
import base64
import hashlib
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

class TCPClientGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Cliente de Arquivos TCP (V2) - Parte 2")
        self.root.geometry("600x450")
        self.setup_ui()

    def setup_ui(self):
        conn_frame = tk.LabelFrame(self.root, text="Conexão", padx=10, pady=10)
        conn_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(conn_frame, text="IP do Servidor:").grid(row=0, column=0, sticky="w")
        self.ent_host = tk.Entry(conn_frame)
        self.ent_host.grid(row=0, column=1, padx=5, sticky="ew")
        self.ent_host.insert(0, "127.0.0.1")
        
        tk.Label(conn_frame, text="Porta:").grid(row=0, column=2, sticky="w")
        self.ent_port = tk.Entry(conn_frame, width=10)
        self.ent_port.grid(row=0, column=3, padx=5, sticky="ew")
        self.ent_port.insert(0, "6000")
        
        # Dica para conexão em rede local
        tk.Label(conn_frame, text="(Para conexão em rede local, use o IP da máquina do servidor, não 127.0.0.1)", fg="gray").grid(row=1, column=0, columnspan=4, sticky="w")
        
        conn_frame.columnconfigure(1, weight=1)

        action_frame = tk.Frame(self.root, padx=10, pady=5)
        action_frame.pack(fill="x")
        
        self.btn_list = tk.Button(action_frame, text="Listar Arquivos", command=self.list_files)
        self.btn_list.pack(side="left", padx=5)
        
        self.btn_upload = tk.Button(action_frame, text="Fazer Upload", command=self.upload_file)
        self.btn_upload.pack(side="left", padx=5)
        
        self.btn_download = tk.Button(action_frame, text="Fazer Download", command=self.download_file)
        self.btn_download.pack(side="left", padx=5)

        list_frame = tk.LabelFrame(self.root, text="Arquivos no Servidor", padx=10, pady=10)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.file_listbox = tk.Listbox(list_frame)
        self.file_listbox.pack(fill="both", expand=True)

    def get_socket(self):
        host = self.ent_host.get()
        port = int(self.ent_port.get())
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(30.0) # Timeout maior para arquivos grandes
        s.connect((host, port))
        return s

    def get_file_hash(self, file_path):
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def receive_full_message(self, sock):
        data = b""
        while True:
            try:
                part = sock.recv(65536)
                if not part:
                    break
                data += part
                if data.strip().endswith(b"}"):
                    break
            except socket.timeout:
                break
        return data

    def list_files(self):
        try:
            s = self.get_socket()
            req = {"cmd": "list_req"}
            s.sendall(json.dumps(req).encode("utf-8"))
            
            data = self.receive_full_message(s)
            resp = json.loads(data.decode("utf-8"))
            
            if resp.get("cmd") == "list_resp":
                self.file_listbox.delete(0, tk.END)
                for f in resp.get("files", []):
                    self.file_listbox.insert(tk.END, f)
            s.close()
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao listar arquivos: {e}")

    def upload_file(self):
        file_path = filedialog.askopenfilename()
        if not file_path:
            return
        
        file_name = os.path.basename(file_path)
        file_hash = self.get_file_hash(file_path)
        
        with open(file_path, "rb") as f:
            file_bytes = f.read()
            file_data_b64 = base64.b64encode(file_bytes).decode("utf-8")
            
        try:
            s = self.get_socket()
            req = {
                "cmd": "put_req",
                "file": file_name,
                "hash": file_hash,
                "value": file_data_b64
            }
            s.sendall(json.dumps(req).encode("utf-8"))
            
            data = self.receive_full_message(s)
            resp = json.loads(data.decode("utf-8"))
            
            if resp.get("status") == "ok":
                messagebox.showinfo("Sucesso", f"Upload de {file_name} concluído!")
                self.list_files()
            else:
                messagebox.showerror("Erro", f"Falha no upload: Inconsistência de Hash!")
            s.close()
        except Exception as e:
            messagebox.showerror("Erro", f"Erro no upload: {e}")

    def download_file(self):
        selected = self.file_listbox.curselection()
        if not selected:
            messagebox.showwarning("Aviso", "Selecione um arquivo!")
            return
        
        file_name = self.file_listbox.get(selected[0])
        save_path = filedialog.asksaveasfilename(initialfile=file_name)
        if not save_path:
            return
            
        try:
            s = self.get_socket()
            req = {"cmd": "get_req", "file": file_name}
            s.sendall(json.dumps(req).encode("utf-8"))
            
            data = self.receive_full_message(s)
            resp = json.loads(data.decode("utf-8"))
            
            if resp.get("cmd") == "get_resp" and "value" in resp:
                file_data_b64 = resp.get("value")
                received_hash = resp.get("hash")
                file_bytes = base64.b64decode(file_data_b64)
                
                with open(save_path, "wb") as f:
                    f.write(file_bytes)
                
                calculated_hash = self.get_file_hash(save_path)
                if calculated_hash == received_hash:
                    messagebox.showinfo("Sucesso", f"Download de {file_name} concluído!")
                else:
                    messagebox.showerror("Erro", "Erro no download: Inconsistência de Hash!")
                    os.remove(save_path)
            else:
                messagebox.showerror("Erro", "Arquivo não encontrado ou erro no servidor.")
            s.close()
        except Exception as e:
            messagebox.showerror("Erro", f"Erro no download: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = TCPClientGUI(root)
    root.mainloop()
