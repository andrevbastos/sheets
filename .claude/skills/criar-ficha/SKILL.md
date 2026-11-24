---
name: criar-ficha
description: Cria fichas de personagem para o app de fichas deste projeto (Ordem Paranormal e D&D 5e), guiando o jogador passo a passo pelas regras de criação dos livros em sistemas/ (atributos, origem/raça, classe, perícias, trilha, rituais, magias, equipamento) e salvando o .json pronto para abrir no app. Use sempre que alguém quiser criar, montar ou fazer um personagem, agente, investigador ou ficha nova, mesmo sem dizer "ficha" (ex.: "quero fazer um ocultista", "monta um anão guerreiro pro meu amigo", "me ajuda a criar meu agente de NEX 20%", "faz um PJ de nível 3 pra sessão de sábado"). Não é para ameaças nem monstros do mestre.
---

# Criar ficha (Ordem Paranormal e D&D 5e)

O objetivo é sair com uma ficha que respeite as regras de criação do livro e que o app abra sem
ajustes, e fazer isso **conversando**: a pessoa decide o personagem, você conhece as regras.

## Antes de começar
1. Descubra o sistema (Ordem Paranormal ou D&D 5e) e, se não for o primeiro nível, o NEX ou nível.
   Se não der para deduzir, pergunte.
2. Leia a referência do sistema: `references/ordem.md` ou `references/dnd.md`. Ela traz o passo a passo
   com páginas, as tabelas de escolha e o formato do arquivo.
3. Para qualquer regra que a referência só resume (habilidades de classe, poderes, trilhas, rituais,
   traços de raça, magias, equipamento), leia a página do livro antes de explicar ou anotar:
   ```
   uv run --no-project --with pypdf python .claude/skills/criar-ficha/scripts/livro.py ordem 32 33
   uv run --no-project --with pypdf python .claude/skills/criar-ficha/scripts/livro.py jogador --buscar "ataque furtivo"
   ```
   A primeira leitura de cada livro demora (até um minuto) e fica em cache. Os PDFs ficam fora do git;
   se faltar o livro, siga só com a referência e diga isso ao usuário.

## Como guiar
- Siga a ordem do livro, **um passo por vez**. Em cada passo diga em uma ou duas frases o que ele
  decide e o que muda na ficha, cite a página, e ofereça as opções. Quando houver ferramenta de
  perguntas com botões, use-a; dê 2 a 4 opções que combinem com o conceito, com a sua recomendação
  primeiro, e lembre que as outras existem (são 26 origens, 13 antecedentes...).
- Comece pelo **conceito** (uma frase sobre quem é o personagem). Ele guia as recomendações: um
  investigador forense pede Intelecto, não Força.
- Se a pessoa já disse as escolhas, não pergunte de novo; confira contra as regras e siga. Se disser
  "escolhe você" ou pedir tudo pronto, decida pelo conceito e explique as escolhas no final em poucas
  linhas, para ela poder trocar.
- Mostre as contas que dependem das escolhas no momento em que importam: "com INT 3 você escolhe
  10 perícias", "Força 0 deixa 2 espaços de carga", "15 + 2 do anão = 17 (+3)".
- Rolagens (4d6 de atributos, 2d20 da origem): pergunte se a pessoa quer rolar os próprios dados ou que
  você role. Se você rolar, use Python (`random`) e mostre cada dado.
- Regra fora do livro (atributo 4 na criação, perícia a mais) é decisão do mestre: avise uma vez,
  com a página, e se a pessoa confirmar, siga e anote a exceção na descrição do personagem.
- Descrições de habilidades, poderes, rituais e magias na ficha são **resumos seus** de uma ou duas
  frases com o efeito mecânico e a página, nunca o texto copiado do livro.
- Não pergunte sobre o que o app calcula sozinho (PV/PE/SAN de Ordem, modificadores, bônus de perícia,
  Defesa, CD de magia, proficiência): só mostre o resultado.

## Montar, conferir e salvar
1. Escreva as escolhas num JSON no diretório de rascunho (formato no fim da referência do sistema).
2. Confira:
   ```
   uv run python .claude/skills/criar-ficha/scripts/criar_ficha.py <escolhas.json> --conferir
   ```
   O script normaliza com o mesmo código do app, imprime o resumo com os números calculados e uma lista
   de AVISOS do que foge da regra de criação (soma de atributos, número de perícias, PV, resistências,
   espaços de magia, rituais do ocultista, limite de itens da patente...). Em Ordem ele também imprime
   "Pelo NEX, a ficha deve ter", uma lista para conferir as habilidades.
3. Para cada aviso, corrija ou, se for exceção combinada, explique ao usuário por que ficou.
4. Salve sem `--conferir`. O padrão é `sheets/<nome>.json`; use `--saida` se a pessoa pedir outra pasta.
   Se o arquivo já existir, o script para: pergunte antes de usar `--sobrescrever`.
5. Mostre o resumo final (atributos, PV/PE/SAN ou PV/CA, perícias, habilidades, equipamento) e diga
   onde a ficha foi salva. Para usar: no app do mestre (`uv run dm.py`), **Abrir ficha** ou clicar no
   jogador conectado e escolher o arquivo.

## Acima do primeiro nível
Monte o personagem de NEX 5% / nível 1 pelas regras e depois aplique cada NEX ou nível em ordem,
perguntando as escolhas de cada um (trilha, poderes, aumentos de atributo, graus de treinamento,
subclasse, magias, talentos). Agrupe as perguntas por marco para não virar uma lista de 20 perguntas.
