"""
AV3 - Parte 3: Cliente de Monitoramento e Controle (Matriz)
Disciplina: Redes de Computadores I (RCA) - IFSC Campus Lages
Professor: Robson Costa | 2026/1

Descrição:
    Cliente com interface gráfica (GUI) que se conecta a múltiplos servidores
    de filiais via protocolo UDP. Permite listar dispositivos, obter estados,
    alterar atuadores e configurar polling periódico.

Uso:
    python cliente.py
"""

import socket
import json
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from datetime import datetime


class FilialConnection:
    """
    Representa uma conexão UDP com um servidor de filial.
    
    Cada instância mantém seu próprio socket UDP, informações de
    autenticação e estado dos dispositivos da filial correspondente.
    
    Atributos:
        ip (str): Endereço IP do servidor da filial.
        port (int): Porta UDP do servidor da filial.
        user (str): Usuário para autenticação.
        password (str): Senha para autenticação.
        filial_name (str): Nome da filial (obtido após autenticação).
        autenticado (bool): Se a conexão está autenticada.
        dispositivos (dict): Estados atuais dos dispositivos.
        socket (socket.socket): Socket UDP para comunicação.
    """

    def __init__(self, ip: str, port: int, user: str, password: str):
        self.ip = ip
        self.port = port
        self.user = user
        self.password = password
        self.filial_name = f"{ip}:{port}"
        self.autenticado = False
        self.dispositivos = {}
        self.ids_list = []
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(5.0)  # Timeout de 5 segundos para respostas

    def enviar(self, mensagem: dict) -> dict:
        """
        Envia uma mensagem JSON via UDP e aguarda a resposta.
        
        Este método implementa o padrão request-response sobre UDP:
        serializa o dicionário em JSON/UTF-8, envia ao servidor e
        aguarda a resposta dentro do timeout configurado.
        
        Args:
            mensagem: Dicionário com o comando a ser enviado.
            
        Returns:
            Dicionário com a resposta do servidor.
            
        Raises:
            socket.timeout: Se o servidor não responder dentro do timeout.
            Exception: Para outros erros de comunicação.
        """
        data = json.dumps(mensagem, ensure_ascii=False).encode('utf-8')
        self.socket.sendto(data, (self.ip, self.port))
        resp_data, _ = self.socket.recvfrom(65535)
        return json.loads(resp_data.decode('utf-8'))

    def autenticar(self) -> tuple:
        """
        Realiza autenticação no servidor da filial.
        
        Envia credenciais (usuário e senha) e verifica a resposta.
        
        Returns:
            Tupla (sucesso: bool, mensagem: str).
        """
        try:
            resposta = self.enviar({
                "cmd": "auth_req",
                "user": self.user,
                "pass": self.password
            })
            if resposta.get("status") == "ok":
                self.autenticado = True
                self.filial_name = resposta.get("filial", self.filial_name)
                return True, f"Autenticado em '{self.filial_name}'"
            else:
                return False, resposta.get("message", "Falha na autenticação")
        except socket.timeout:
            return False, "Timeout: servidor não respondeu"
        except Exception as e:
            return False, f"Erro: {e}"

    def listar_dispositivos(self) -> tuple:
        """
        Solicita a lista de dispositivos (sensores e atuadores) da filial.
        
        Returns:
            Tupla (sucesso: bool, lista_ids ou mensagem_erro).
        """
        try:
            resposta = self.enviar({"cmd": "list_req"})
            if resposta.get("cmd") == "list_resp":
                self.ids_list = resposta.get("id", [])
                return True, self.ids_list
            else:
                return False, resposta.get("message", "Resposta inesperada")
        except socket.timeout:
            return False, "Timeout: servidor não respondeu"
        except Exception as e:
            return False, f"Erro: {e}"

    def obter_estados(self) -> tuple:
        """
        Solicita o estado atual de todos os dispositivos da filial.
        
        Returns:
            Tupla (sucesso: bool, dicionário_estados ou mensagem_erro).
        """
        try:
            resposta = self.enviar({"cmd": "get_status"})
            if resposta.get("cmd") == "get_resp":
                # Remover a chave 'cmd' para ficar só com os dispositivos
                estados = {k: v for k, v in resposta.items() if k != "cmd"}
                self.dispositivos = estados
                return True, estados
            else:
                return False, resposta.get("message", "Resposta inesperada")
        except socket.timeout:
            return False, "Timeout: servidor não respondeu"
        except Exception as e:
            return False, f"Erro: {e}"

    def alterar_atuador(self, device_id: str, valor: bool) -> tuple:
        """
        Envia comando para alterar o estado de um atuador.
        
        Args:
            device_id: Identificador do atuador (ex: "actuator_light_sala").
            valor: Novo valor booleano (True = ligado, False = desligado).
            
        Returns:
            Tupla (sucesso: bool, mensagem: str).
        """
        try:
            resposta = self.enviar({
                "cmd": "set_req",
                "id": device_id,
                "value": valor
            })
            if resposta.get("cmd") == "set_resp":
                if "status" in resposta and resposta["status"] == "fail":
                    return False, resposta.get("message", "Falha ao alterar")
                new_val = resposta.get("value", valor)
                self.dispositivos[device_id] = new_val
                return True, f"'{device_id}' alterado para {'LIGADO' if new_val else 'DESLIGADO'}"
            else:
                return False, resposta.get("message", "Resposta inesperada")
        except socket.timeout:
            return False, "Timeout: servidor não respondeu"
        except Exception as e:
            return False, f"Erro: {e}"

    def fechar(self):
        """Fecha o socket UDP."""
        try:
            self.socket.close()
        except Exception:
            pass


