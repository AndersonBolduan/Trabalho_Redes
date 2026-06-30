"""
AV3 - Parte 3: Servidor de Monitoramento e Controle (Filial)
Disciplina: Redes de Computadores I (RCA) - IFSC Campus Lages
Professor: Robson Costa | 2026/1

Descrição:
    Servidor UDP que simula uma filial com sensores e atuadores.
    Carrega configuração de um arquivo JSON e responde aos comandos
    do cliente (matriz) via protocolo UDP com payload JSON/UTF-8.

Uso:
    python servidor.py <arquivo_config.json>
    Exemplo: python servidor.py config_filial1.json
"""

import socket
import json
import sys
import os
import threading
import random
from datetime import datetime


class ServidorFilial:
    """
    Servidor UDP que gerencia sensores e atuadores de uma filial.
    
    Atributos:
        config (dict): Configuração carregada do arquivo JSON.
        port (int): Porta UDP na qual o servidor escuta.
        admin_user (str): Usuário para autenticação.
        admin_pass (str): Senha para autenticação.
        filial_name (str): Nome identificador da filial.
        dispositivos (dict): Dicionário com os estados atuais dos dispositivos.
        sessoes_autenticadas (set): Conjunto de endereços (ip, porta) autenticados.
    """

    def __init__(self, config_path: str):
        """
        Inicializa o servidor carregando a configuração do arquivo JSON.
        
        Args:
            config_path: Caminho para o arquivo de configuração JSON.
        """
        # Carregar configuração
        if not os.path.isfile(config_path):
            print(f"[ERRO] Arquivo de configuração não encontrado: {config_path}")
            sys.exit(1)

        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)

        self.port = self.config.get("port", 51000)
        self.admin_user = self.config.get("admin_user", "admin")
        self.admin_pass = self.config.get("admin_pass", "admin")
        self.filial_name = self.config.get("filial_name", "Filial Desconhecida")
        ids_list = self.config.get("id", [])

        # Inicializar estados dos dispositivos
        # Sensores e atuadores começam com valores aleatórios (simulação)
        self.dispositivos = {}
        for device_id in ids_list:
            # Todos os dispositivos são booleanos conforme enunciado
            self.dispositivos[device_id] = random.choice([True, False])

        # Sessões autenticadas: armazena tuplas (ip, porta) dos clientes autenticados
        self.sessoes_autenticadas = set()

        # Lock para acesso thread-safe aos dispositivos
        self.lock = threading.Lock()

        # Socket UDP
        self.socket = None
        self.running = False

    def iniciar(self):
        """Inicia o servidor UDP e começa a escutar requisições."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(('0.0.0.0', self.port))
            self.running = True

            print("=" * 60)
            print(f"  SERVIDOR DE MONITORAMENTO/CONTROLE - UDP")
            print(f"  Filial: {self.filial_name}")
            print(f"  Porta: {self.port}")
            print(f"  Usuário: {self.admin_user}")
            print(f"  Dispositivos cadastrados: {len(self.dispositivos)}")
            print("=" * 60)
            print()
            self._listar_dispositivos_console()
            print("\n  Aguardando requisições...\n")

            while self.running:
                try:
                    # Receber dados (buffer de 65535 bytes - máximo UDP)
                    data, addr = self.socket.recvfrom(65535)
                    # Processar em thread separada para não bloquear
                    threading.Thread(
                        target=self._processar_requisicao,
                        args=(data, addr),
                        daemon=True
                    ).start()
                except socket.error:
                    if self.running:
                        continue
                    break

        except OSError as e:
            print(f"[ERRO] Não foi possível iniciar o servidor: {e}")
            sys.exit(1)
        except KeyboardInterrupt:
            print("\n[INFO] Servidor encerrado pelo usuário.")
        finally:
            self.running = False
            if self.socket:
                self.socket.close()

    def _listar_dispositivos_console(self):
        """Exibe no console a lista de dispositivos e seus estados atuais."""
        print("  Dispositivos registrados:")
        print("  " + "-" * 56)
        print(f"  {'ID':<40} {'TIPO':<10} {'VALOR'}")
        print("  " + "-" * 56)
        for dev_id, valor in self.dispositivos.items():
            tipo = "SENSOR" if dev_id.startswith("sensor_") else "ATUADOR"
            estado = "LIGADO" if valor else "DESLIGADO"
            print(f"  {dev_id:<40} {tipo:<10} {estado}")
        print("  " + "-" * 56)

    def _enviar_resposta(self, resposta: dict, addr: tuple):
        """
        Serializa e envia uma resposta JSON via UDP para o endereço do cliente.
        
        Args:
            resposta: Dicionário com a resposta a ser enviada.
            addr: Tupla (ip, porta) do destinatário.
        """
        try:
            data = json.dumps(resposta, ensure_ascii=False).encode('utf-8')
            self.socket.sendto(data, addr)
        except Exception as e:
            print(f"  [ERRO] Falha ao enviar resposta para {addr}: {e}")

    def _processar_requisicao(self, data: bytes, addr: tuple):
        """
        Processa uma requisição recebida de um cliente.
        
        Fluxo:
            1. Decodifica o JSON recebido.
            2. Verifica se o comando requer autenticação.
            3. Executa o comando correspondente.
            4. Envia a resposta ao cliente.
        
        Args:
            data: Bytes recebidos do socket.
            addr: Tupla (ip, porta) do remetente.
        """
        timestamp = datetime.now().strftime("%H:%M:%S")

        try:
            # Decodificar JSON
            mensagem = json.loads(data.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f"  [{timestamp}] {addr} -> ERRO: payload inválido ({e})")
            self._enviar_resposta({"cmd": "error", "message": "Payload JSON inválido"}, addr)
            return

        cmd = mensagem.get("cmd", "")
        print(f"  [{timestamp}] {addr} -> CMD: {cmd}")

        # Comando de autenticação (login)
        if cmd == "auth_req":
            self._cmd_auth(mensagem, addr)
            return

        # Todos os outros comandos requerem autenticação
        if addr not in self.sessoes_autenticadas:
            print(f"  [{timestamp}] {addr} -> NEGADO: não autenticado")
            self._enviar_resposta({
                "cmd": "error",
                "message": "Não autenticado. Envie auth_req primeiro."
            }, addr)
            return

        # Roteamento de comandos
        if cmd == "list_req":
            self._cmd_list(addr)
        elif cmd == "get_status":
            self._cmd_get_status(addr)
        elif cmd == "set_req":
            self._cmd_set(mensagem, addr)
        else:
            self._enviar_resposta({
                "cmd": "error",
                "message": f"Comando desconhecido: {cmd}"
            }, addr)

    def _cmd_auth(self, mensagem: dict, addr: tuple):
        """
        Processa o comando de autenticação.
        
        O cliente envia usuário e senha. Se corretos, o endereço é
        adicionado ao conjunto de sessões autenticadas.
        
        Protocolo:
            Requisição: {"cmd": "auth_req", "user": "<usuario>", "pass": "<senha>"}
            Resposta OK: {"cmd": "auth_resp", "status": "ok", "filial": "<nome>"}
            Resposta FAIL: {"cmd": "auth_resp", "status": "fail", "message": "..."}
        """
        user = mensagem.get("user", "")
        password = mensagem.get("pass", "")

        if user == self.admin_user and password == self.admin_pass:
            self.sessoes_autenticadas.add(addr)
            print(f"    -> Autenticação OK para {addr}")
            self._enviar_resposta({
                "cmd": "auth_resp",
                "status": "ok",
                "filial": self.filial_name
            }, addr)
        else:
            print(f"    -> Autenticação FALHOU para {addr} (user={user})")
            self._enviar_resposta({
                "cmd": "auth_resp",
                "status": "fail",
                "message": "Usuário ou senha incorretos."
            }, addr)

    def _cmd_list(self, addr: tuple):
        """
        Processa o comando LIST - retorna a lista de sensores e atuadores.
        
        Protocolo:
            Requisição: {"cmd": "list_req"}
            Resposta: {"cmd": "list_resp", "id": ["sensor_light_sala", ...]}
        """
        with self.lock:
            ids = list(self.dispositivos.keys())

        self._enviar_resposta({
            "cmd": "list_resp",
            "id": ids
        }, addr)
        print(f"    -> LIST: {len(ids)} dispositivo(s) enviado(s)")

    def _cmd_get_status(self, addr: tuple):
        """
        Processa o comando GET - retorna o estado atual de todos os dispositivos.
        
        Protocolo:
            Requisição: {"cmd": "get_status"}
            Resposta: {"cmd": "get_resp", "<id1>": <value1>, "<id2>": <value2>, ...}
        """
        with self.lock:
            resposta = {"cmd": "get_resp"}
            for dev_id, valor in self.dispositivos.items():
                resposta[dev_id] = valor

        self._enviar_resposta(resposta, addr)
        print(f"    -> GET_STATUS: estados enviados")

    def _cmd_set(self, mensagem: dict, addr: tuple):
        """
        Processa o comando SET - altera o estado de um atuador.
        
        Regras:
            - Somente IDs do tipo 'actuator' podem ser alterados.
            - IDs do tipo 'sensor' são somente leitura.
        
        Protocolo:
            Requisição: {"cmd": "set_req", "id": "<id_name>", "value": <new_value>}
            Resposta OK: {"cmd": "set_resp", "id": "<id_name>", "value": <new_value>}
            Resposta FAIL: {"cmd": "set_resp", "id": "<id_name>", "status": "fail", "message": "..."}
        """
        dev_id = mensagem.get("id", "")
        new_value = mensagem.get("value", None)

        # Verificar se o ID existe
        if dev_id not in self.dispositivos:
            self._enviar_resposta({
                "cmd": "set_resp",
                "id": dev_id,
                "status": "fail",
                "message": f"Dispositivo '{dev_id}' não encontrado."
            }, addr)
            print(f"    -> SET FAIL: '{dev_id}' não existe")
            return

        # Verificar se é um atuador (somente atuadores podem ser alterados)
        if not dev_id.startswith("actuator_"):
            self._enviar_resposta({
                "cmd": "set_resp",
                "id": dev_id,
                "status": "fail",
                "message": f"'{dev_id}' é um sensor (somente leitura)."
            }, addr)
            print(f"    -> SET FAIL: '{dev_id}' é sensor (read-only)")
            return

        # Converter valor para booleano
        if isinstance(new_value, bool):
            valor_bool = new_value
        elif isinstance(new_value, str):
            valor_bool = new_value.lower() in ("true", "1", "on", "ligado")
        elif isinstance(new_value, (int, float)):
            valor_bool = bool(new_value)
        else:
            valor_bool = False

        # Atualizar o estado do atuador
        with self.lock:
            self.dispositivos[dev_id] = valor_bool
            # Atualizar também o sensor correspondente (sincronizar)
            # Ex: actuator_light_sala -> sensor_light_sala
            sensor_id = dev_id.replace("actuator_", "sensor_", 1)
            if sensor_id in self.dispositivos:
                self.dispositivos[sensor_id] = valor_bool

        self._enviar_resposta({
            "cmd": "set_resp",
            "id": dev_id,
            "value": valor_bool
        }, addr)
        estado = "LIGADO" if valor_bool else "DESLIGADO"
        print(f"    -> SET OK: '{dev_id}' = {estado}")


def main():
    """Função principal - carrega configuração e inicia o servidor."""
    if len(sys.argv) < 2:
        print("Uso: python servidor.py <arquivo_config.json>")
        print("Exemplo: python servidor.py config_filial1.json")
        sys.exit(1)

    config_path = sys.argv[1]

    # Se o caminho não é absoluto, procurar no diretório do script
    if not os.path.isabs(config_path):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(script_dir, config_path)

    servidor = ServidorFilial(config_path)
    servidor.iniciar()


if __name__ == "__main__":
    main()
