"""AddressCutter: Positional Naive Bayes street name boundary detector.

Scores every possible split point in a query string to find where the street
name ends and the rest (house number, neighborhood, city) begins.

Scoring Model
─────────────
For each candidate split, two scores are combined:

  score(split) = street_score(tokens[:i]) + transition_score(tokens[i:])

Street score is the sum of per-token scores using Positional Naive Bayes:

  token_score = max(LLR × weight, LLR_FLOOR) + gaussian_penalty
  gaussian_penalty = -(L - μ)² / (2σ²)

  where L     = number of tokens in the street hypothesis
        μ, σ  = mean/std of street length when this token appears at this position
        LLR   = log(P(pos|token) / P(pos|corpus))  — log-likelihood ratio
        weight = log(total_frequency + 1)            — global token importance

Special rules applied per-token:
  • OOV (out-of-vocabulary):     flat penalty (default -10.0)
  • House number (trailing digit): HOUSE_NUMBER_BASE / (1 + log(qt_entities + 1))
    — progressively lighter for digits that genuinely belong to street names

Transition score evaluates the rest tokens as neighborhood/city candidates:
  • If rest starts with a digit → +HOUSE_NUMBER_BONUS (high-confidence boundary)
  • Otherwise → average best LLR×weight across all rest tokens as neigh/city,
    dampened by ×NO_DIGIT_DAMPING when the query contains no digits (street-only typing)
"""

import json
import math

from openaddrbr.core.models._models import AddressKey, CutHypothesis, Pos, Role, TokenStats
from openaddrbr.utils._text import normalize_text


