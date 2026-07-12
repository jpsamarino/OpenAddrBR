# Uma Abordagem Posicional Naive-Bayes para Address Parsing e Segmentação de Sequências utilizando Marcação BILOU

**Resumo**
A padronização e estruturação de endereços (*Address Parsing*) é um desafio clássico em Sistemas de Informação Geográfica (GIS) e Processamento de Linguagem Natural (NLP). Devido à alta variabilidade na digitação humana, uso de abreviações e ausência de delimitadores estritos, regras heurísticas tradicionais falham frequentemente. Este artigo propõe uma arquitetura estocástica leve (*AddressCutter*), que utiliza pontuação Naive Bayes posicional e um esquema inspirado na marcação BILOU (Begin, Inside, Last, Outside, Unit) para segmentar strings caóticas e parciais em logradouro, número e bairro. A solução inclui um decaimento exponencial suave para tolerância a erros tipográficos e heurísticas contextuais baseadas no léxico, atingindo uma precisão de 98.96% no Top 3 em um benchmark de 100.000 buscas com ruído de mundo real injetado.

---

## 1. Introdução

Sistemas de busca e autocompletar lidam diariamente com strings de endereços digitadas por humanos. Em muitos sistemas legados ou caixas de busca de texto livre, o usuário pode digitar strings como `RUA PAU`, `PAULISTA1500`, ou `JSE COSTA`, sem delimitar o que é rua e o que é número da casa ou bairro.

O desafio de fatiar e rotular cada componente de uma string não-estruturada é conhecido na literatura como **Address Parsing** ou **Token Classification** (Classificação de Tokens). Modelos profundos (Redes Neurais / Transformers) resolvem este problema com maestria, mas com um alto custo computacional e latência incompatível com sistemas de *autocomplete* em tempo real.

### 1.1. O Problema de Escala: Por que um Pré-Filtro?

Em uma arquitetura de busca de endereços completa, modelos de alta precisão — como motores de busca textual (ex: Tantivy) ou modelos de embedding semântico — são tipicamente **100× mais lentos** que um classificador estatístico leve. Se a query bruta `PAULISTA1500 BELA VISTA` for enviada diretamente a um índice contendo milhões de endereços completos, o modelo pesado precisa avaliar um espaço de busca massivo.

A estratégia proposta é interpor um **pré-filtro ultrarrápido** (~0.03ms) que fatia a query em componentes semânticos *antes* de acionar o modelo pesado. Considere o seguinte exemplo concreto:

> **Query digitada:** `PAULISTA1500 BELA VISTA`
>
> **Sem pré-filtro:** Busca direta em um índice monolítico de milhões de endereços completos (rua + número + bairro + cidade). O modelo pesado avalia todas as combinações.
>
> **Com AddressCutter:** A query é fatiada em `rua = "PAULISTA"`, `número = "1500"`, `bairro = "BELA VISTA"`. O sistema consulta primeiro um **índice seletivo de ruas** — que mapeia cada nome de rua normalizado às cidades onde ela existe — reduzindo drasticamente o espaço de candidatos. Somente então o modelo pesado é acionado sobre o subconjunto filtrado.

Essa arquitetura em cascata permite que o AddressCutter tenha limitações toleráveis (como não resolver ambiguidades complexas), pois o modelo subsequente as compensa. O que importa é que o pré-filtro seja **rápido o suficiente para não adicionar latência perceptível** e **preciso o suficiente para não descartar a resposta correta** — o que nossa métrica Top-3 de 98.77% captura diretamente.

Nossa proposta aborda o problema por um prisma probabilístico puro, extraindo a fronteira semântica de divisão através de pontuações de verossimilhança (*Log-Likelihood*).

## 2. Trabalhos Relacionados

Na literatura de NLP, a extração de elementos específicos de um texto é abordada como **Reconhecimento de Entidades Nomeadas (NER)**. 

Historicamente, algoritmos estatísticos como Modelos Ocultos de Markov (*Hidden Markov Models - HMMs*) e Campos Aleatórios Condicionais (*Conditional Random Fields - CRF*) de Lafferty et al. (2001) dominaram a extração de dados antes do advento do Deep Learning. Para mapear palavras individuais para suas classes, o padrão-ouro de modelagem é o **esquema BILOU** (Ratinov and Roth, 2009), que classifica palavras como:
- **B**egin (Início da entidade)
- **I**nside (Meio da entidade)
- **L**ast (Fim da entidade)
- **O**utside (Fora da entidade)
- **U**nit (Entidade de uma única palavra)

