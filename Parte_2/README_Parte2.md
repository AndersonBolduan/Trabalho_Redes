# Servidor e Cliente de Arquivos TCP (Parte 2 - AV3) - Versão Corrigida

Esta é a implementação da Parte 2 do trabalho de Redes de Computadores I, que consiste em um servidor e um cliente de arquivos baseados no protocolo TCP, utilizando um protocolo de aplicação customizado em formato JSON.

**Esta versão inclui correções para o erro `WinError 10054` que ocorria ao tentar fazer upload de arquivos grandes (como PDFs), garantindo um tratamento mais robusto de mensagens JSON extensas.**

## Requisitos

*   **Python 3.x**
*   **tkinter** (para a interface gráfica do cliente)

## Estrutura dos Arquivos

*   `tcp_server.py`: Código-fonte do servidor TCP (atualizado).
*   `tcp_client.py`: Código-fonte do cliente TCP com interface gráfica (atualizado).
*   `server_storage/`: Diretório criado automaticamente pelo servidor para armazenar os arquivos enviados.

## Como Executar

### 1. Iniciando o Servidor

O servidor deve ser iniciado primeiro. Ele não possui interface gráfica e roda diretamente no terminal.

1.  Abra um terminal ou prompt de comando.
2.  Navegue até o diretório onde os arquivos estão salvos.
3.  Execute o comando:
    ```bash
    python tcp_server.py
    ```
    *(O servidor ficará aguardando conexões na porta 6000)*

### 2. Iniciando o Cliente

Com o servidor rodando, você pode iniciar um ou mais clientes.

1.  Abra um **novo** terminal ou prompt de comando.
2.  Navegue até o diretório onde os arquivos estão salvos.
3.  Execute o comando:
    ```bash
    python tcp_client.py
    ```

## Funcionalidades da Interface do Cliente

*   **Conexão**: Permite definir o IP e a porta do servidor (padrão: `127.0.0.1` e `6000`).
*   **Listar Arquivos**: Solicita ao servidor a lista de arquivos disponíveis e a exibe na tela.
*   **Fazer Upload**: Abre uma janela para selecionar um arquivo do seu computador e o envia para o servidor. O arquivo será salvo na pasta `server_storage`.
*   **Fazer Download**: Selecione um arquivo na lista exibida e clique neste botão para baixá-lo. Você poderá escolher onde salvar o arquivo no seu computador.

## Detalhes Técnicos Implementados (Atualizações)

*   **Protocolo TCP**: A comunicação é feita via TCP, garantindo a entrega ordenada e confiável dos dados, conforme ensinado na Unidade 5.
*   **Tratamento Robusto de Mensagens Grandes**: A lógica de recebimento de dados tanto no cliente quanto no servidor foi aprimorada para ler o fluxo de bytes do socket até que uma mensagem JSON completa seja detectada. Isso resolve o problema de `WinError 10054` ao lidar com arquivos grandes que, quando codificados em Base64 e inseridos no JSON, excedem o buffer de leitura inicial.
*   **Formato JSON**: Todas as requisições e respostas seguem rigorosamente o layout JSON especificado no documento AV3.
*   **Hash SHA-256**: A integridade dos arquivos é verificada usando o algoritmo SHA-256. Se houver inconsistência no hash durante o upload ou download, uma mensagem de erro é exibida e o arquivo corrompido é descartado.
*   **Base64**: O conteúdo binário dos arquivos é codificado em Base64 para ser transmitido com segurança dentro do payload JSON.

---
Desenvolvido por Manus AI para fins acadêmicos.