class AddressCutter:
    _ROLE_KEYS = ("street", "neighborhood", "city")
    _POS_LOOKUP = {"start": Pos.START, "middle": Pos.MIDDLE, "end": Pos.END, "single": Pos.SINGLE}
    _TRANSITION_ROLES = (Role.NEIGHBORHOOD, Role.CITY)

    @staticmethod
    def gaussian_penalty(L: int, mean: float, std: float) -> float:
        """Penalizes street length hypotheses that deviate from the token's typical street length."""
        return -((L - mean) ** 2) / (2 * std**2)

    @staticmethod
    def house_number_penalty(qt_entities: int, base: float) -> float:
        """Progressive penalty: common street-ending digits (e.g. '2') get almost no penalty,
        rare ones (e.g. '1200') get penalized heavily."""
        return base / (1.0 + math.log(qt_entities + 1))

    def _tokenize(self, text: str) -> list[str]:
        raw_tokens = text.split()
        import re
        final_tokens = []
        for token in raw_tokens:
            if token.isalpha() or token.isdigit():
                final_tokens.append(token)
                continue
                
            parts = [p for p in re.split(r'(\d+)', token) if p]
            
            # Se o token misto já existe no vocabulário oficial, mantém junto
            if token in self.weights:
                final_tokens.append(token)
                continue
                
            # Checar se a parte alfabética existe no vocabulário
            alpha_parts = [p for p in parts if p.isalpha()]
            if any(p in self.weights for p in alpha_parts):
                final_tokens.extend(parts)
            else:
                # Comportamento fallback antigo do gluing_threshold
                if self.gluing_threshold is not None and any(len(p) > self.gluing_threshold for p in alpha_parts):
                    final_tokens.extend(parts)
                else:
                    final_tokens.append(token)
        return final_tokens

    @staticmethod
    def token_position(index: int, length: int) -> int:
        """Maps a token's index within a sequence to its positional enum (int)."""
        if length == 1:
            return Pos.SINGLE
        if index == 0:
            return Pos.START
        if index == length - 1:
            return Pos.END
        return Pos.MIDDLE

    def __init__(
        self,
        json_path: str,
        alpha: float = 1.0,
        *,
        oov_penalty: float = -10.0,
        llr_floor: float = -3.0,
        house_number_base: float = -20.0,
        house_number_bonus: float = 15.0,
        no_digit_damping: float = 0.2,
        gluing_threshold: int | None = 2,
        use_kelly: bool = True,
        kelly_min: float = 0.30,
        kelly_decay: float = 2.0,
    ):
        # Tunable scoring constants — override via __init__ or mutate on instance
        self.oov_penalty = oov_penalty
        self.llr_floor = llr_floor
        self.house_number_base = house_number_base
        self.house_number_bonus = house_number_bonus
        self.no_digit_damping = no_digit_damping
        self.gluing_threshold = gluing_threshold
        self.use_kelly = use_kelly
        self.kelly_min = kelly_min
        self.kelly_decay = kelly_decay

        with open(json_path, "r", encoding="utf-8") as f:
            raw_tokens = json.load(f).get("tokens", {})

        # Pass 1: Corpus-wide totals for LLR denominators.
        global_counts = [[0] * len(Pos) for _ in range(len(Role))]
        token_totals: dict[str, int] = {}

        for token, roles in raw_tokens.items():
            token_count = 0
            for r, role_key in enumerate(self._ROLE_KEYS):
                for pos_str, stats in roles.get(role_key, {}).items():
                    qt = stats["qt_entities"]
                    token_count += qt
                    global_counts[r][self._POS_LOOKUP[pos_str]] += qt
            token_totals[token] = token_count

        role_totals = [sum(rc) for rc in global_counts]

        # Pass 2: Build self.stats & self.weights
        self.stats: dict[AddressKey, TokenStats] = {}
        self.weights: dict[str, float] = {}

        for token, roles in raw_tokens.items():
            self.weights[token] = math.log(token_totals[token] + 1)

            for r, role_key in enumerate(self._ROLE_KEYS):
                positions = roles.get(role_key)
                if not positions:
                    continue

                num_pos = sum(1 for p in global_counts[r] if p > 0)
                token_role_total = sum(p["qt_entities"] for p in positions.values())
                rt = role_totals[r]

                for pos_str, stats in positions.items():
                    p = self._POS_LOOKUP[pos_str]
                    qt = stats["qt_entities"]
                    p_token = (qt + alpha) / (token_role_total + alpha * num_pos)
                    p_corpus = global_counts[r][p] / rt if rt > 0 else 1e-5
                    llr = math.log(p_token / p_corpus)
                    std = max(stats["std"], 3.5) if qt < 5 else max(stats["std"], 0.5)
                    self.stats[AddressKey(token, r, p)] = TokenStats(
                        llr=llr,
                        mean=stats["mean"],
                        std=std,
                        qt_entities=qt,
                    )

        # Build SymSpell index for top 5000 tokens to allow typo tolerance
        self.typo_map: dict[str, str] = {}
        # Sort tokens by frequency descending
        top_tokens = sorted(token_totals.items(), key=lambda x: x[1], reverse=True)[:5000]
        for token, count in top_tokens:
            if len(token) < 4:
                continue
            if token not in self.typo_map:
                self.typo_map[token] = token
            for i in range(len(token)):
                d = token[:i] + token[i+1:]
                if d not in self.typo_map:
                    self.typo_map[d] = token

    def _find_closest_typo(self, token: str):
        if len(token) < 3:
            return None
        if token in self.typo_map:
            return self.typo_map[token]
        # Check distance 2 (which covers edit dist 1 of query vs edit dist 1 of dict)
        for i in range(len(token)):
            d = token[:i] + token[i+1:]
            if d in self.typo_map:
                return self.typo_map[d]
        return None

    def _get_stats_with_fallback(self, token: str, pos: Pos):
        ts = self.stats.get((token, Role.STREET, pos))
        if not ts:
            # Anti-Drop Prefix: Permite flexibilidade de posição para o street matching
            if pos == Pos.SINGLE:
                ts = (self.stats.get((token, Role.STREET, Pos.END)) or 
                      self.stats.get((token, Role.STREET, Pos.START)) or 
                      self.stats.get((token, Role.STREET, Pos.MIDDLE)))
            elif pos == Pos.END:
                ts = (self.stats.get((token, Role.STREET, Pos.SINGLE)) or 
                      self.stats.get((token, Role.STREET, Pos.MIDDLE)) or 
                      self.stats.get((token, Role.STREET, Pos.START)))
            elif pos == Pos.START:
                ts = (self.stats.get((token, Role.STREET, Pos.MIDDLE)) or 
                      self.stats.get((token, Role.STREET, Pos.END)) or 
                      self.stats.get((token, Role.STREET, Pos.SINGLE)))
            elif pos == Pos.MIDDLE:
                ts = (self.stats.get((token, Role.STREET, Pos.START)) or 
                      self.stats.get((token, Role.STREET, Pos.END)) or 
                      self.stats.get((token, Role.STREET, Pos.SINGLE)))
        return ts


    def _score_street(self, tokens: list[str], start: int, end: int) -> float:
        """Positional Naive Bayes score for a street name hypothesis."""
        L = end - start
        if L == 0:
            return 0.0

        score = 0.0
        for i in range(start, end):
            token = tokens[i]
            pos = self.token_position(i - start, L)

            ts = self._get_stats_with_fallback(token, pos)
            typo_penalty = 0.0

            if not ts:
                corrected = self._find_closest_typo(token)
                if corrected:
                    ts = self._get_stats_with_fallback(corrected, pos)
                    if ts:
                        token = corrected # Use the corrected token's weight
                        typo_penalty = -2.0 # Apply a small penalty for the typo instead of -10.0
                
                if not ts:
                    # Contextual penalty: if this is the very last token in the entire query,
                    # it might be an incomplete word being typed, or a house number.
                    # We penalize it much less (-1.0) than a true OOV in the middle (-10.0).
                    if i == len(tokens) - 1:
                        score += -1.0
                    else:
                        score += self.oov_penalty
                    continue

            llr, mean, std, qt_entities = ts
            weight = self.weights.get(token, 0.0)

            gaussian = self.gaussian_penalty(L, mean, std)

            if self.use_kelly and llr < 0:
                kelly_fraction = self.kelly_min + (1.0 - self.kelly_min) * math.exp(llr / self.kelly_decay)
                final_llr = llr * kelly_fraction
            else:
                final_llr = max(llr, self.llr_floor)

            token_score = (final_llr * weight) + gaussian + typo_penalty

            if pos == Pos.END and token.isdigit():
                token_score += self.house_number_penalty(qt_entities, self.house_number_base)

            score += token_score

        return score

    def _score_transition(
        self, tokens: list[str], start: int, end: int, has_any_digit: bool
    ) -> float:
        """Bilateral evaluation of rest tokens as neighborhood/city candidates."""
        R = end - start
        if R == 0:
            return 0.0

        if any(c.isdigit() for c in tokens[start]):
            return self.house_number_bonus

        total = 0.0
        for i in range(start, end):
            token = tokens[i]
            weight = self.weights.get(token)
            if weight is None:
                continue

            pos = self.token_position(i - start, R)
            check = (pos,)
            if pos == Pos.SINGLE:
                check = (Pos.SINGLE, Pos.START)
            elif pos == Pos.START:
                check = (Pos.START, Pos.SINGLE)
            elif pos == Pos.END:
                check = (Pos.END, Pos.MIDDLE)

            best = 0.0
            for role in self._TRANSITION_ROLES:
                for p in check:
                    ts = self.stats.get((token, role, p))
                    if not ts:
                        if p == Pos.SINGLE:
                            ts = self.stats.get((token, role, Pos.END))
                        elif p == Pos.END:
                            ts = self.stats.get((token, role, Pos.SINGLE))
                            
                    if ts:
                        if self.use_kelly and ts.llr < 0:
                            kelly_fraction = self.kelly_min + (1.0 - self.kelly_min) * math.exp(ts.llr / self.kelly_decay)
                            llr = ts.llr * kelly_fraction
                        else:
                            llr = max(ts.llr, self.llr_floor)
                            
                        s = llr * weight
                        if s > best:
                            best = s
            total += best

        avg = total / R
        if not has_any_digit:
            avg *= self.no_digit_damping
        return avg

    def cut(self, query: str) -> list[CutHypothesis]:
        """Return all possible street/rest splits, ranked by score (best first)."""
        if not query:
            return []

        has_digit = any(c.isdigit() for c in query)

        # Hard cut: commas are explicit delimiters
        if "," in query:
            street, rest = (normalize_text(p).strip() for p in query.split(",", 1))
            s_tok, r_tok = self._tokenize(street), self._tokenize(rest)
            all_tok = s_tok + r_tok
            split = len(s_tok)
            score = self._score_street(all_tok, 0, split) + self._score_transition(
                all_tok, split, len(all_tok), has_digit
            )
            return [CutHypothesis(street, rest, score)]

        norm_query = normalize_text(query)
        tokens = self._tokenize(norm_query)
        N = len(tokens)
        if N == 0:
            return []

        # Sliding window — score using indices, materialize strings after sorting
        scored: list[tuple[int, float]] = []
        for i in range(1, N + 1):
            score = self._score_street(tokens, 0, i) + self._score_transition(
                tokens, i, N, has_digit
            )
            scored.append((i, score))

        scored.sort(key=lambda x: x[1], reverse=True)

        return [
            CutHypothesis(" ".join(tokens[:i]), " ".join(tokens[i:]), score) for i, score in scored
        ]
