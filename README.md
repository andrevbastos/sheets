# Fichas de RPG em rede

App de fichas para mesa presencial ou em rede local. O mestre abre o servidor, cada jogador conecta pelo próprio PC, e a ficha sincroniza nos dois sentidos em tempo real.

Sistemas suportados:
- **D&D 5e**
- **Ordem Paranormal**: segue a ficha oficial. Todos os campos são editáveis na tela; o app só calcula o que a própria ficha mostra (Defesa = 10 + AGI + Equip. + Outros, e o bônus de cada perícia = Treino + Outros).

## Instalar

Precisa do [uv](https://docs.astral.sh/uv/). Ele baixa o Python 3.14 e as dependências sozinho:

```
winget install astral-sh.uv
uv sync
```

## Usar

**Mestre**
```
uv run dm.py
```
Ao abrir, o mestre escolhe o sistema da sessão (D&D 5e ou Ordem Paranormal); todas as fichas da sessão seguem esse sistema, e fichas de outro sistema são recusadas. Para pular a pergunta: `uv run dm.py --sistema ordem`.

A barra lateral mostra o endereço que os jogadores devem digitar (ex.: `192.168.0.4:5000`). Na primeira vez, o Windows pergunta se o Python pode usar a rede: clique em **Permitir**, senão os outros PCs não conseguem conectar.

- Quando um jogador conecta, ele aparece na lista. Clique nele para escolher o arquivo `.json` da ficha.
- **Abrir ficha** abre um `.json` só para você ver e editar (sem jogador).
- **Nova ficha** cria uma ficha em branco do sistema da sessão.
- Tudo o que o mestre ou o jogador edita é salvo na hora no arquivo da ficha, no PC do mestre.

**Jogador**
```
uv run player.py
```
Digite o endereço do mestre e o nome do personagem. Se a conexão cair (Wi-Fi, PC suspenso), a ficha continua aberta, o app reconecta sozinho e envia o que foi editado no meio tempo. O mestre não precisa escolher a ficha de novo.

**Criar ficha pela linha de comando**
```
uv run main.py "Gimli"
uv run main.py "Arthur" --sistema ordem
```

Para usar outra porta: `uv run dm.py --port 5001`, e o jogador digita `ip:5001`.

## Estrutura

```
dm.py, player.py          janelas do mestre e do jogador
main.py                   cria ficha nova a partir do template
src/sheet_io.py           ler/salvar/normalizar fichas
src/net/protocol.py       mensagens JSON + heartbeat
src/net/server.py         servidor do mestre
src/net/client.py         cliente do jogador (com reconexão)
src/ordem.py              perícias, cálculos e normalização de Ordem Paranormal
src/ui/dnd5e_sheet.py     tela da ficha de D&D 5e
src/ui/ordem_sheet.py     tela da ficha de Ordem Paranormal
src/ui/systems.py         escolhe a tela pelo campo "sistema" da ficha
sheets/                   template e fichas de exemplo
tests/                    testes (uv run pytest)
```

Para adicionar outro sistema de RPG: criar `src/ui/<sistema>_sheet.py` com uma classe `SheetView`, um template em `sheets/`, e registrar em `src/ui/systems.py` e `src/sheet_io.SYSTEMS`.

## Testes

```
uv run pytest
```