Nossa abordagem se inspira no esquema BILOU para definir as posições semânticas dos tokens, embora opere como um **detector de fronteira** (*boundary detector*) ao invés de um classificador sequencial de tokens. A posição **O** (Outside) é tratada implicitamente pela TransitionScore (Seção 3.3), que avalia os tokens fora da hipótese de rua como candidatos a bairro ou cidade.

## 3. Metodologia (Arquitetura AddressCutter)

### 3.1. Esquema de Posições (O Padrão BILOU Adaptado)
Para calcular a probabilidade de uma palavra pertencer ao nome da rua, não basta saber se ela existe, mas sim *onde* ela costuma existir. O AddressCutter utiliza quatro marcadores posicionais nativos:
1. `START` (Análogo ao **B**egin): Palavras que abrem ruas, como "RUA", "AVENIDA", "ALAMEDA".
2. `MIDDLE` (Análogo ao **I**nside): Palavras do meio, como preposições ("DE", "DA") ou nomes compostos.
3. `END` (Análogo ao **L**ast): Sobrenomes ou indicadores de fim.
4. `SINGLE` (Análogo ao **U**nit): Palavras que compõem o nome da rua sozinhas.

### 3.2. Pontuação de Hipótese de Rua (Positional Naive Bayes)

Para qualquer ponto de corte *i* na string digitada, o modelo avalia a qualidade da hipótese "os tokens de 0 até *i* formam o nome da rua". A pontuação total de cada hipótese combina duas componentes:

$$ Score(i) = StreetScore(tokens_{0..i}) + TransitionScore(tokens_{i..N}) $$

A **StreetScore** soma a evidência posicional de cada token individualmente:

$$ StreetScore = \sum_{j=0}^{i-1} TokenScore_j $$

Para cada token, a pontuação é calculada conforme:

$$ TokenScore = f(LLR) \times Weight + GaussianPenalty $$

Onde:
- **LLR** (Log-Likelihood Ratio) = $\log\frac{P(posição \mid token)}{P(posição \mid corpus)}$ — indica se o token aparece desproporcionalmente nesta posição (START, MIDDLE, END, SINGLE) em relação à média do corpus.
- **Weight** = $\log(freq_{global} + 1)$ — importância global do token, priorizando palavras frequentes.
- **$f(LLR)$** — função de amortecimento do LLR, definida por duas variantes:
  - **Com Decaimento Suave (padrão):** quando $LLR < 0$, aplica-se a fração amortecedora (Seção 3.5.B): $f(LLR) = LLR \times Damping\_Fraction$.
  - **Com Floor Rígido (baseline):** $f(LLR) = \max(LLR, -3.0)$.

**Casos especiais por token:**
- **OOV (Out-of-Vocabulary):** tokens não encontrados no corpus recebem penalidade fixa de $-10.0$, sem passar pela função de amortecimento nem pela penalidade gaussiana.
- **Dígitos em posição final:** quando o último token da hipótese de rua é numérico, recebe penalidade progressiva $\frac{base}{1 + \log(freq + 1)}$, que é leve para dígitos que genuinamente pertencem a nomes de rua (ex: "RUA 2") e severa para números de casa capturados erroneamente.
- **Fallback posicional SINGLE↔END:** se um token não é encontrado na posição SINGLE, o modelo busca na posição END, e vice-versa — refletindo que ruas de uma palavra e últimas palavras de ruas longas compartilham distribuições similares.

> **Nota terminológica:** Utilizamos "Naive Bayes" por analogia à suposição de independência condicional entre tokens — cada token contribui independentemente para a pontuação total. Diferentemente de um classificador Naive Bayes canônico, nosso modelo não computa posteriors de classe com priors, mas sim pontua hipóteses de fronteira via somas de log-verossimilhança.

### 3.3. Pontuação de Transição (Avaliação do Resto)

Enquanto a StreetScore avalia "quão bom é este trecho como nome de rua", a **TransitionScore** avalia "quão plausível é que o resto da string seja número/bairro/cidade". Esta pontuação bilateral é fundamental para identificar fronteiras corretas.

A TransitionScore opera em dois modos:

**Modo Numérico (alta confiança):** Se o primeiro token do "resto" contém dígitos, a hipótese recebe um bônus fixo elevado ($B_{house} = +15.0$). Este é o sinal mais forte do modelo: a presença de um número imediatamente após o nome da rua é quase sempre um número de casa, confirmando a fronteira.

