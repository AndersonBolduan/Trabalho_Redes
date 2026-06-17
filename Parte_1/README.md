# Aplicação de Chat Multicast (Trabalho Acadêmico)

Esta é uma aplicação de chat com interface gráfica (GUI) desenvolvida em Python, utilizando a biblioteca `tkinter`, para comunicação via multicast UDP. Ela foi criada para atender aos requisitos de um trabalho acadêmico, permitindo que usuários em uma rede local se comuniquem em grupos multicast.

## Requisitos

Para rodar esta aplicação, você precisará ter instalado em seu sistema Windows:

*   **Python 3.x**: Certifique-se de que o Python esteja instalado e configurado nas variáveis de ambiente.
*   **tkinter**: Geralmente, o `tkinter` já vem incluído com a instalação padrão do Python. Caso contrário, você pode precisar instalá-lo. No Windows, ele costuma ser parte da instalação do Python. Em sistemas baseados em Debian/Ubuntu, pode ser instalado com `sudo apt-get install python3-tk`.
*   **VSCode (Opcional)**: Embora a aplicação rode diretamente, o VSCode é recomendado para desenvolvimento e execução.

## Como Executar

1.  **Salve o arquivo**: Salve o código Python (`multicast_chat.py`) em um diretório de sua preferência.

2.  **Abra o Terminal/Prompt de Comando**: Navegue até o diretório onde você salvou o arquivo `multicast_chat.py`.

    ```bash
    cd caminho/para/o/seu/diretorio
    ```

3.  **Execute a aplicação**: Utilize o interpretador Python para executar o script:

    ```bash
    python multicast_chat.py
    ```

    Ou, se você tiver várias versões do Python, especifique a versão 3:

    ```bash
    python3 multicast_chat.py
    ```

## Funcionalidades da Interface Gráfica

Ao iniciar a aplicação, você verá uma janela com as seguintes seções:

*   **Configurações de Conexão**:
    *   **Nome de Usuário**: Campo para definir o seu nome de usuário no chat. **Este campo agora é lido corretamente para o envio de mensagens.**
    *   **Grupo Multicast (IP)**: Campo para inserir o endereço IP do grupo multicast (ex: `224.1.1.1`).
    *   **Porta de Comunicação**: Campo para definir a porta de comunicação (ex: `5000`).
    *   **Botão "ENTRAR NO GRUPO" / "SAIR DO GRUPO"**: Inicia ou encerra a conexão com o grupo multicast especificado. A aplicação se comunica com apenas um grupo por vez. **O estado dos botões e campos agora é atualizado dinamicamente para refletir o status da conexão.**

*   **Histórico de Mensagens**: Uma área de texto onde as mensagens recebidas e enviadas serão exibidas. **Melhorias visuais foram aplicadas para melhor legibilidade.**

*   **Enviar Mensagem**:
    *   Um campo de texto para digitar sua mensagem. **Este campo agora é habilitado apenas quando conectado a um grupo e o envio de mensagens está funcional.**
    *   Um botão "ENVIAR" para enviar a mensagem ao grupo. Você também pode pressionar `Enter` para enviar. **O envio de mensagens foi corrigido e está totalmente funcional.**

## Formato da Mensagem (JSON)

Todas as mensagens enviadas seguem rigorosamente o formato JSON (codificação UTF-8):

```json
{
 "date":"dd/mm/aaaa",
 "time":"hh:mm:ss",
 "username":"nome_do_usuario",
 "message":"sua_mensagem"
}
```

## Observações Importantes

*   **Multicast**: A comunicação é realizada via protocolo UDP multicast. Certifique-se de que sua rede permite tráfego multicast.
*   **Threads**: O envio e recebimento de mensagens são tratados em threads distintas para permitir a operação simultânea sem bloquear a interface gráfica.
*   **Windows**: A aplicação foi projetada para rodar no VSCode em Windows, utilizando `tkinter` para a GUI.
*   **Melhorias**: Foram adicionadas validações de entrada, tratamento de erros mais robusto e feedback visual na interface para uma melhor experiência do usuário.

--- 

Desenvolvido por Manus AI para fins acadêmicos.
