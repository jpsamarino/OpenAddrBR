import json
import math

from openaddrbr.core.models._models import CutHypothesis, TokenStats
from openaddrbr.utils._text import normalize_text


class AddressCutter:
    def __init__(self, json_path: str, alpha: float = 1.0):
        self.stats: dict[str, dict[str, dict[str, TokenStats]]] = {}
        self.weights: dict[str, float] = {}

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        raw_tokens = data.get("tokens", {})

        total_global: dict[str, dict[str, int]] = {}
        total_token: dict[str, int] = {}

        for token, roles in raw_tokens.items():
            token_count = 0
            for role, positions in roles.items():
                if role not in total_global:
                    total_global[role] = {}
                for pos, stats in positions.items():
                    qt_entities = stats["qt_entities"]
                    token_count += qt_entities
                    total_global[role][pos] = total_global[role].get(pos, 0) + qt_entities
            total_token[token] = token_count

        role_totals: dict[str, int] = {
            role: sum(pos_counts.values()) for role, pos_counts in total_global.items()
        }

        for token, roles in raw_tokens.items():
            self.weights[token] = math.log(total_token[token] + 1)
            self.stats[token] = {}
            for role, positions in roles.items():
                self.stats[token][role] = {}
                num_positions = len(total_global.get(role, {}))

                token_role_total = sum(p["qt_entities"] for p in positions.values())
                role_total = role_totals.get(role, 0)

                for pos, stats in positions.items():
                    qt_entities = stats["qt_entities"]
                    p_pos_given_token = (qt_entities + alpha) / (
                        token_role_total + alpha * num_positions
                    )
                    p_media = total_global[role][pos] / role_total if role_total > 0 else 1e-5
                    llr = math.log(p_pos_given_token / p_media)
                    std = max(stats["std"], 0.5)
                    self.stats[token][role][pos] = TokenStats(
                        llr=llr, mean=stats["mean"], std=std, qt_entities=qt_entities
                    )

    def _calculate_score(self, street_tokens: list[str]) -> float:
        score = 0.0
        L = len(street_tokens)
        if L == 0:
            return score

        for i, token in enumerate(street_tokens):
            if L == 1:
                pos = "single"
            elif i == 0:
                pos = "start"
            elif i == L - 1:
                pos = "end"
            else:
                pos = "middle"

            token_stats = self.stats.get(token, {}).get("street", {}).get(pos)
            weight = self.weights.get(token, 0.0)

            if not token_stats:
                # OOV Penalty: Harsh wall to prevent absorbing unknown neighborhood words into the middle of the street.
                score -= 10.0
                continue

            llr = token_stats.llr
            mean = token_stats.mean
            std = token_stats.std
            gaussian_penalty = -((L - mean) ** 2) / (2 * (std**2))

            # Limiting negative LLR penalty for valid abbreviations
            token_score = max((llr * weight), -3.0) + gaussian_penalty

            # House Number Rule: In Brazil, if a street ends in a bare number, it's often a house number.
            if pos == "end" and token.isdigit():
                qt = token_stats.qt_entities
                token_score -= 20.0 / (1.0 + math.log(qt + 1))

            score += token_score

        return score

    def cut(self, query: str) -> list[CutHypothesis]:
        if not query:
            return []

        hypotheses = []

        # 1. Hard Cut by Comma
        if "," in query:
            parts = query.split(",", 1)
            street_str = normalize_text(parts[0])
            rest_str = normalize_text(parts[1])
            street_tokens = street_str.split()
            rest_tokens = rest_str.split()
            score = self._calculate_score(street_tokens)
            hypotheses.append(CutHypothesis(" ".join(street_tokens), " ".join(rest_tokens), score))
            return hypotheses

        norm_query = normalize_text(query)
        tokens = norm_query.split()
        if not tokens:
            return []

        # 2. Statistical Sliding (Probabilistic evaluation of everything else)
        for i in range(1, len(tokens) + 1):
            street_tokens = tokens[:i]
            rest_tokens = tokens[i:]
            score = self._calculate_score(street_tokens)

            # Transition Bonus
            if rest_tokens:
                transition_token = rest_tokens[0]
                t_weight = self.weights.get(transition_token, 0.0)
                if any(c.isdigit() for c in transition_token):
                    score += 15.0
                else:
                    best_t_score = 0.0
                    for role in ["neighborhood", "city"]:
                        for pos in ["start", "single"]:
                            t_stats = self.stats.get(transition_token, {}).get(role, {}).get(pos)
                            if t_stats:
                                t_score = t_stats.llr * t_weight
                                if t_score > best_t_score:
                                    best_t_score = t_score
                    score += best_t_score

            hypotheses.append(CutHypothesis(" ".join(street_tokens), " ".join(rest_tokens), score))

        hypotheses.sort(key=lambda h: h.score, reverse=True)
        return hypotheses
