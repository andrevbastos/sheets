# Ordem Paranormal: criação de agente (livro básico)

Páginas são as impressas no livro. Leia o texto com
`uv run --no-project --with pypdf python .claude/skills/criar-ficha/scripts/livro.py ordem <páginas>`
(ou `--buscar "termo"`). Os nomes, perícias e poderes das origens e os nomes das trilhas também estão
em `src/ordem.py` (`ORIGENS`, `TRILHAS`), que é o que o app usa.

## Sumário
1. Passo a passo (p. 13)
2. Atributos
3. Origem
4. Classe, perícias e habilidades de NEX 5%
5. Personagem acima de NEX 5%
6. Ocultista: rituais
7. Equipamento
8. Toques finais
9. Formato do arquivo de escolhas

## 1. Passo a passo (p. 13)
Conceito → atributos → origem → classe → perícias → revisão (PV, PE, SAN) → equipamento → toques finais.
O livro segue o exemplo da agente Bianca nesses passos (p. 13-22), útil para mostrar ao jogador.

## 2. Atributos (p. 13; descrição p. 10 e 34-35)
- Agilidade (AGI), Força (FOR), Intelecto (INT), Presença (PRE), Vigor (VIG). Escala 0 a 5; 1 é a média humana.
- Todos começam em **1** e há **4 pontos** para distribuir. Pode reduzir **um** atributo a 0 para ganhar
  1 ponto a mais. Máximo inicial **3**. Ou seja: a soma inicial é sempre 9.
- O que cada um faz na ficha: AGI = Defesa (10 + AGI) e dados de perícias de AGI; FOR = carga (5 × FOR
  espaços; 2 com FOR 0); INT = número de perícias treinadas; PRE = PE e DT de rituais; VIG = PV.
- Atributo 0 rola 2d20 e fica com o pior: avise o jogador se ele zerar algo usado por perícias que quer.

## 3. Origem (p. 16-21; Tabela 1.1 na p. 19, rolagem 2d20 opcional)
Dá **duas perícias treinadas** e **um poder**. As 26 origens:

| Origem | Perícias | Poder |
|---|---|---|
| Acadêmico | Ciências, Investigação | Saber é Poder |
| Agente de Saúde | Intuição, Medicina | Técnica Medicinal |
| Amnésico | duas à escolha do mestre | Vislumbres do Passado |
| Artista | Artes, Enganação | Magnum Opus |
| Atleta | Acrobacia, Atletismo | 110% |
| Chef | Fortitude, Profissão (cozinheiro) | Ingrediente Secreto |
| Criminoso | Crime, Furtividade | O Crime Compensa |
| Cultista Arrependido | Ocultismo, Religião | Traços do Outro Lado (um poder paranormal; metade da SAN) |
| Desgarrado | Fortitude, Sobrevivência | Calejado |
| Engenheiro | Profissão, Tecnologia | Ferramenta Favorita |
| Executivo | Diplomacia, Profissão | Processo Otimizado |
| Investigador | Investigação, Percepção | Faro para Pistas |
| Lutador | Luta, Reflexos | Mão Pesada |
| Magnata | Diplomacia, Pilotagem | Patrocinador da Ordem |
| Mercenário | Iniciativa, Intimidação | Posição de Combate |
| Militar | Pontaria, Tática | Para Bellum |
| Operário | Fortitude, Profissão | Ferramenta de Trabalho |
| Policial | Percepção, Pontaria | Patrulha |
| Religioso | Religião, Vontade | Acalentar |
| Servidor Público | Intuição, Vontade | Espírito Cívico |
| Teórico da Conspiração | Investigação, Ocultismo | Eu Já Sabia |
| T.I. | Investigação, Tecnologia | Motor de Busca |
| Trabalhador Rural | Adestramento, Sobrevivência | Desbravador |
| Trambiqueiro | Crime, Enganação | Impostor |
| Universitário | Atualidades, Investigação | Dedicação |
| Vítima | Reflexos, Vontade | Cicatrizes Psicológicas |

O app marca as perícias da origem como treinadas e mostra o poder resumido; os poderes que mudam números
(Calejado, Cicatrizes, Dedicação, Patrulha, Patrocinador, Traços do Outro Lado) já entram na conta.
Para Profissão, preencha `profissao_nome` (ex.: "advogado").

## 4. Classe (p. 22-35)
Se a classe der uma perícia que a origem já deu, **escolha outra** (p. 22). Comece com todas as
habilidades de NEX 5% da classe.

| | Combatente (p. 24-27) | Especialista (p. 28-31) | Ocultista (p. 32-35) |
|---|---|---|---|
| PV | 20 + VIG; +4 + VIG por NEX | 16 + VIG; +3 + VIG | 12 + VIG; +2 + VIG |
| PE | 2 + PRE; +2 + PRE | 3 + PRE; +3 + PRE | 4 + PRE; +4 + PRE |
| SAN | 12; +3 | 16; +4 | 20; +5 |
| Perícias | Luta **ou** Pontaria, Fortitude **ou** Reflexos, + 1 + INT à escolha | 7 + INT à escolha | Ocultismo e Vontade, + 3 + INT à escolha |
| Proficiências | armas simples e táticas, proteções leves | armas simples, proteções leves | armas simples |
| NEX 5% | Ataque Especial (2 PE: +5 no ataque ou no dano) | Eclético (2 PE: age como treinado numa perícia); Perito (escolhe 2 perícias treinadas, exceto Luta/Pontaria; 2 PE: +1d6) | Escolhido pelo Outro Lado (rituais de 1º círculo; começa com 3) |

