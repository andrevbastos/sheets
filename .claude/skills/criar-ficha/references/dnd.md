# D&D 5e: criação de personagem (Livro do Jogador PT-BR, edição de 2014)

Páginas são as impressas no livro. Leia o texto com
`uv run --no-project --with pypdf python .claude/skills/criar-ficha/scripts/livro.py jogador <páginas>`
(ou `--buscar "termo"`). O Caldeirão de Tasha (`livro.py tasha`, páginas do PDF) traz o artífice
(p. 8-12) e "Customizando sua Origem" (p. 6-7). O Guia do Mestre é foto, sem texto.

## Sumário
1. Passo a passo (cap. 1, p. 11-15)
2. Raça (cap. 2)
3. Classe (cap. 3)
4. Valores de habilidade
5. Antecedente e descrição (cap. 4)
6. Equipamento (cap. 5)
7. Magia
8. Acima do 1º nível
9. Formato do arquivo de escolhas

## 1. Passo a passo (p. 11-15)
Raça → classe → valores de habilidade → descrição (nome, tendência, antecedente, personalidade) →
equipamento → reunir o grupo. O livro acompanha o exemplo "Construindo Bruenor" em cada passo.
A ordem pode mudar (muita gente escolhe a classe primeiro); o que importa é aplicar todos os passos.

## 2. Raça (cap. 2, p. 17-43)
| Raça (sub-raça) | Aumentos | Desloc. | Pág. | Observações |
|---|---|---|---|---|
| Anão | CON +2 | 7,5m | 20 | colina: SAB +1, +1 PV por nível; montanha: FOR +2, armaduras leves e médias |
| Elfo | DES +2 | 9m | 23 | alto elfo: INT +1, um truque de mago; da floresta: SAB +1, 10,5m; drow: CAR +1. Percepção proficiente |
| Halfling | DES +2 | 7,5m | 28 | pés leves: CAR +1; robusto: CON +1 |
| Humano | +1 em todos | 9m | 31 | variante (p. 31): +1 em dois, uma perícia e um talento |
| Draconato | FOR +2, CAR +1 | 9m | 34 | ancestralidade dracônica: sopro e resistência |
| Gnomo | INT +2 | 7,5m | 36 | da floresta: DES +1; das rochas: CON +1 |
| Meio-elfo | CAR +2, +1 em outros dois | 9m | 39 | duas perícias à escolha |
| Meio-orc | FOR +2, CON +1 | 9m | 41 | Intimidação proficiente |
| Tiefling | CAR +2, INT +1 | 9m | 43 | |
Leia a página da raça para os traços (visão no escuro, resistências, idiomas, truques) e anote cada
traço em `caracteristicas`. Com a regra do Tasha (se o mestre permitir), os aumentos da raça podem ir
para outros atributos.

## 3. Classe (cap. 3, p. 45-117; tabela da classe na primeira página de cada uma)
| Classe | Dado de vida | Resistências | Perícias | Nível 1 | Pág. |
|---|---|---|---|---|---|
| Bárbaro | d12 | FOR, CON | 2 de: Adestrar Animais, Atletismo, Intimidação, Natureza, Percepção, Sobrevivência | Fúria, Defesa sem Armadura | 46-48 |
| Bardo | d8 | DES, CAR | 3 quaisquer | Conjuração, Inspiração de Bardo (d6) | 51-54 |
| Bruxo | d8 | SAB, CAR | 2 de: Arcanismo, Enganação, História, Intimidação, Investigação, Natureza, Religião | Patrono Transcendental, Magia de Pacto | 57-59 |
| Clérigo | d8 | SAB, CAR | 2 de: História, Intuição, Medicina, Persuasão, Religião | Conjuração, Domínio Divino | 63-65 |
| Druida | d8 | INT, SAB | 2 de: Arcanismo, Adestrar Animais, Intuição, Medicina, Natureza, Percepção, Religião, Sobrevivência | Druídico, Conjuração | 72-73 |
| Feiticeiro | d6 | CON, CAR | 2 de: Arcanismo, Enganação, Intuição, Intimidação, Persuasão, Religião | Conjuração, Origem de Feitiçaria | 78-79 |
| Guerreiro | d10 | FOR, CON | 2 de: Acrobacia, Adestrar Animais, Atletismo, História, Intuição, Intimidação, Percepção, Sobrevivência | Estilo de Luta, Retomar o Fôlego | 84-85 |
| Ladino | d8 | DES, INT | 4 de: Acrobacia, Atletismo, Atuação, Enganação, Furtividade, Intimidação, Intuição, Investigação, Percepção, Persuasão, Prestidigitação | Especialização, Ataque Furtivo (1d6), Gíria de Ladrão | 90-91 |
| Mago | d6 | INT, SAB | 2 de: Arcanismo, História, Intuição, Investigação, Medicina, Religião | Conjuração, Recuperação Arcana | 95-97 |
| Monge | d8 | FOR, DES | 2 de: Acrobacia, Atletismo, Furtividade, História, Intuição, Religião | Defesa sem Armadura, Artes Marciais (1d4) | 103-104 |
| Paladino | d10 | SAB, CAR | 2 de: Atletismo, Intuição, Intimidação, Medicina, Persuasão, Religião | Sentido Divino, Cura pelas Mãos | 109-110 |
| Patrulheiro | d10 | FOR, DES | 3 de: Acrobacia, Adestrar Animais, Atletismo, Furtividade, Intuição, Investigação, Natureza, Percepção, Sobrevivência | Inimigo Favorito, Explorador Natural | 116-117 |
| Artífice (Tasha) | d8 | CON, INT | 2 de: Arcanismo, História, Investigação, Medicina, Natureza, Percepção, Prestidigitação | Engenharia Mágica, Conjuração | Tasha 8-11 |

