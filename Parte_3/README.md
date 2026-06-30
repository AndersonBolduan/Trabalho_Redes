# AV3 - Parte 3: Sistema de Monitoramento e Controle Remoto

## Disciplina
Redes de Computadores I (RCA) - IFSC Campus Lages  
Professor: Robson Costa | 2026/1

## Descrição
Sistema cliente-servidor para monitoramento e controle remoto de sensores e atuadores em filiais de uma empresa. A comunicação é realizada via protocolo UDP com payload JSON codificado em UTF-8.

## Arquivos
- `servidor.py` - Aplicação do servidor (executada em cada filial)
- `cliente.py` - Aplicação do cliente com GUI (executada na matriz)
- `config_filial1.json` - Configuração de exemplo para Filial 1
- `config_filial2.json` - Configuração de exemplo para Filial 2

## Como Executar

### Servidor (Filial)
```bash
python servidor.py config_filial1.json
python servidor.py config_filial2.json
```

### Cliente (Matriz)
```bash
python cliente.py
```

## Requisitos
- Python 3.7+
- Biblioteca `tkinter` (inclusa na instalação padrão do Python)

## Ambiente de Teste (3 computadores)
1. **PC1** - Servidor Filial 1 (porta 51000)
2. **PC2** - Servidor Filial 2 (porta 52000)
3. **PC3** - Cliente Matriz (conecta em ambos)
