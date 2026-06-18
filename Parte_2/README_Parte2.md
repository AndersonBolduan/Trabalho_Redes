# Parte 2 — Cliente e Servidor de Arquivos via TCP

Esta pasta contém a implementação da **Parte 2** do trabalho de Redes de Computadores. A aplicação é composta por dois programas: um **servidor TCP**, responsável por armazenar e enviar arquivos, e um **cliente com interface gráfica**, responsável por listar, enviar e baixar arquivos do servidor.

A versão atual foi revisada para facilitar o uso entre **dois computadores diferentes na mesma rede local**, sem depender de alteração manual no Painel de Controle. O servidor agora exibe automaticamente os IPs locais que podem ser usados pelo cliente, o cliente possui um botão para tentar localizar o servidor na rede e a troca de mensagens TCP usa um protocolo mais robusto com cabeçalho de tamanho.

## Arquivos

| Arquivo | Função |
|---|---|
| `tcp_server.py` | Programa que deve ser executado no computador que armazenará os arquivos. |
| `tcp_client.py` | Programa com interface gráfica usado para listar, enviar e baixar arquivos. |
| `server_storage/` | Pasta criada automaticamente pelo servidor para guardar os arquivos recebidos. |

## Como testar no mesmo computador

Para testar tudo em uma única máquina, abra dois terminais na pasta da Parte 2. No primeiro terminal, execute o servidor:

```bash
python tcp_server.py
```

No segundo terminal, execute o cliente:

```bash
python tcp_client.py
```

Na interface do cliente, mantenha o IP como `127.0.0.1` e a porta como `50000`. Depois clique em **Listar Arquivos**, **Fazer Upload** ou **Fazer Download**.

## Como conectar dois computadores na mesma rede

No computador que será o servidor, execute:

```bash
python tcp_server.py
```

Ao iniciar, o servidor mostrará uma saída parecida com esta:

```text
Use, no cliente, um dos IPs abaixo como IP do servidor:
  - 192.168.1.34:50000
```

No outro computador, execute:

```bash
python tcp_client.py
```

Na interface do cliente, coloque no campo **IP do Servidor** o IPv4 mostrado no terminal do servidor, por exemplo `192.168.1.34`. A porta deve ser a mesma exibida pelo servidor, por padrão `50000`.

Você também pode clicar no botão **Localizar Servidor na Rede**. Esse botão envia uma mensagem de descoberta via broadcast UDP na rede local. Se a rede permitir broadcast, o cliente preencherá automaticamente o IP e a porta do servidor.

## Importante sobre bloqueios de rede

Esta versão foi ajustada para funcionar melhor em laboratório, usando uma porta alta (`50000`), escutando em todas as interfaces de rede (`0.0.0.0`) e oferecendo descoberta automática. Mesmo assim, existe um limite técnico: se a política da máquina ou da rede bloquear totalmente conexões de entrada, nenhum código consegue “furar” esse bloqueio sozinho.

Na prática, se outros alunos estão conseguindo sem abrir regra no Painel de Controle, provavelmente a rede permite conexões locais ou o Windows já autorizou o Python anteriormente. Com esta versão, o teste fica mais simples porque o servidor mostra o IP correto e o cliente tenta encontrá-lo automaticamente.

## Comandos úteis

Se quiser usar outra porta, execute o servidor assim:

```bash
python tcp_server.py --port 50001
```

Depois, no cliente, use a mesma porta `50001`.

Se quiser mudar a pasta onde os arquivos ficam armazenados no servidor, execute:

```bash
python tcp_server.py --storage meus_arquivos
```

## Protocolo de comunicação

A comunicação usa **TCP**. Cada mensagem enviada pelo cliente ou pelo servidor possui duas partes: primeiro, um cabeçalho de 8 bytes informando o tamanho da mensagem; depois, o JSON em UTF-8. Isso evita o problema clássico de tentar ler uma mensagem TCP “pela metade”, principalmente quando o arquivo é grande.

| Operação | Requisição | Resposta |
|---|---|---|
| Listar arquivos | `list_req` | `list_resp` com a lista de arquivos. |
| Enviar arquivo | `put_req` com nome, hash e conteúdo em Base64 | `put_resp` com status `ok` ou `fail`. |
| Baixar arquivo | `get_req` com o nome do arquivo | `get_resp` com hash e conteúdo em Base64. |

O conteúdo dos arquivos é convertido para **Base64** para caber dentro do JSON. A integridade é verificada com **SHA-256**: o cliente calcula o hash antes do upload, o servidor recalcula depois de receber, e no download o cliente também confere se o arquivo recebido tem o mesmo hash enviado pelo servidor.

## Passo a passo recomendado para apresentação

Primeiro, abra o servidor no computador principal e mostre que ele está escutando em `0.0.0.0:50000`. Explique que `0.0.0.0` significa que o programa aceita conexões vindas das interfaces de rede da máquina. Em seguida, mostre o IP local impresso no terminal, como `192.168.x.x`, e use esse endereço no cliente executado em outro computador.

Depois, clique em **Listar Arquivos** para provar que a conexão funcionou. Em seguida, faça upload de um arquivo PDF ou CSV e mostre que ele aparece na lista. Por fim, faça download do mesmo arquivo e explique que o SHA-256 confirma se o arquivo chegou íntegro.

## Resumo das melhorias desta versão

| Melhoria | Por que ajuda |
|---|---|
| Porta padrão alterada para `50000` | Evita conflitos com serviços conhecidos e facilita testes em laboratório. |
| Servidor mostra os IPs locais | Evita confusão entre `127.0.0.1` e o IP real da rede. |
| Botão “Localizar Servidor na Rede” | Tenta encontrar o servidor automaticamente via broadcast UDP. |
| Cabeçalho de 8 bytes com tamanho do JSON | Garante leitura correta de mensagens grandes no TCP. |
| Mensagens de erro mais explicativas | Ajuda a diagnosticar IP errado, porta errada ou servidor desligado. |

---

Autor: **Manus AI**