class ClienteMatrizGUI:
    """
    Interface gráfica do cliente da matriz para monitoramento e controle.
    
    Permite ao usuário:
        - Adicionar múltiplas filiais (IP, porta, credenciais).
        - Conectar-se (autenticar) em cada filial.
        - Listar dispositivos de cada filial.
        - Visualizar estados atuais dos sensores e atuadores.
        - Alterar estados dos atuadores.
        - Configurar polling periódico para atualização automática.
    """

    def __init__(self, root):
        self.root = root
        self.root.title("Cliente Matriz - Monitoramento e Controle | AV3 Parte 3")
        self.root.geometry("950x700")
        self.root.minsize(800, 600)

        # Lista de conexões com filiais
        self.filiais = {}  # chave: "ip:porta" -> FilialConnection
        
        # Controle de polling periódico
        self.polling_ativo = False
        self.polling_intervalo = 5  # segundos
        self.polling_thread = None

        self._criar_interface()

    def _criar_interface(self):
        """Constrói todos os widgets da interface gráfica."""
        
        # ===== FRAME SUPERIOR: Configuração de Filial =====
        frame_config = ttk.LabelFrame(self.root, text="Adicionar Filial", padding=10)
        frame_config.pack(fill=tk.X, padx=10, pady=5)

        # Linha 1: IP e Porta
        ttk.Label(frame_config, text="IP do Servidor:").grid(row=0, column=0, sticky="w", padx=2)
        self.entry_ip = ttk.Entry(frame_config, width=16)
        self.entry_ip.insert(0, "127.0.0.1")
        self.entry_ip.grid(row=0, column=1, padx=4, pady=2)

        ttk.Label(frame_config, text="Porta:").grid(row=0, column=2, sticky="w", padx=2)
        self.entry_porta = ttk.Entry(frame_config, width=8)
        self.entry_porta.insert(0, "51000")
        self.entry_porta.grid(row=0, column=3, padx=4, pady=2)

        # Linha 1: Usuário e Senha
        ttk.Label(frame_config, text="Usuário:").grid(row=0, column=4, sticky="w", padx=2)
        self.entry_user = ttk.Entry(frame_config, width=12)
        self.entry_user.insert(0, "admin")
        self.entry_user.grid(row=0, column=5, padx=4, pady=2)

        ttk.Label(frame_config, text="Senha:").grid(row=0, column=6, sticky="w", padx=2)
        self.entry_pass = ttk.Entry(frame_config, width=12, show="*")
        self.entry_pass.insert(0, "admin123")
        self.entry_pass.grid(row=0, column=7, padx=4, pady=2)

        # Botão Conectar
        self.btn_conectar = ttk.Button(frame_config, text="Conectar Filial", command=self._conectar_filial)
        self.btn_conectar.grid(row=0, column=8, padx=8, pady=2)

        # ===== FRAME: Lista de Filiais Conectadas =====
        frame_filiais = ttk.LabelFrame(self.root, text="Filiais Conectadas", padding=10)
        frame_filiais.pack(fill=tk.X, padx=10, pady=5)

        # Combobox para selecionar filial
        ttk.Label(frame_filiais, text="Filial Ativa:").pack(side=tk.LEFT, padx=4)
        self.combo_filiais = ttk.Combobox(frame_filiais, state="readonly", width=40)
        self.combo_filiais.pack(side=tk.LEFT, padx=4)
        self.combo_filiais.bind("<<ComboboxSelected>>", self._on_filial_selecionada)

        # Botões de operação
        self.btn_listar = ttk.Button(frame_filiais, text="Listar Dispositivos",
                                     command=self._listar_dispositivos, state=tk.DISABLED)
        self.btn_listar.pack(side=tk.LEFT, padx=4)

        self.btn_atualizar = ttk.Button(frame_filiais, text="Atualizar Estados",
                                        command=self._atualizar_estados, state=tk.DISABLED)
        self.btn_atualizar.pack(side=tk.LEFT, padx=4)

        self.btn_desconectar = ttk.Button(frame_filiais, text="Desconectar",
                                          command=self._desconectar_filial, state=tk.DISABLED)
        self.btn_desconectar.pack(side=tk.LEFT, padx=4)

        # ===== FRAME: Polling Periódico =====
        frame_polling = ttk.LabelFrame(self.root, text="Obtenção Periódica de Dados", padding=10)
        frame_polling.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(frame_polling, text="Intervalo (segundos):").pack(side=tk.LEFT, padx=4)
        self.entry_intervalo = ttk.Entry(frame_polling, width=6)
        self.entry_intervalo.insert(0, "5")
        self.entry_intervalo.pack(side=tk.LEFT, padx=4)

        self.btn_polling = ttk.Button(frame_polling, text="Iniciar Polling",
                                      command=self._toggle_polling, state=tk.DISABLED)
        self.btn_polling.pack(side=tk.LEFT, padx=8)

        self.lbl_polling_status = ttk.Label(frame_polling, text="Polling: INATIVO", foreground="red")
        self.lbl_polling_status.pack(side=tk.LEFT, padx=8)

        # ===== FRAME CENTRAL: Tabela de Dispositivos =====
        frame_dispositivos = ttk.LabelFrame(self.root, text="Dispositivos - Estado Atual", padding=10)
        frame_dispositivos.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Treeview para exibir dispositivos
        colunas = ("filial", "id", "tipo", "dispositivo", "local", "estado", "acao")
        self.tree = ttk.Treeview(frame_dispositivos, columns=colunas, show="headings", height=12)
        
        self.tree.heading("filial", text="Filial")
        self.tree.heading("id", text="ID Completo")
        self.tree.heading("tipo", text="Tipo")
        self.tree.heading("dispositivo", text="Dispositivo")
        self.tree.heading("local", text="Local")
        self.tree.heading("estado", text="Estado")
        self.tree.heading("acao", text="Ação")

        self.tree.column("filial", width=120, anchor="center")
        self.tree.column("id", width=200, anchor="w")
        self.tree.column("tipo", width=80, anchor="center")
        self.tree.column("dispositivo", width=100, anchor="center")
        self.tree.column("local", width=120, anchor="center")
        self.tree.column("estado", width=80, anchor="center")
        self.tree.column("acao", width=100, anchor="center")

        # Scrollbar vertical
        scrollbar_v = ttk.Scrollbar(frame_dispositivos, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar_v.set)
        scrollbar_v.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)

        # Botão para alternar estado (duplo clique)
        self.tree.bind("<Double-1>", self._on_duplo_clique)

        # Frame para ação manual de SET
        frame_set = ttk.Frame(frame_dispositivos)
        frame_set.pack(fill=tk.X, pady=5)

        ttk.Label(frame_set, text="Alterar Atuador Selecionado:").pack(side=tk.LEFT, padx=4)
        self.btn_ligar = ttk.Button(frame_set, text="LIGAR", command=lambda: self._set_atuador(True))
        self.btn_ligar.pack(side=tk.LEFT, padx=4)
        self.btn_desligar = ttk.Button(frame_set, text="DESLIGAR", command=lambda: self._set_atuador(False))
        self.btn_desligar.pack(side=tk.LEFT, padx=4)

        # ===== FRAME INFERIOR: Log =====
        frame_log = ttk.LabelFrame(self.root, text="Log de Comunicação", padding=5)
        frame_log.pack(fill=tk.BOTH, expand=False, padx=10, pady=5)

        self.log_area = scrolledtext.ScrolledText(frame_log, height=8, font=("Consolas", 9),
                                                  state=tk.DISABLED, wrap=tk.WORD)
        self.log_area.pack(fill=tk.BOTH, expand=True)

    def _log(self, mensagem: str):
        """Adiciona uma mensagem ao log com timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_area.config(state=tk.NORMAL)
        self.log_area.insert(tk.END, f"[{timestamp}] {mensagem}\n")
        self.log_area.see(tk.END)
        self.log_area.config(state=tk.DISABLED)

    def _conectar_filial(self):
        """
        Conecta (autentica) em uma nova filial.
        
        Cria um objeto FilialConnection, tenta autenticar e, se bem-sucedido,
        adiciona a filial à lista de filiais conectadas.
        """
        ip = self.entry_ip.get().strip()
        porta_str = self.entry_porta.get().strip()
        user = self.entry_user.get().strip()
        senha = self.entry_pass.get().strip()

        if not ip or not porta_str or not user or not senha:
            messagebox.showwarning("Aviso", "Preencha todos os campos de conexão!")
            return

        try:
            porta = int(porta_str)
        except ValueError:
            messagebox.showerror("Erro", "Porta deve ser um número inteiro!")
            return

        chave = f"{ip}:{porta}"
        if chave in self.filiais:
            messagebox.showinfo("Info", f"Já conectado em {chave}")
            return

        self._log(f"Tentando conectar em {chave}...")

        # Criar conexão e autenticar em thread separada para não travar a GUI
        def _thread_conectar():
            conn = FilialConnection(ip, porta, user, senha)
            sucesso, msg = conn.autenticar()
            # Atualizar GUI na thread principal
            self.root.after(0, lambda: self._resultado_conexao(conn, chave, sucesso, msg))

        threading.Thread(target=_thread_conectar, daemon=True).start()

    def _resultado_conexao(self, conn: FilialConnection, chave: str, sucesso: bool, msg: str):
        """Callback executado na thread principal após tentativa de conexão."""
        if sucesso:
            self.filiais[chave] = conn
            self._log(f"CONECTADO: {msg}")
            self._atualizar_combo_filiais()
            # Habilitar botões
            self.btn_listar.config(state=tk.NORMAL)
            self.btn_atualizar.config(state=tk.NORMAL)
            self.btn_desconectar.config(state=tk.NORMAL)
            self.btn_polling.config(state=tk.NORMAL)
            # Selecionar automaticamente a filial recém-conectada
            self.combo_filiais.set(f"{conn.filial_name} ({chave})")
        else:
            self._log(f"FALHA ao conectar em {chave}: {msg}")
            messagebox.showerror("Erro de Conexão", f"Não foi possível conectar:\n{msg}")
            conn.fechar()

    def _atualizar_combo_filiais(self):
        """Atualiza a lista de filiais no combobox."""
        valores = [f"{conn.filial_name} ({chave})" for chave, conn in self.filiais.items()]
        self.combo_filiais['values'] = valores
        if valores and not self.combo_filiais.get():
            self.combo_filiais.current(0)

    def _get_filial_selecionada(self) -> FilialConnection:
        """Retorna o objeto FilialConnection da filial atualmente selecionada."""
        sel = self.combo_filiais.get()
        if not sel:
            return None
        # Extrair a chave (ip:porta) do texto do combobox
        # Formato: "Nome da Filial (ip:porta)"
        try:
            chave = sel.split("(")[-1].rstrip(")")
            return self.filiais.get(chave)
        except (IndexError, KeyError):
            return None

    def _on_filial_selecionada(self, event=None):
        """Callback quando o usuário seleciona uma filial no combobox."""
        self._atualizar_tabela()

    def _listar_dispositivos(self):
        """Solicita a lista de dispositivos da filial selecionada."""
        conn = self._get_filial_selecionada()
        if not conn:
            messagebox.showwarning("Aviso", "Selecione uma filial primeiro!")
            return

        def _thread_listar():
            sucesso, resultado = conn.listar_dispositivos()
            self.root.after(0, lambda: self._resultado_listar(conn, sucesso, resultado))

        threading.Thread(target=_thread_listar, daemon=True).start()

    def _resultado_listar(self, conn: FilialConnection, sucesso: bool, resultado):
        """Callback após listar dispositivos."""
        if sucesso:
            self._log(f"LIST [{conn.filial_name}]: {len(resultado)} dispositivo(s)")
            # Após listar, obter estados automaticamente
            self._atualizar_estados()
        else:
            self._log(f"ERRO LIST [{conn.filial_name}]: {resultado}")
            messagebox.showerror("Erro", f"Falha ao listar:\n{resultado}")

    def _atualizar_estados(self):
        """Solicita o estado atual de todos os dispositivos da filial selecionada."""
        conn = self._get_filial_selecionada()
        if not conn:
            messagebox.showwarning("Aviso", "Selecione uma filial primeiro!")
            return

        def _thread_get():
            sucesso, resultado = conn.obter_estados()
            self.root.after(0, lambda: self._resultado_get(conn, sucesso, resultado))

        threading.Thread(target=_thread_get, daemon=True).start()

    def _resultado_get(self, conn: FilialConnection, sucesso: bool, resultado):
        """Callback após obter estados."""
        if sucesso:
            self._log(f"GET_STATUS [{conn.filial_name}]: {len(resultado)} estado(s) recebido(s)")
            self._atualizar_tabela()
        else:
            self._log(f"ERRO GET [{conn.filial_name}]: {resultado}")

    def _atualizar_tabela(self):
        """Atualiza a Treeview com os estados de todos os dispositivos de todas as filiais."""
        # Limpar tabela
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Preencher com dados de todas as filiais
        for chave, conn in self.filiais.items():
            for dev_id, valor in conn.dispositivos.items():
                # Parsear o ID: <type>_<device>_<place>
                partes = dev_id.split("_", 2)
                if len(partes) >= 3:
                    tipo = partes[0].upper()  # SENSOR ou ACTUATOR
                    dispositivo = partes[1].upper()  # LIGHT ou AC
                    local = partes[2].replace("_", " ").title()
                else:
                    tipo = "?"
                    dispositivo = "?"
                    local = dev_id

                estado = "LIGADO" if valor else "DESLIGADO"
                acao = "Alterável" if dev_id.startswith("actuator_") else "Somente Leitura"

                # Tag para colorir
                tag = "ligado" if valor else "desligado"
                
                self.tree.insert("", tk.END, values=(
                    conn.filial_name, dev_id, tipo, dispositivo, local, estado, acao
                ), tags=(tag,))

        # Configurar cores das tags
        self.tree.tag_configure("ligado", background="#d4edda")
        self.tree.tag_configure("desligado", background="#f8d7da")

    def _on_duplo_clique(self, event):
        """Alterna o estado de um atuador ao dar duplo clique na linha."""
        item = self.tree.selection()
        if not item:
            return
        valores = self.tree.item(item[0], "values")
        dev_id = valores[1]  # Coluna 'id'
        estado_atual = valores[5]  # Coluna 'estado'

        if not dev_id.startswith("actuator_"):
            messagebox.showinfo("Info", "Sensores são somente leitura.\nApenas atuadores podem ser alterados.")
            return

        # Alternar: se está LIGADO, desligar; se DESLIGADO, ligar
        novo_valor = (estado_atual == "DESLIGADO")
        self._executar_set(dev_id, novo_valor)

    def _set_atuador(self, valor: bool):
        """Altera o estado do atuador selecionado na tabela."""
        item = self.tree.selection()
        if not item:
            messagebox.showwarning("Aviso", "Selecione um dispositivo na tabela!")
            return
        valores = self.tree.item(item[0], "values")
        dev_id = valores[1]

        if not dev_id.startswith("actuator_"):
            messagebox.showinfo("Info", "Sensores são somente leitura.\nApenas atuadores podem ser alterados.")
            return

        self._executar_set(dev_id, valor)

    def _executar_set(self, dev_id: str, valor: bool):
        """Executa o comando SET em thread separada."""
        conn = self._get_filial_selecionada()
        if not conn:
            messagebox.showwarning("Aviso", "Selecione uma filial primeiro!")
            return

        def _thread_set():
            sucesso, msg = conn.alterar_atuador(dev_id, valor)
            self.root.after(0, lambda: self._resultado_set(conn, sucesso, msg))

        threading.Thread(target=_thread_set, daemon=True).start()

    def _resultado_set(self, conn: FilialConnection, sucesso: bool, msg: str):
        """Callback após executar SET."""
        if sucesso:
            self._log(f"SET [{conn.filial_name}]: {msg}")
            self._atualizar_tabela()
        else:
            self._log(f"ERRO SET [{conn.filial_name}]: {msg}")
            messagebox.showerror("Erro", f"Falha ao alterar:\n{msg}")

    def _toggle_polling(self):
        """Inicia ou para o polling periódico."""
        if not self.polling_ativo:
            # Iniciar polling
            try:
                intervalo = int(self.entry_intervalo.get().strip())
                if intervalo < 1:
                    raise ValueError()
                self.polling_intervalo = intervalo
            except ValueError:
                messagebox.showerror("Erro", "Intervalo deve ser um número inteiro positivo (segundos)!")
                return

            self.polling_ativo = True
            self.btn_polling.config(text="Parar Polling")
            self.lbl_polling_status.config(text=f"Polling: ATIVO ({self.polling_intervalo}s)",
                                           foreground="green")
            self._log(f"Polling iniciado (intervalo: {self.polling_intervalo}s)")
            self._executar_polling()
        else:
            # Parar polling
            self.polling_ativo = False
            self.btn_polling.config(text="Iniciar Polling")
            self.lbl_polling_status.config(text="Polling: INATIVO", foreground="red")
            self._log("Polling parado.")

    def _executar_polling(self):
        """
        Executa uma rodada de polling: solicita estados de todas as filiais.
        Reagenda-se automaticamente enquanto o polling estiver ativo.
        """
        if not self.polling_ativo:
            return

        def _thread_polling():
            for chave, conn in list(self.filiais.items()):
                if not self.polling_ativo:
                    break
                try:
                    sucesso, resultado = conn.obter_estados()
                    if sucesso:
                        self.root.after(0, lambda c=conn, r=resultado:
                            self._log(f"POLL [{c.filial_name}]: {len(r)} estado(s) atualizados"))
                except Exception as e:
                    self.root.after(0, lambda c=conn, err=e:
                        self._log(f"POLL ERRO [{c.filial_name}]: {err}"))
            
            # Atualizar tabela após polling de todas as filiais
            self.root.after(0, self._atualizar_tabela)

        threading.Thread(target=_thread_polling, daemon=True).start()

        # Reagendar próxima execução
        if self.polling_ativo:
            self.root.after(self.polling_intervalo * 1000, self._executar_polling)

    def _desconectar_filial(self):
        """Desconecta a filial selecionada."""
        conn = self._get_filial_selecionada()
        if not conn:
            messagebox.showwarning("Aviso", "Selecione uma filial para desconectar!")
            return

        # Encontrar a chave
        chave_remover = None
        for chave, c in self.filiais.items():
            if c is conn:
                chave_remover = chave
                break

        if chave_remover:
            conn.fechar()
            del self.filiais[chave_remover]
            self._log(f"Desconectado de {conn.filial_name} ({chave_remover})")
            self._atualizar_combo_filiais()
            self._atualizar_tabela()

            if not self.filiais:
                self.btn_listar.config(state=tk.DISABLED)
                self.btn_atualizar.config(state=tk.DISABLED)
                self.btn_desconectar.config(state=tk.DISABLED)
                self.btn_polling.config(state=tk.DISABLED)
                if self.polling_ativo:
                    self._toggle_polling()

    def on_closing(self):
        """Encerra todas as conexões e fecha a aplicação."""
        self.polling_ativo = False
        for conn in self.filiais.values():
            conn.fechar()
        self.root.destroy()


def main():
    """Função principal - inicializa a GUI do cliente."""
    root = tk.Tk()
    app = ClienteMatrizGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
