# Parte 2 — Transferência de Arquivos com TCP

Esta pasta contém a implementação da **Parte 2** do trabalho de Redes de Computadores. A aplicação é formada por dois programas: um **servidor TCP**, responsável por armazenar e enviar arquivos, e um **cliente com interface gráfica**, responsável por listar, enviar e baixar arquivos.

Nesta versão de teste, a **descoberta automática por UDP foi removida**. A conexão ficou propositalmente mais simples: o cliente se conecta manualmente ao servidor usando **IP e porta**. O endereço padrão configurado no cliente é:

```text
192.168.56.1:50000
```

## Arquivos

| Arquivo | Função |
|---|---|
| `tcp_server.py` | Programa servidor. Deve ficar aberto no computador que receberá os arquivos. |
| `tcp_client.py` | Programa cliente com interface gráfica. Conecta manualmente no IP e porta informados. |
| `server_storage/` | Pasta criada automaticamente pelo servidor para armazenar os arquivos enviados. |

## Como testar no mesmo computador

Para testar no próprio computador, abra dois terminais no VSCode.

No primeiro terminal, execute o servidor:

```bash
python tcp_server.py
```

No segundo terminal, execute o cliente:

```bash
python tcp_client.py
```

Se o teste for no mesmo computador, altere temporariamente o campo **IP do Servidor** no cliente para:

```text
127.0.0.1
```

Depois clique em **Testar Conexão TCP**. Se aparecer uma mensagem de sucesso, o cliente e o servidor estão conversando corretamente.

## Como testar usando o IP solicitado

Para o teste entre computadores, deixe o servidor rodando no computador que possui o IP `192.168.56.1`.

No computador servidor, execute:

```bash
python tcp_server.py
```

O servidor escuta em `0.0.0.0:50000`. Isso significa que ele aceita conexões TCP destinadas às interfaces de rede disponíveis na máquina, incluindo a interface cujo IP seja `192.168.56.1`, caso ela exista no computador.

No outro computador, execute:

```bash
python tcp_client.py
```

O cliente já abrirá com estes valores preenchidos:

| Campo | Valor padrão |
|---|---|
| IP do Servidor | `192.168.56.1` |
| Porta | `50000` |

O primeiro botão que deve ser usado é **Testar Conexão TCP**. Se esse teste funcionar, então **Listar Arquivos**, **Fazer Upload** e **Fazer Download** também passam a usar a mesma conexão manual.

## O que foi removido nesta versão

| Recurso removido | Motivo |
|---|---|
| Botão **Localizar Servidor** | Evitar dependência de broadcast UDP durante os testes. |
| Resposta UDP no servidor | Deixar o servidor trabalhando apenas com TCP. |
| Diagnóstico de broadcast | O teste agora é direto por IP e porta. |

A ideia desta versão é eliminar uma variável do problema. Antes, se a localização automática falhasse, poderia haver dúvida se o problema estava no UDP, no broadcast, no IP, no TCP ou no firewall. Agora o teste fica mais objetivo: **ou a conexão TCP chega em `192.168.56.1:50000`, ou não chega**.

## Como interpretar o resultado

| Resultado | Interpretação provável |
|---|---|
| O botão **Testar Conexão TCP** mostra sucesso. | O cliente conseguiu chegar ao servidor pelo IP e porta informados. |
| O terminal do servidor mostra `[TCP] Conexão aceita`. | A tentativa de conexão chegou ao servidor. |
| O cliente falha e o terminal do servidor não mostra nada. | A tentativa não chegou ao servidor. Verifique se `192.168.56.1` é realmente o IP do computador servidor. |
| O erro diz “conexão recusada”. | O IP respondeu, mas não há servidor ouvindo na porta informada. Confira se `tcp_server.py` está aberto. |
| O erro diz “tempo esgotado”. | O pacote não teve resposta. Pode ser IP incorreto, rota de rede ou bloqueio de entrada. |

## Protocolo usado

A aplicação continua usando o protocolo TCP. Cada mensagem possui um cabeçalho de 8 bytes com o tamanho do JSON, seguido pelo JSON codificado em UTF-8. Esse detalhe evita problemas quando arquivos grandes são enviados, porque o programa sabe exatamente quantos bytes precisa receber antes de processar a mensagem.

| Comando | Quem envia | Finalidade |
|---|---|---|
| `test_req` | Cliente | Testar a conexão TCP manual. |
| `test_resp` | Servidor | Confirmar que a conexão chegou ao servidor. |
| `list_req` | Cliente | Solicitar a lista de arquivos armazenados. |
| `list_resp` | Servidor | Retornar a lista de arquivos. |
| `put_req` | Cliente | Enviar arquivo em Base64 com hash SHA-256. |
| `put_resp` | Servidor | Confirmar ou rejeitar o upload. |
| `get_req` | Cliente | Solicitar download de um arquivo. |
| `get_resp` | Servidor | Enviar o arquivo solicitado em Base64 com hash SHA-256. |

## Observação para apresentação

Se perguntarem por que a descoberta UDP foi removida, a resposta é simples: **foi uma escolha temporária para teste e diagnóstico**. Como a Parte 2 exige comunicação TCP para a transferência de arquivos, o foco desta versão é validar diretamente se dois computadores conseguem estabelecer conexão TCP usando um endereço conhecido, neste caso `192.168.56.1:50000`.

---

Autor: **Manus AI**