**Modo Textual (evidência contextual):** Se o resto começa com texto, cada token é avaliado como candidato a bairro ou cidade, utilizando o mesmo LLR posicional da StreetScore mas agora consultando as estatísticas dos papéis `NEIGHBORHOOD` e `CITY`. A pontuação final é a média do melhor $f(LLR) \times Weight$ de cada token restante, amortecida por um fator de damping $D$ quando a query inteira não contém nenhum dígito — reconhecendo que, na ausência de números, o usuário provavelmente ainda está digitando o nome da rua.

$$ TransitionScore = \begin{cases} +B_{house} & \text{se } tokens_{rest}[0] \text{ contém dígito} \\ \frac{1}{R}\sum_{j}\max_{role \in \{neigh, city\}} (f(LLR_{j,role}) \times W_j) \times D & \text{caso contrário} \end{cases} $$

Onde $B_{house} = 15.0$, $R$ é o número de tokens restantes, e $D = 0.2$ quando não há dígitos na query ($1.0$ caso contrário).

### 3.4. Penalidade Gaussiana de Comprimento
Certas palavras não apenas aparecem em posições específicas, mas também em ruas com um número previsível de palavras. O algoritmo modela a média ($\mu$) e o desvio padrão ($\sigma$) do comprimento da rua onde o token costuma ocorrer, aplicando um decaimento gaussiano para penalizar cortes artificiais:

$$ GaussianPenalty = -\frac{(L - \mu)^2}{2\sigma^2} $$

Onde $L$ é o número de tokens na hipótese de rua, e $\mu, \sigma$ são a média e desvio padrão do comprimento de ruas onde aquele token costuma ocorrer naquela posição.

### 3.5. Inovações Híbridas contra o Caos Humano

#### A. Smart Splitting (Anti-Gluing)
Usuários frequentemente omitem espaços entre letras e números (ex: `PAULISTA1500`). Isso gera tokens que nunca foram vistos no treinamento (OOV - *Out Of Vocabulary*). Nossa solução aplica um *split* em tempo de inferência condicional: se a string alfabética possuir mais de 2 caracteres (preservando assim identificadores curtos reais como `KM2` ou `10A`), ela é separada do número agressivamente.

#### B. Decaimento Exponencial Suave (Soft Floor)
Na equação original, uma palavra contendo um erro tipográfico grave (Ex: `JSE` em vez de `JOSE`) não é encontrada no corpus de LLR, sofrendo um limite rígido punitivo (Hard Floor de `-3.0`). 
Para lidar com incertezas induzidas por ruído ortográfico, propomos um amortecedor exponencial inspirado em princípios de gestão de risco. Quando o LLR é negativo (evidência contra a posição), ao invés de aplicar um floor rígido, multiplicamos o LLR por uma fração amortecedora que converge suavemente para um piso mínimo:

$$ Damping\_Fraction = k_{min} + (1 - k_{min}) \times e^{\frac{LLR}{k_{decay}}} $$

Ao configurar $k_{min} = 0.3$ e $k_{decay} = 2.0$, o modelo perdoa parcialmente palavras com evidência negativa fraca, permitindo que as outras palavras corretas da rua compensem o ruído, prevenindo a quebra do ponto de corte.

## 4. Experimentos e Resultados

O modelo foi submetido a um teste de estresse de 100.000 buscas reais brasileiras, das quais 35% foram injetadas com ruídos hostis simultâneos (remoção de prefixos, abreviações extremas e colagem de números).

**Métricas Globais Atingidas (Inferência Média de 0.03ms):**
- Acurácia Top-1: **87.64%**
- Acurácia Top-3: **98.96%**
- Mean Reciprocal Rank (MRR): **0.9318**

*A tabela abaixo demonstra a resiliência do classificador por tipo de mutação inserida:*

| Tipo de Ruído | Acurácia (Top 1) | Acurácia (Top 3) |
|---------------|------------------|------------------|
| Limpo (Clean) | 87.94%           | 98.95%           |
| Typing Number | 94.19%           | 99.00%           |
| Token Gluing  | 85.75%           | 88.85%           |
| Erro de Digitação (Typo) | 85.18% | 98.79%           |
| Omissão de Prefixo | 86.55%      | 99.20%           |
| Omissão de Preposição | 82.75%   | 98.95%           |
| Abreviatura Exagerada | 86.36%   | 98.72%           |

*Nota: As categorias de ruído não são mutuamente exclusivas — um mesmo sample pode receber múltiplas tags simultaneamente (ex: "token_gluing" ocorre dentro de cenários de "typing_number"). Os números refletem a acurácia condicional dado que aquela mutação foi aplicada.*