- **PV no 1º nível** = valor máximo do dado + mod. de CON (p. 12). Depois, por nível: rolar o dado ou
  usar o valor fixo (metade do dado + 1) + CON (p. 15).
- Proficiência +2 no 1º nível (o app calcula pelo nível).
- Escolhas do 1º nível que mudam a ficha: Especialização do ladino (2 perícias com `grau` 2), Estilo de
  Luta (ex. Defesa: +1 CA), Defesa sem Armadura (CA = 10 + DES + CON ou SAB), domínio do clérigo e
  origem do feiticeiro (podem dar proficiências e magias), patrono do bruxo.
- Recursos com contador vão em `recursos` (`recupera`: "curto" ou "longo"): Fúria (2, longo), Inspiração
  de Bardo (CAR vezes, longo), Retomar o Fôlego (1, curto), Sentido Divino (1 + CAR, longo), Cura pelas
  Mãos (5 × nível, longo), Recuperação Arcana (1, longo). Confira no texto da classe.

## 4. Valores de habilidade (p. 13; modificador p. 173)
Três métodos, à escolha do jogador e do mestre:
- **Conjunto padrão**: 15, 14, 13, 12, 10, 8.
- **Compra de pontos** (variação, p. 13): 27 pontos; custo 8=0, 9=1, 10=2, 11=3, 12=4, 13=5, 14=7, 15=9.
  Nenhum valor abaixo de 8 nem acima de 15 antes da raça.
- **Rolagem**: 4d6, descarta o menor, seis vezes. Se for rolar, role de verdade (ou peça ao jogador os
  números) e mostre os dados.
Depois some os aumentos da raça. Modificador = (valor − 10) ÷ 2, para baixo. Máximo 20.
Diga ao jogador quais atributos importam para a classe (o "Sumário de Valores de Habilidade" na p. 12).

