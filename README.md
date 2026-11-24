# Fichas de RPG em rede

App de fichas para mesa presencial ou em rede local. O mestre abre o servidor, cada jogador conecta pelo próprio PC, e a ficha sincroniza nos dois sentidos em tempo real.

Sistemas suportados:
- **D&D 5e**: tudo é editável no app, e as regras do Livro do Jogador são calculadas sozinhas:
  - Modificador de cada atributo pelo valor (p. 173) e bônus de proficiência pelo nível (p. 15).
  - Perícias e testes de resistência: modificador + proficiência (dobrada para especialista) + um campo "outros" para talentos e itens. Na ficha, a bolinha dos testes de resistência marca a proficiência.
  - Iniciativa (Destreza + outros), Percepção passiva (10 + Percepção) e CD/ataque de magia (8 + modificador + proficiência, p. 205). O atributo de conjuração sai da classe (Mago = INT, Clérigo = SAB, Bardo = CAR...) ou é escolhido à mão; sem ele, CD e ataque são digitados.
  - Fichas antigas abrem com os mesmos números: a diferença entre o bônus salvo e o calculado vira "outros".
  - **Rolar pela ficha:** o bônus de cada perícia, teste de resistência, atributo e da iniciativa é um botão. Cada ataque tem **Ataque** (`+5`, ou `FOR`/`DES +1` = atributo + proficiência + extra) e **Dano** (`2d6+3`, ou `1d8+FOR` com o modificador). Ataques antigos ("Bônus: +5 | Dano: 2d6+3") são separados nesses campos sozinhos.
  - **Vida e descanso:** PV temporários (o dano tira deles primeiro, p. 198), botões de dano e cura, inspiração (★), dados de vida pela classe (o botão **Gastar** rola o dado + CON e desconta um) e, com 0 PV, os testes contra a morte (p. 197). **Recursos** de classe com −/+ e quando voltam (descanso curto ou longo). **Descanso curto** enche os recursos de descanso curto; **Descanso longo** recupera PV, metade dos dados de vida, espaços de magia e recursos (p. 186).
  - Magias têm nível (truque a 9º) e a lista fica em ordem de nível.
- **Ordem Paranormal**: segue a ficha oficial, com as regras do livro básico calculadas sozinhas:
  - PV, PE e SAN máximos pela classe (Combatente, Especialista, Ocultista), NEX, Vigor e Presença. Cada um tem um campo de **bônus** para poderes e desvantagens. Com outra classe, os máximos são digitados à mão.
  - Origem (as 26 do livro): as duas perícias da origem ficam Treinadas e o poder aparece resumido embaixo. Os poderes que mexem na ficha entram na conta: Calejado (+1 PV por NEX), Cicatrizes Psicológicas (+1 SAN por NEX), Dedicação (+PE e +1 PE por rodada), Patrulha (+2 Defesa), Patrocinador da Ordem (crédito um acima), Traços do Outro Lado (metade da SAN inicial). Ao trocar de origem, as perícias da antiga que estavam só em Treinado voltam a Destreinado.
  - PE por rodada (limite de PE) e DT de rituais (10 + limite de PE + PRE).
  - **Trilha** (p. 26-35): o menu mostra as 5 trilhas da classe e, embaixo, as habilidades de NEX 10%, 40%, 65% e 99% (em branco as que o NEX já liberou). As que mudam números entram na conta: Casca Grossa (+1 PV por 5% de NEX), Iniciativa Aprimorada (+5 em Iniciativa), Inventário Otimizado (carga com FOR + INT) e Inquebrável (+5 na Defesa machucado; morrendo não fica indefeso). Trocar de classe apaga a trilha da classe antiga. **Afinidade** (Conhecimento, Energia, Morte ou Sangue) libera em NEX 50%.
  - **Estados** (p. 88 e 111, com a errata): **machucado** (metade dos PV ou menos) e **inconsciente** (0 PV) aparecem ao lado dos PV. Chegar a 0 PV liga **morrendo**, que curar não desliga: só **Estabilizar** (Medicina DT 20, fica com 1 PV). Chegar a 0 SAN liga **enlouquecendo**, que acaba com qualquer cura de SAN ou com **Acalmar** (fica com SAN 1). Cada um mostra 3 bolinhas para os turnos iniciados assim na cena; a terceira é MORTO/INSANO. **Nova cena** zera a contagem. Na barra lateral do mestre aparecem os estados de todo mundo (no D&D: caído com os testes contra a morte; monstro sangrando ou derrotado).
  - **Condições** (p. 310-311): o menu **+ condição** põe uma etiqueta e o × tira. Passar o mouse mostra um resumo do efeito. Repetir uma condição piora como o livro manda: abalado vira apavorado, fatigado vira exausto e depois inconsciente, fraco vira debilitado e depois inconsciente, frustrado vira esmorecido. Ameaças também têm condições, e a barra lateral do mestre mostra as de todo mundo. As **penalidades entram sozinhas**: cada condição tira os d20 que o livro manda dos testes que ela atinge (abalado: todos; fraco/debilitado: AGI, FOR e VIG; caído: ataques corpo a corpo; surdo: Iniciativa...), e o motivo aparece no histórico (`Faca (−4d20: abalado, fraco, caído)`). Condições que incluem outras contam as incluídas (exausto = debilitado, lento e vulnerável); na mesma linha vale a pior. Com 0 dados rola 2d20 e fica com o pior. Na tabela de perícias, os dados ficam amarelos quando estão reduzidos. A Defesa cai 5 (desprevenido), 10 (indefeso, inclusive com 0 PV) e 2 (vulnerável); na ameaça aparece "vale N" embaixo da Defesa digitada. O caído na Defesa depende do ataque e fica só no aviso.
  - Perícias por grau (destreinado, treinado +5, veterano +10, expert +15); atributo 0 rola 2d20 e fica com o pior.
  - Carga máxima (5 × FOR; 2 com FOR 0). Sobrecarregado: −5 na Defesa e nas perícias de carga. Não dá para passar do dobro da carga: o inventário recusa o item ou limita os espaços.
  - Patente, limite de crédito e limite de itens por categoria a partir dos pontos de prestígio.
  - Itens, ataques e habilidades têm uma área de descrição com quebra de linha embaixo de cada um.
  - Rituais numa aba própria: elemento, círculo (o custo em PE sai da tabela da p. 119), execução, alcance, alvo, duração, resistência e dano. A DT de rituais fica no topo da aba.
  - **Rolar pela ficha:** o bônus de cada perícia é um botão, e cada ataque tem **Teste** e **Dano**. Shift+clique rola com +1d20 e Ctrl+clique com −1d20. O clique abre a janela de Dados (se estiver fechada) e rola, com o nome da perícia ou do ataque no histórico. No teste de ataque vale escrever `Luta`, `Luta +2`, `+5` ou o dado inteiro (`3d20+10`; na ficha do livro aparece como 3O+10).
