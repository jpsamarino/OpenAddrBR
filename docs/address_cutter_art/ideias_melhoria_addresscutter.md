# Ideias para Melhorar o AddressCutter

Baseado na análise dos gaps do benchmark e do código:

| Cenário de Ruído | Gap Top-1 (vs Clean) | Gap Top-3 (vs Clean) | Prioridade |
|---|---|---|---|
| **Token Gluing** | -4.11 p.p. | **-11.92 p.p.** | 🔴 Máxima (destrói Top-3) |
| **Typo** | **-9.34 p.p.** | -0.54 p.p. | 🔴 Alta (destrói Top-1) |
| **Drop Prefix** | -8.76 p.p. | +0.00 p.p. | 🟡 Média (Top-3 OK) |

---

## Ideia 1: Character N-Gram LLR para Tokens OOV (Anti-Typo)

**Problema:** Quando o usuário digita `JSE` ao invés de `JOSE`, o token não existe no corpus e recebe a penalidade OOV fixa de -10.0. Todas as outras evidências da rua ficam incapazes de compensar.

**Hipótese:** Mesmo com um typo, os **trigramas de caracteres** do token parcialmente correto ainda carregam informação. `JSE` contém os trigramas `_JS`, `JSE`, `SE_` — dos quais `SE_` aparece em milhares de tokens de rua (`JOSE`, `SERAFIM`, ...). Se pré-computarmos o LLR médio dos trigramas de cada posição no corpus, podemos dar ao token OOV uma penalidade **informada** ao invés de fixa.

**Implementação:**
```python
# No __init__, pré-computar:
self.trigram_stats: dict[tuple[str, int, int], float] = {}  # (trigram, role, pos) -> avg_llr

# Em _score_street, quando OOV:
if not ts:
    # Ao invés de score += self.oov_penalty:
    trigrams = char_trigrams(token)  # ["_JS", "JSE", "SE_"]
    evidence = [self.trigram_stats.get((tg, Role.STREET, pos), 0) for tg in trigrams]
    score += max(sum(evidence) / len(evidence), self.oov_penalty)  # Bounded below
```

**Custo:** ~2-5 lookups em dict por token OOV. Negligível (<0.001ms).

**Impacto esperado:** +3-5 p.p. no Top-1 de Typos. O Top-3 já é 98.19%, então ganho incremental ali.

---

## Ideia 2: Smart Split Adaptativo com Vocabulário (Anti-Gluing++)

**Problema:** O Smart Split atual usa um threshold fixo de 2 caracteres. Isso funciona bem para `PAULISTA1500`, mas falha em `PAULISTA1A` (sufixo curto), e pode splittar incorretamente tokens legítimos que contêm dígitos.

**Hipótese:** Ao invés de decidir pelo comprimento, consultar o **vocabulário** durante o split. Se a parte alfabética do token colado existe no corpus como token de rua, splittar. Se o token inteiro existe no corpus (ex: `KM2`, `10A`), manter junto.

**Implementação:**
```python
def _tokenize(self, text: str) -> list[str]:
    raw_tokens = text.split()
    final_tokens = []
    for token in raw_tokens:
        if token.isalpha() or token.isdigit():
            final_tokens.append(token)
            continue
        
        parts = [p for p in re.split(r'(\d+)', token) if p]
        
        # NOVO: Checar se o token inteiro é conhecido
        if token in self.weights:
            final_tokens.append(token)
            continue
            
        # NOVO: Checar se a parte alfa é conhecida
        alpha_parts = [p for p in parts if p.isalpha()]
        if any(p in self.weights for p in alpha_parts):
            final_tokens.extend(parts)
        else:
            final_tokens.append(token)  # Desconhecido, manter junto
            
    return final_tokens
```

**Custo:** 1 lookup no dict `self.weights` por token misto. Zero custo para tokens puros.

**Impacto esperado:** +2-4 p.p. no Top-3 de Token Gluing (o gap atual é -11.92 p.p.).

---

## Ideia 3: Prefixo Implícito (Tipo de Logradouro Inferido)

**Problema:** Quando o usuário omite o prefixo (`COSTA` ao invés de `RUA COSTA`), o token que seria `MIDDLE` ou `END` é forçado a ser `START`, onde seu LLR é baixo ou negativo. Gap: -8.76 p.p. Top-1.

**Hipótese:** Se o primeiro token da hipótese de rua NÃO é um prefixo conhecido (RUA, AV, etc.), e é encontrado no corpus predominantemente como `MIDDLE` ou `END` de rua, adicionar um **bônus de prefixo implícito** — como se houvesse um token fantasma `<PREFIX>` antes dele.

**Implementação:**
```python
KNOWN_PREFIXES = {"RUA", "AVENIDA", "AV", "TRAVESSA", "ALAMEDA", "ESTRADA", ...}

def _score_street(self, tokens, start, end):
    L = end - start
    # NOVO: Se o primeiro token não é prefixo, ajustar posições
    has_prefix = tokens[start] in KNOWN_PREFIXES if L > 0 else False
    
    for i in range(start, end):
        if not has_prefix and i == start and L > 1:
            # Testar o token como MIDDLE ao invés de START
            pos_alt = Pos.MIDDLE
            ts_alt = self.stats.get((token, Role.STREET, pos_alt))
            if ts_alt and ts_alt.llr > (ts.llr if ts else -999):
                ts = ts_alt
                pos = pos_alt
        ...
```

