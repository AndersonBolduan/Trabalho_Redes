import socket
import struct
import threading
import json
import tkinter as tk
from tkinter import messagebox, scrolledtext
from datetime import datetime

class MulticastChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Multicast Chat - Trabalho Acadêmico")
        self.root.geometry("600x550")

        # Variáveis de estado
        self.socket = None
        self.receive_thread = None
        self.running = False
        self.current_group = None
        self.current_port = None
        self.username = ""

        self.setup_ui()

    def setup_ui(self):
        # Frame de Configuração
        config_frame = tk.LabelFrame(self.root, text="Configurações de Conexão", padx=10, pady=10)
        config_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(config_frame, text="Nome de Usuário:").grid(row=0, column=0, sticky="w")
        self.ent_username = tk.Entry(config_frame)
        self.ent_username.grid(row=0, column=1, padx=5, pady=2, sticky="ew")
        self.ent_username.insert(0, "Estudante")

        tk.Label(config_frame, text="Grupo Multicast (IP):").grid(row=1, column=0, sticky="w")
        self.ent_group = tk.Entry(config_frame)
        self.ent_group.grid(row=1, column=1, padx=5, pady=2, sticky="ew")
        self.ent_group.insert(0, "224.1.1.1")

        tk.Label(config_frame, text="Porta de Comunicação:").grid(row=2, column=0, sticky="w")
        self.ent_port = tk.Entry(config_frame)
        self.ent_port.grid(row=2, column=1, padx=5, pady=2, sticky="ew")
        self.ent_port.insert(0, "5000")

        self.btn_connect = tk.Button(config_frame, text="ENTRAR NO GRUPO", command=self.toggle_connection, 
                                     bg="#28a745", fg="white", font=("Arial", 9, "bold"))
        self.btn_connect.grid(row=0, column=2, rowspan=3, padx=10, sticky="nsew")

        config_frame.columnconfigure(1, weight=1)

        # Área de Chat
        chat_frame = tk.LabelFrame(self.root, text="Histórico de Mensagens", padx=10, pady=10)
        chat_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.chat_area = scrolledtext.ScrolledText(chat_frame, state='disabled', wrap='word', font=("Consolas", 10))
        self.chat_area.pack(fill="both", expand=True)

        # Envio de Mensagem
        send_frame = tk.LabelFrame(self.root, text="Enviar Mensagem", padx=10, pady=10)
        send_frame.pack(fill="x", padx=10, pady=5)

        self.ent_message = tk.Entry(send_frame, font=("Arial", 10))
        self.ent_message.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.ent_message.bind("<Return>", lambda e: self.send_message())
        self.ent_message.config(state="disabled")

        self.btn_send = tk.Button(send_frame, text="ENVIAR", command=self.send_message, 
                                  state="disabled", bg="#007bff", fg="white", width=10)
        self.btn_send.pack(side="right")

    def log(self, message):
        self.chat_area.configure(state='normal')
        self.chat_area.insert(tk.END, message + "\n")
        self.chat_area.configure(state='disabled')
        self.chat_area.see(tk.END)

    def toggle_connection(self):
        if not self.running:
            self.start_chat()
        else:
            self.stop_chat()

    def start_chat(self):
        group = self.ent_group.get().strip()
        port_str = self.ent_port.get().strip()
        self.username = self.ent_username.get().strip()

        if not group or not port_str or not self.username:
            messagebox.showwarning("Aviso", "Por favor, preencha todos os campos de configuração!")
            return

        try:
            port = int(port_str)
        except ValueError:
            messagebox.showerror("Erro", "A porta deve ser um valor numérico!")
            return

        try:
            # Criar socket UDP para Multicast
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            
            # Permitir reuso de endereço
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # No Windows, bind na porta específica
            self.socket.bind(('', port))

            # Configurar para entrar no grupo multicast
            mreq = struct.pack("4sl", socket.inet_aton(group), socket.INADDR_ANY)
            self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            
            # Definir TTL (Time To Live) para 2 (alcance da rede local)
            self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
            
            # Opcional: Desativar loopback se não quiser receber as próprias mensagens
            # self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)

            self.current_group = group
            self.current_port = port
            self.running = True
            
            # Iniciar thread de recebimento (Thread distinta conforme requisito)
            self.receive_thread = threading.Thread(target=self.receive_loop, daemon=True)
            self.receive_thread.start()

            # Atualizar Interface
            self.btn_connect.config(text="SAIR DO GRUPO", bg="#dc3545")
            self.btn_send.config(state="normal")
            self.ent_message.config(state="normal")
            self.ent_group.config(state="disabled")
            self.ent_port.config(state="disabled")
            self.ent_username.config(state="disabled")
            self.ent_message.focus_set()
            
            self.log(f"--- Conectado ao grupo {group}:{port} como '{self.username}' ---")

        except Exception as e:
            messagebox.showerror("Erro de Socket", f"Falha ao configurar multicast: {e}")
            self.stop_chat()

    def stop_chat(self):
        self.running = False
        if self.socket:
            try:
                # Sair do grupo multicast
                mreq = struct.pack("4sl", socket.inet_aton(self.current_group), socket.INADDR_ANY)
                self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_DROP_MEMBERSHIP, mreq)
                self.socket.close()
            except:
                pass
            self.socket = None
        
        # Restaurar Interface
        self.btn_connect.config(text="ENTRAR NO GRUPO", bg="#28a745")
        self.btn_send.config(state="disabled")
        self.ent_message.config(state="disabled")
        self.ent_group.config(state="normal")
        self.ent_port.config(state="normal")
        self.ent_username.config(state="normal")
        self.log("--- Desconectado do grupo ---")

    def send_message(self):
        msg_text = self.ent_message.get().strip()
        if not msg_text or not self.running or not self.socket:
            return

        # Obter data e hora local conforme requisito
        now = datetime.now()
        
        # Criar payload JSON conforme layout rigoroso solicitado
        payload = {
            "date": now.strftime("%d/%m/%Y"),
            "time": now.strftime("%H:%M:%S"),
            "username": self.username,
            "message": msg_text
        }

        try:
            # Codificação UTF-8 rigorosa
            json_data = json.dumps(payload).encode('utf-8')
            
            # Enviar para o grupo multicast
            self.socket.sendto(json_data, (self.current_group, self.current_port))
            
            # Limpar campo de entrada
            self.ent_message.delete(0, tk.END)
        except Exception as e:
            messagebox.showerror("Erro de Envio", f"Não foi possível enviar a mensagem: {e}")

    def receive_loop(self):
        """Thread dedicada para recebimento de mensagens"""
        while self.running:
            try:
                # Receber dados do socket
                data, addr = self.socket.recvfrom(4096)
                if not data:
                    break
                
                # Tentar decodificar o JSON recebido
                try:
                    payload = json.loads(data.decode('utf-8'))
                    
                    # Extrair campos conforme o layout definido
                    msg_time = payload.get('time', '??:??:??')
                    msg_user = payload.get('username', 'Desconhecido')
                    msg_content = payload.get('message', '')
                    
                    formatted_msg = f"[{msg_time}] {msg_user}: {msg_content}"
                    
                    # Atualizar a GUI a partir da thread (usando after para thread-safety)
                    self.root.after(0, lambda m=formatted_msg: self.log(m))
                    
                except (json.JSONDecodeError, UnicodeDecodeError):
                    # Lidar com dados que não estão no formato esperado
                    raw_data = data.decode('utf-8', errors='replace')
                    self.root.after(0, lambda d=raw_data: self.log(f"Recebido (Formato Inválido): {d}"))
            except Exception:
                # Ocorre quando o socket é fechado ou a aplicação é encerrada
                break

if __name__ == "__main__":
    root = tk.Tk()
    # Centralizar janela na tela (opcional)
    root.eval('tk::PlaceWindow . center')
    app = MulticastChatApp(root)
    root.mainloop()