## 5. Antecedente (cap. 4, p. 125-141) e descrição
Cada antecedente dá 2 perícias, idiomas ou ferramentas, equipamento e uma característica:
| Antecedente | Perícias | Pág. |
|---|---|---|
| Acólito | Intuição, Religião | 127 |
| Artesão de Guilda | Intuição, Persuasão | 128 |
| Artista | Acrobacia, Atuação | 129 |
| Charlatão | Enganação, Prestidigitação | 131 |
| Criminoso | Enganação, Furtividade | 132 |
| Eremita | Medicina, Religião | 133 |
| Forasteiro | Atletismo, Sobrevivência | 134-135 |
| Herói do Povo | Adestrar Animais, Sobrevivência | 135 |
| Marinheiro | Atletismo, Percepção | 136 |
| Nobre | História, Persuasão | 137-138 |
| Órfão | Furtividade, Prestidigitação | 138-139 |
| Sábio | Arcanismo, História | 139 |
| Soldado | Atletismo, Intimidação | 140 |
Se a perícia do antecedente repetir uma da classe ou raça, escolha outra (p. 125, "Personalizando um
Antecedente"). Tendência, traços de personalidade, ideal, vínculo e defeito (tabelas do antecedente)
vão numa característica "Personalidade" em `caracteristicas`.

## 6. Equipamento (cap. 5, p. 143-157)
Equipamento inicial da classe + do antecedente, ou o ouro inicial da classe (p. 143) para comprar.
CA (p. 144-145): sem armadura 10 + DES; couro 11 + DES; couro batido 12 + DES; armaduras médias com DES
máx. +2 (gibão de peles 12, camisão de malha 13, brunea 14, peitoral 14, meia-armadura 15); pesadas sem
DES (cota de malha 16, cota de talas 17, placas 18; cota de anéis veja a p. 145); escudo +2.
A CA é digitada na ficha (`combate.ca`). Armas na p. 149: o ataque pode ser escrito `FOR` ou `DES`
(o app soma modificador + proficiência) e o dano `1d8+FOR cortante`.

## 7. Magia (cap. 10-11; CD = 8 + prof. + mod., p. 205)
O app calcula CD e ataque pelo atributo da classe. Espaços de 1º nível: bardo, clérigo, druida,
feiticeiro, mago 2; bruxo 1 (Magia de Pacto); artífice 2; paladino e patrulheiro nenhum até o 2º nível.
Truques e magias no 1º nível (confira na tabela da classe): bardo 2 truques e 4 magias; bruxo 2 e 2;
clérigo 3 truques e prepara SAB + nível; druida 2 truques e prepara SAB + nível; feiticeiro 4 e 2;
mago 3 truques, 6 magias no grimório e prepara INT + nível. Listas de magias por classe (cap. 11):
bardo p. 207, bruxo e clérigo p. 208, druida p. 209, feiticeiro e mago p. 210, paladino e patrulheiro
logo depois; a descrição de cada magia vem em ordem alfabética a partir da p. 211 (use `--buscar`).
Magias de domínio, patrono ou juramento ficam sempre preparadas e não contam no limite: anote na
descrição "(sempre preparada)".
Cada magia: `{"nome", "nivel": 0-9 (0 = truque), "descricao": resumo seu}`.

## 8. Acima do 1º nível (p. 15)
Some PV por nível, adicione as características de cada nível da tabela da classe, subclasse (geralmente
no 3º; clérigo, feiticeiro e bruxo no 1º; mago e druida no 2º), Incremento no Valor de Habilidade
(+2 num atributo ou +1 em dois, ou um talento; níveis 4, 8, 12, 16, 19 e extras do guerreiro e ladino) e os
espaços de magia da tabela. O script confere PV fixos, resistências e espaços pelo nível.

## 9. Formato do arquivo de escolhas
```json
{
  "sistema": "dnd5e",
  "nome": "Bruenor", "jogador": "Bob",
  "classe": "Guerreiro", "nivel": 1, "raca": "Anão da montanha", "antecedente": "Herói do Povo",
  "tendencia": "Leal e Bom", "experiencia": 0,
  "atributos": {"forca": {"valor": 17}, "destreza": {"valor": 10}, "constituicao": {"valor": 16},
                "inteligencia": {"valor": 8}, "sabedoria": {"valor": 13}, "carisma": {"valor": 12}},
  "resistencia": {"forca": {"proficiente": true}, "constituicao": {"proficiente": true}},
  "pericias": {"Atletismo": {"grau": 1}, "Intimidação": {"grau": 1}},
  "combate": {"hp_max": 13, "ca": 16, "deslocamento": "7,5m", "dados_vida": {"dado": "d10"}},
  "magias": {"slots": {"1": {"max": 0}}, "lista": []},
  "ataques": [{"nome": "Machado de batalha", "ataque": "FOR", "dano": "1d8+FOR cortante", "descricao": "versátil (1d10)"}],
  "caracteristicas": [{"nome": "Estilo de Luta: Defesa", "detalhes": "+1 na CA usando armadura."}],
  "recursos": [{"nome": "Retomar o Fôlego", "atual": 1, "max": 1, "recupera": "curto", "detalhes": "1d10 + nível de PV"}],
  "idiomas": "Comum, Anão", "proficiencias": "Todas as armaduras, escudos, armas simples e marciais, ferramentas de ferreiro",
  "inventario": ["Cota de malha", "Machado de batalha", "Pacote de aventureiro", "10 po"]
}
```
`grau` da perícia: 1 proficiente, 2 especialista. Enganação pode vir pelo nome (a chave interna é
`blefar`). Para espaços, `slots` vai de "1" a "9" com `max` (o `atual` começa igual).