**Custo:** 1 comparação extra + 1 lookup no primeiro token. Negligível.

**Impacto esperado:** +3-5 p.p. no Top-1 de Drop Prefix.

---

## Ideia 4: Bigramas Posicionais Leves (Transição entre Tokens)

**Problema:** O modelo trata cada token como independente (suposição naive). Isso ignora pares fortes como `NOSSA→SENHORA`, `SAO→JOSE`, `VINTE→CINCO`. Quando um dos tokens do par está correto, ele deveria "puxar" o outro.

**Hipótese:** Pré-computar um **bônus de bigrama** para pares adjacentes que coocorrem frequentemente em ruas. Não substitui o LLR individual — apenas soma um bônus quando o par é encontrado.

**Implementação:**
```python
# No __init__:
# Só pré-computar bigramas com coocorrência > threshold (ex: 50 entidades)
self.bigram_bonus: dict[tuple[str, str], float] = {}

# Em _score_street, após computar token_score:
if i > start:
    prev_token = tokens[i - 1]
    bigram_key = (prev_token, token)
    bonus = self.bigram_bonus.get(bigram_key, 0.0)
    score += bonus
```

**Custo:** 1 lookup no dict por par. ~0.001ms por query.

**Tamanho:** Filtrando por coocorrência > 50, estimo ~5-10k bigramas. ~200KB em memória.

**Impacto esperado:** +1-2 p.p. no Top-1 geral. Mais visível em ruas compostas longas.

---

## Ideia 5: Weight com Saturação BM25-style

**Problema:** O peso atual `Weight = log(freq + 1)` cresce sem limite. Tokens ultra-frequentes como `DE` (190k entidades!) dominam a pontuação com weight ≈ 12.16, enquanto um nome raro mas informativo como `SAMARITANO` (50 entidades) tem weight ≈ 3.93. A palavra `DE` contribui 3× mais para o score apesar de ser 3× menos informativa.

**Hipótese:** Aplicar saturação estilo BM25 para limitar a influência de tokens ultra-frequentes:

```python
# Atual:
weight = math.log(freq + 1)

# Proposta (BM25-style saturation):
k = 500  # ponto de saturação
weight = math.log(freq + 1) * (k / (k + freq))
```

Com `k=500`:
- `DE` (190k): 12.16 × 0.0026 = **0.032** (esmagado)
- `SAMARITANO` (50): 3.93 × 0.91 = **3.57** (quase intacto)

**Custo:** Zero (troca de fórmula no `__init__`).

**Impacto esperado:** Melhor discriminação em ruas com nomes raros. Difícil estimar sem testar, mas ~+0.5-1.5 p.p. Top-1.

> [!WARNING]
> Essa mudança pode **piorar** o desempenho se palavras funcionais como `DE`, `DA` estiverem ajudando o modelo. Testar com sweep de `k`.

---

## Ideia 6: Comma-Split Inteligente para Múltiplos Delimitadores

**Problema:** O código atual ([_address_cutter.py:272](file:///d:/projetos/OpenAddrBR/openaddrbr/core/_address_cutter.py#L272)) faz hard-cut na vírgula e retorna uma única hipótese. Mas usuários podem usar outros delimitadores: `-`, `/`, `\`, ou até múltiplas vírgulas.

**Hipótese:** Expandir o reconhecimento de delimitadores explícitos. Se a query contém um delimitador, usá-lo como **forte evidência** de fronteira (bônus alto), mas ainda gerar hipóteses alternativas.

**Implementação:**
```python
DELIMITERS = {",", " - ", " / "}

def cut(self, query):
    for delim in DELIMITERS:
        if delim in query:
            parts = query.split(delim, 1)
            # Gerar hipótese com bônus alto, mas NÃO retornar só ela
            # Continuar com o sliding window normal
            break
```

**Custo:** Negligível (1-3 string checks).

**Impacto esperado:** Marginal no benchmark atual (pouca vírgula nos dados), mas importante para produção.

---

## Priorização Sugerida

| # | Ideia | Impacto Esperado | Esforço | Risco |
|---|---|---|---|---|
| 1 | **Smart Split Adaptativo** | 🔴 Alto (Token Gluing Top-3) | 🟢 Baixo | 🟢 Baixo |
| 2 | **Prefixo Implícito** | 🔴 Alto (Drop Prefix Top-1) | 🟢 Baixo | 🟡 Médio |
| 3 | **Char N-Gram LLR** | 🔴 Alto (Typo Top-1) | 🟡 Médio | 🟡 Médio |
| 4 | **Bigramas** | 🟡 Médio | 🟡 Médio | 🟢 Baixo |
| 5 | **BM25 Saturation** | 🟡 Incerto | 🟢 Baixo | 🔴 Alto |
| 6 | **Multi-delimiter** | 🟢 Baixo (benchmark) | 🟢 Baixo | 🟢 Baixo |

Todas são **testáveis independentemente** com o mesmo benchmark de 100k queries + seed fixa.
