# Fichas de RPG em rede

App de fichas para mesa presencial ou em rede local. O mestre abre o servidor, cada jogador conecta pelo próprio PC, e a ficha sincroniza nos dois sentidos em tempo real.

Sistemas suportados:
- **D&D 5e**
- **Ordem Paranormal**: segue a ficha oficial, com as regras do livro básico calculadas sozinhas:
  - PV, PE e SAN máximos pela classe (Combatente, Especialista, Ocultista), NEX, Vigor e Presença. Cada um tem um campo de **bônus** para poderes e desvantagens. Com outra classe, os máximos são digitados à mão.
  - Origem (as 26 do livro): as duas perícias da origem ficam Treinadas e o poder aparece resumido embaixo. Os poderes que mexem na ficha entram na conta: Calejado (+1 PV por NEX), Cicatrizes Psicológicas (+1 SAN por NEX), Dedicação (+PE e +1 PE por rodada), Patrulha (+2 Defesa), Patrocinador da Ordem (crédito um acima), Traços do Outro Lado (metade da SAN inicial). Ao trocar de origem, as perícias da antiga que estavam só em Treinado voltam a Destreinado.
  - PE por rodada (limite de PE) e DT de rituais (10 + limite de PE + PRE).
  - Perícias por grau (destreinado, treinado +5, veterano +10, expert +15); atributo 0 rola 2d20 e fica com o pior.
  - Carga máxima (5 × FOR; 2 com FOR 0). Sobrecarregado: −5 na Defesa e nas perícias de carga.
  - Patente, limite de crédito e limite de itens por categoria a partir dos pontos de prestígio.

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

**Dados**

O botão **Dados** (na barra lateral do mestre e na barra de cima do jogador) abre uma janela separada de rolagem. Escolha o dado, a quantidade, o bônus e, se for o caso, vantagem ou desvantagem com quantos dados extras (rola a mais e fica com os maiores ou menores). Quem rola é sempre o servidor do mestre, e todo mundo vê o resultado no histórico da mesa, por exemplo `Sofia: 1d20 (Van 1) + 5 → [(13), 18] = 23` (o dado entre parênteses foi descartado).

Num teste de 1d20, um 20 natural aparece em verde como **SUCESSO CRÍTICO** e um 1 natural em vermelho como **FALHA CRÍTICA** (vale o dado que ficou depois da vantagem/desvantagem).

O mestre pode marcar **Privada**: os jogadores veem a linha `? Mestre: ?d? = ?`, sem o dado nem o valor; o mestre vê o resultado completo.

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
src/ordem.py              perícias, regras do livro e normalização de Ordem Paranormal
src/ui/dnd5e_sheet.py     tela da ficha de D&D 5e
src/ui/ordem_sheet.py     tela da ficha de Ordem Paranormal
src/ui/systems.py         escolhe a tela pelo campo "sistema" da ficha
src/dice.py               rolagem de dados (vantagem/desvantagem, privada)
src/ui/dice_window.py     janela separada de rolagem
sheets/                   template e fichas de exemplo
tests/                    testes (uv run pytest)
```

Para adicionar outro sistema de RPG: criar `src/ui/<sistema>_sheet.py` com uma classe `SheetView`, um template em `sheets/`, e registrar em `src/ui/systems.py` e `src/sheet_io.SYSTEMS`.

## Testes

```
uv run pytest
```
