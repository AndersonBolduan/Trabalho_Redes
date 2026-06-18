# Parte 2 — Transferência de Arquivos com TCP

Este projeto implementa a **Parte 2** do trabalho de Redes de Computadores. A solução possui dois programas: um **servidor TCP**, que armazena arquivos, e um **cliente com interface gráfica**, que permite listar, enviar e baixar arquivos.

A versão atual foi revisada para facilitar testes entre **dois computadores diferentes na mesma rede local**. Além da transferência de arquivos, o cliente agora possui botões de **Teste de Conexão TCP**, **Localização Automática do Servidor** e **Diagnóstico**, ajudando a identificar se o problema está no código, no IP, na porta, no firewall ou no isolamento da rede.

## Arquivos

| Arquivo | Função |
|---|---|
| `tcp_server.py` | Programa servidor. Deve ser executado no computador que receberá e armazenará os arquivos. |
| `tcp_client.py` | Programa cliente com interface gráfica. Deve ser executado no computador que enviará, listará ou baixará arquivos. |
| `README_Parte2.md` | Este guia de uso e diagnóstico. |

## Como executar no mesmo computador

Para testar tudo em uma única máquina, abra dois terminais no VSCode.

No primeiro terminal, execute o servidor:

```bash
python tcp_server.py
```

No segundo terminal, execute o cliente:

```bash
python tcp_client.py
```

No cliente, deixe o IP como `127.0.0.1` e a porta como `50000`. Clique em **Testar Conexão TCP**. Se aparecer a mensagem de sucesso, o cliente está conseguindo conversar com o servidor.

## Como executar entre dois computadores na mesma rede

No computador que será o **servidor**, execute:

```bash
python tcp_server.py
```

O terminal do servidor mostrará uma tela semelhante a esta:

```text
No cliente, use um dos endereços abaixo como IP do servidor:
  - 192.168.1.25:50000
```

No computador que será o **cliente**, execute:

```bash
python tcp_client.py
```

Na interface gráfica do cliente, digite o IPv4 mostrado no terminal do servidor, por exemplo `192.168.1.25`, mantendo a porta `50000`. Em seguida, clique em **Testar Conexão TCP**.

> **Atenção:** `127.0.0.1` só funciona quando cliente e servidor estão no mesmo computador. Entre computadores diferentes, sempre use o IPv4 real exibido no terminal do servidor.

## O que mudou nesta revisão

| Recurso | O que faz | Por que ajuda |
|---|---|---|
| Servidor escutando em `0.0.0.0` | Aceita conexões vindas de outras máquinas da rede. | Evita que o servidor fique preso somente ao próprio computador. |
| Porta padrão `50000` | Usa uma porta alta e menos associada a serviços do sistema. | Reduz conflitos com portas conhecidas. |
| Botão **Testar Conexão TCP** | Envia um comando `test_req` ao servidor e espera `test_resp`. | Confirma se a conexão TCP está funcionando antes de tentar upload/download. |
| Botão **Localizar Servidor** | Envia mensagens UDP de descoberta por broadcast. | Pode preencher o IP automaticamente quando a rede permite broadcast. |
| Botão **Diagnóstico** | Mostra IPs locais e destinos de broadcast testados. | Ajuda a explicar e investigar falhas em laboratório. |
| Cabeçalho de 8 bytes | Informa o tamanho exato de cada JSON transmitido. | Evita erro com arquivos grandes, pois o receptor sabe exatamente quantos bytes deve ler. |

## Interpretação dos testes

O ponto mais importante é observar o terminal do servidor enquanto o cliente tenta conectar.