A métrica **Top-3** é operacionalmente relevante em contexto de autocomplete: o sistema avalia as três melhores hipóteses de corte em paralelo contra o índice de busca, e a resposta é considerada correta se pelo menos uma delas recupera o endereço desejado. Assim, o Top-3 representa a taxa efetiva de sucesso percebida pelo usuário final.

### 4.2. Estudo de Ablação

Para quantificar a contribuição individual de cada componente, desabilitamos sistematicamente cada um enquanto mantendo os demais fixos. Como baseline, incluímos uma heurística trivial que corta a string no primeiro caractere numérico. Todos os experimentos utilizam seed fixa ($seed = 42$) para reprodutibilidade.

| Configuração | Acurácia Top-1 | Δ Top-1 | Acurácia Top-3 | Δ Top-3 |
|---|---|---|---|---|
| Baseline (primeiro dígito) | 83.06% | -4.58 p.p. | — | — |
| **Modelo completo** | **87.64%** | — | **98.96%** | — |
| Sem Correção de Typos e Soft Floor | 86.04% | -1.60 p.p. | 98.62% | -0.34 p.p. |
| Sem Smart Split | 84.56% | -3.08 p.p. | 96.41% | -2.55 p.p. |

Os resultados confirmam que:
1. **Smart Split é o componente de maior impacto**, responsável por +3.08 p.p. no Top-1 e +2.55 p.p. no Top-3 — esperado dado que token gluing é um tipo de ruído altamente destrutivo.
2. **A correção de Typos baseada em Distância de Edição e Soft Floor contribuem com +1.60 p.p.** no Top-1, resgatando um grande volume de strings corrompidas sem destruir a base 'clean'.
3. **O modelo completo supera o baseline trivial em +4.58 p.p.** no Top-1, demonstrando que a decomposição posicional bilateral (StreetScore + TransitionScore) agregada às tolerâncias contextuais entrega valor massivo sobre a heurística inocente.

### 4.3. Limitações e Trabalhos Futuros

O AddressCutter apresenta limitações conhecidas:

1. **Ambiguidade rua/bairro:** Tokens que são simultaneamente nomes de rua e de bairro (ex: "CENTRO", "JARDIM") podem confundir a TransitionScore, gerando empates entre hipóteses.
2. **Dependência do corpus:** A qualidade das estatísticas LLR depende diretamente da cobertura do corpus de treinamento. Regiões sub-representadas produzem mais tokens OOV, degradando a pontuação.
3. **Independência condicional:** A suposição naive de independência entre tokens ignora coocorrências fortes (ex: "NOSSA" quase sempre precede "SENHORA"), podendo sub-pontuar sequências compostas raras.
4. **Token Gluing com sufixos curtos:** O threshold de 2 caracteres para Smart Split preserva tokens legítimos como "KM2", mas falha em separar colagens com sufixos de 1-2 letras (ex: "PAULISTA1A").

Conforme discutido na Seção 1.1, essas limitações são toleráveis no contexto de uso do AddressCutter como pré-filtro em cascata: o modelo de busca subsequente (Tantivy, embeddings) é capaz de compensá-las, desde que a resposta correta não seja descartada nas hipóteses Top-3.

## 5. Conclusão

O AddressCutter demonstra que modelos estatísticos bayesianos leves, enriquecidos com heurísticas de tolerância a ruído de domínio específico (Smart Splitting, Distância de Edição O(1), Flexibilidade de Posição de Prefixos e Decaimento Exponencial Suave), oferecem uma alternativa viável e escalável a soluções baseadas em expressões regulares, com vantagens significativas em robustez a ruído e manutenibilidade. Ao adaptar posições inspiradas no esquema BILOU à pontuação de log-verossimilhança bilateral (StreetScore + TransitionScore), alcançamos uma arquitetura adequada para cenários de autocompletar em tempo real, casando alta robustez semântica (98.96% Top-3) com latência média de 0.03ms por query.

---
## Referências

1. Lafferty, J., McCallum, A., Pereira, F. (2001). *Conditional Random Fields: Probabilistic Models for Segmenting and Labeling Sequence Data*. ICML.
2. Ratinov, L., Roth, D. (2009). *Design Challenges and Misconceptions in Named Entity Recognition*. CoNLL.
3. Comber, S., Arribas-Bel, D. (2019). *Machine learning innovations in address matching: A practical comparison of word2vec and CRFs*. Transactions in GIS.
4. Libpostal. (2016). *International street address NLP using statistical NLP and open data*. https://github.com/openvenues/libpostal