PV, PE e SAN o app calcula sozinho; não é preciso digitar. Total de perícias treinadas na criação:
2 da origem + as da classe (contando as fixas) + INT. Aumentar o INT depois dá mais uma perícia (p. 39).
Graus: treinado +5, veterano +10, expert +15 (p. 39). Na criação, todas ficam em treinado.

Anote as habilidades da classe em `habilidades` (nome, custo em PE, página, descrição curta escrita por
você, sem copiar o livro). Exemplo: `{"nome": "Perito", "custo": "2", "pagina": "28",
"descricao": "Ciências e Investigação: +1d6 no teste."}`.

## 5. Acima de NEX 5% (Tabela 1.2 na p. 23; Tabelas 1.3-1.5 nas p. 25, 29, 33)
NEX válidos: 5, 10, ..., 95, 99. Ganhos por NEX (iguais nas três classes, salvo a linha da classe):
- 10%, 40%, 65%, 99%: habilidade de **trilha** (escolhe a trilha em 10%; trilhas p. 24-35, nomes em
  `src/ordem.py`, campo `trilha` com a chave, ex. `"tropa"`).
- 15%, 30%, 45%, 60%, 75%, 90%: **poder de classe** (listas logo depois de cada tabela).
- 20%, 50%, 80%, 95%: **aumento de atributo** (+1, máximo 5).
- 35%, 70%: **grau de treinamento**: sobe um grau em 2 + INT (combatente), 5 + INT (especialista) ou
  3 + INT (ocultista) perícias.
- 50%: **versatilidade** e **afinidade** (campo `afinidade`: Conhecimento, Energia, Morte ou Sangue; p. 114).
- Linha da classe: Ataque Especial em 25/55/85% (combatente); Perito em 25/55/85% e Engenhosidade em
  40/75% (especialista); novo círculo de ritual em 25/55/85% (ocultista).
O script de conferência imprime "Pelo NEX, a ficha deve ter: ..." para usar como checklist.

## 6. Ocultista: rituais (p. 32; capítulo 5, lista na p. 122, custo Tabela 5.2 na p. 119)
Começa com **3 rituais de 1º círculo**; a cada NEX novo aprende mais um de um círculo que possa lançar
(2º em 25%, 3º em 55%, 4º em 85%). Outras classes só têm rituais por poderes (ex. Transcender).
Campos de cada ritual: nome, elemento (Conhecimento, Energia, Morte, Sangue, Medo), circulo, execucao,
alcance, alvo, duracao, resistencia, dano, pagina, descricao (resumo seu). Leia o ritual no livro antes.

## 7. Equipamento (capítulo 3: patentes p. 51-53, armas p. 54-59, proteções e itens depois)
- Todo agente começa como **recruta**: até **2 itens de categoria I** e quantos itens de categoria 0
  quiser, limitados pela carga (5 × FOR espaços). Crédito baixo. "Equipamento Inicial" (p. 53): escolha
  um equipamento padrão e anote as estatísticas das armas.
- Ataques: `{"nome": "Faca", "teste": "Luta", "dano": "1d4", "especial": "19 / corpo a corpo / corte"}`.
  `teste` é Luta (corpo a corpo) ou Pontaria (distância), opcionalmente com bônus (`Luta +2`).
- Proteção: `defesa.equipamento` recebe o bônus da proteção; `protecao` é o nome.
- Itens: `{"nome", "categoria": "0".."IV", "espacos", "descricao"}`.

## 8. Toques finais (p. 36-37)
Nome, gênero, idade (2d6+15 se quiser sortear), aparência, personalidade, histórico e objetivo
(campo `descricao`), e `jogador`. Deslocamento padrão 9m.

## 9. Formato do arquivo de escolhas
```json
{
  "sistema": "ordem",
  "nome": "Bianca Lima", "jogador": "Luísa",
  "origem": "Investigador", "classe": "Especialista", "nex": 5,
  "atributos": {"agi": 2, "for": 1, "int": 3, "pre": 2, "vig": 1},
  "pericias": {"Ciências": {"treino": 5}, "Investigação": {"treino": 5}},
  "profissao_nome": "",
  "trilha": "", "afinidade": "",
  "habilidades": [{"nome": "Eclético", "custo": "2", "pagina": "28", "descricao": "..."}],
  "rituais": [],
  "ataques": [{"nome": "Revólver", "teste": "Pontaria", "dano": "2d6", "especial": "19 / curto / balístico"}],
  "defesa": {"equipamento": 0, "outros": 0}, "protecao": "",
  "inventario": {"pontos_prestigio": 0, "itens": [{"nome": "Revólver", "categoria": "I", "espacos": 1}]},
  "descricao": {"aparencia": "", "personalidade": "", "historico": "", "objetivo": ""}
}
```
Inclua em `pericias` todas as treinadas (as da origem também, para a contagem ficar clara).