- **Ameaças (Ordem Paranormal, só do mestre):** ficha no formato do livro (p. 178-179). Tem VD, descritores, tamanho, Presença Perturbadora, PV com o limiar de machucado, Defesa, Percepção, Iniciativa, Fortitude, Reflexos e Vontade, resistências, vulnerabilidades, perícias, ações (padrão, movimento, completa, reação, livre) e habilidades. Os testes são escritos com o dado inteiro (`2d20+10`, `2d6+5 corte`; o 2O+10 do livro é convertido sozinho), e cada um tem botão de rolar. Ameaças não podem ser entregues a jogadores.
- **Monstros (D&D 5e, só do mestre):** ficha no formato do bloco de estatísticas. O ND define o bônus de proficiência e o XP. Tem tamanho, tipo de criatura, tendência, CA com descrição, PV com fórmula (**Média** preenche os PV como nos livros), PV temporários, iniciativa, deslocamento, atributos com o teste de resistência embaixo de cada um (a bolinha soma a proficiência), perícias escritas (`Furtividade +6, Percepção`; sem número vale atributo + proficiência), sentidos, idiomas, vulnerabilidades, resistências, imunidades e Percepção passiva. As ações ficam em ordem de tipo (ação, ação bônus, reação, lendária), com ataque `+4` ou `DES` e dano `1d6+DES cortante`, e há um contador de ações lendárias. Monstros também não podem ser entregues a jogadores.

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
- **Abrir ficha** abre um ou vários `.json` (Ctrl/Shift no explorador) para você ver e editar sem jogador.
- **Nova ficha** cria uma ficha em branco do sistema da sessão. **Nova ameaça** (Ordem Paranormal) ou **Novo monstro** (D&D 5e) cria a ficha só do mestre (o explorador abre em `sheets/npcs`).
- **Iniciativa** abre uma janela com todas as fichas abertas na barra lateral. **Rolar todos** rola a iniciativa de todo mundo e ordena (empate: maior bônus; depois agentes antes de ameaças). **Próximo turno** avança e conta as rodadas. Dá para digitar o valor à mão, rolar uma ficha só e adicionar nomes avulsos (ex.: "Filhote 2"). A iniciativa dos agentes aparece para a mesa; a das ameaças é privada (dá para desmarcar).
- Tudo o que o mestre ou o jogador edita é salvo na hora no arquivo da ficha, no PC do mestre.

**Jogador**
```
uv run player.py
```
Digite o endereço do mestre e o nome do personagem. Se a conexão cair (Wi-Fi, PC suspenso), a ficha continua aberta, o app reconecta sozinho e envia o que foi editado no meio tempo. O mestre não precisa escolher a ficha de novo.

**Dados**

Nos botões de rolar das fichas: no D&D, **Shift+clique = vantagem** e **Ctrl+clique = desvantagem**; no Ordem, Shift soma um d20 e Ctrl tira um.

O botão **Dados** (na barra lateral do mestre e na barra de cima do jogador) abre uma janela separada de rolagem. Escolha o dado, a quantidade, o bônus e, se for o caso, vantagem ou desvantagem com quantos dados extras (rola a mais e fica com os maiores ou menores). Quem rola é sempre o servidor do mestre, e todo mundo vê o resultado no histórico da mesa, por exemplo `Sofia: 2d20 (maior) + 5 → [(13), 18] = 23` (o dado entre parênteses foi descartado).

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
src/dnd.py                regras do Livro do Jogador e normalização de D&D 5e
src/ui/sheet_base.py      base das fichas editáveis (campos, recálculo, listas)
src/ui/dnd5e_sheet.py     tela da ficha de D&D 5e
src/ui/ordem_sheet.py     tela da ficha de Ordem Paranormal
src/ui/ameaca_sheet.py    tela da ficha de ameaça (Ordem Paranormal, só do mestre)
src/ui/monstro_sheet.py   tela da ficha de monstro (D&D 5e, só do mestre)
src/ui/initiative_window.py  janela de iniciativa do mestre
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