| Situação observada | Significado provável | O que fazer |
|---|---|---|
| No cliente, `127.0.0.1` funciona no mesmo PC. | O código e o protocolo estão funcionando localmente. | Use esse teste apenas como validação inicial. |
| Ao clicar em **Localizar Servidor**, aparece `[UDP] Descoberta recebida` no servidor. | O broadcast UDP chegou ao servidor. | A descoberta automática deve funcionar ou está muito próxima de funcionar. |
| Ao clicar em **Testar Conexão TCP**, aparece `[TCP] Conexão aceita` no servidor. | A conexão TCP chegou ao servidor. | A comunicação entre computadores está funcionando. |
| O cliente falha e não aparece nada no terminal do servidor. | A tentativa nem chegou ao servidor. | Verifique IP, rede, isolamento Wi‑Fi ou bloqueio de entrada. |
| O cliente mostra “conexão recusada”. | O computador respondeu, mas não há servidor ouvindo naquela porta. | Confira se `tcp_server.py` está rodando e se a porta é a mesma. |
| O cliente mostra “tempo esgotado”. | A rede não entregou a tentativa ou a resposta foi bloqueada. | Use IP manual, confirme a mesma rede e teste outro computador como servidor. |

## Sobre o botão “Localizar Servidor”

A localização automática usa **broadcast UDP**. Em algumas redes Wi‑Fi de escolas, empresas ou laboratórios, o roteador pode bloquear broadcast entre clientes. Quando isso acontece, o botão **Localizar Servidor** pode falhar mesmo que o TCP funcione com IP manual.

Por isso, a ordem recomendada para teste é:

| Ordem | Ação |
|---|---|
| 1 | Rodar `tcp_server.py` no computador servidor. |
| 2 | Copiar o IPv4 exibido no terminal do servidor. |
| 3 | Digitar esse IPv4 manualmente no cliente. |
| 4 | Clicar em **Testar Conexão TCP**. |
| 5 | Se o teste TCP der certo, usar **Listar Arquivos**, **Upload** e **Download**. |

## Se não funcionar entre dois computadores

Se no mesmo computador funciona, mas entre dois computadores não funciona, a causa quase sempre está fora da lógica principal do programa. Os motivos mais comuns são: IP incorreto, computadores em redes diferentes, rede Wi‑Fi com isolamento entre clientes, porta diferente no cliente e no servidor, ou bloqueio de conexões de entrada no computador que executa o servidor.

Uma estratégia prática é inverter os papéis: execute o `tcp_server.py` no outro computador e rode o `tcp_client.py` no seu. Se funcionar invertido, o problema está provavelmente no bloqueio de entrada do primeiro computador.

## Protocolo usado pela aplicação

As mensagens são enviadas em JSON, mas antes de cada JSON é enviado um cabeçalho binário de 8 bytes. Esse cabeçalho informa o tamanho da mensagem. Assim, o programa não depende de “chutar” onde o JSON termina.

| Comando | Quem envia | Finalidade |
|---|---|---|
| `test_req` | Cliente | Testar se a conexão TCP está funcionando. |
| `test_resp` | Servidor | Confirmar que o servidor recebeu a conexão. |
| `list_req` | Cliente | Solicitar a lista de arquivos disponíveis. |
| `list_resp` | Servidor | Responder com a lista de arquivos. |
| `put_req` | Cliente | Enviar um arquivo ao servidor. |
| `put_resp` | Servidor | Confirmar ou negar o upload. |
| `get_req` | Cliente | Solicitar download de um arquivo. |
| `get_resp` | Servidor | Enviar o arquivo solicitado. |

## Observação importante para apresentação

Se o professor perguntar por que a descoberta automática pode falhar, a resposta é: a descoberta usa broadcast UDP, e algumas redes bloqueiam broadcast entre clientes. Isso não invalida o protocolo TCP da aplicação. O teste mais importante é o botão **Testar Conexão TCP** usando o IPv4 real do servidor.

Se o professor perguntar por que o TCP precisa de um cabeçalho de tamanho, a resposta é: TCP entrega um fluxo contínuo de bytes, não mensagens prontas. Portanto, a aplicação precisa definir onde cada mensagem começa e termina. O cabeçalho de 8 bytes resolve isso informando o tamanho exato do JSON que será recebido.

---

Autor: **Manus AI**
