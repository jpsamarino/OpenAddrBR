import json
import math
from openaddrbr.core.models._models import TokenStats, CutHypothesis
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
            
        role_totals: dict[str, int] = {role: sum(pos_counts.values()) for role, pos_counts in total_global.items()}
            
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
                    p_pos_given_token = (qt_entities + alpha) / (token_role_total + alpha * num_positions)
                    p_media = total_global[role][pos] / role_total if role_total > 0 else 1e-5
                    llr = math.log(p_pos_given_token / p_media)
                    std = max(stats["std"], 0.5)
                    self.stats[token][role][pos] = TokenStats(llr=llr, mean=stats["mean"], std=std)

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
            if not token_stats:
                continue
                
            llr = token_stats.llr
            weight = self.weights.get(token, 0.0)
            mean = token_stats.mean
            std = token_stats.std
            gaussian_penalty = - ((L - mean) ** 2) / (2 * (std ** 2))
            score += (llr * weight) + gaussian_penalty
            
        return score

    def cut(self, query: str) -> list[CutHypothesis]:
        if not query:
            return []
            
        hypotheses = []
        
        # 1. Hard Cut by Comma
        if ',' in query:
            parts = query.split(',', 1)
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
            
        # 2. Anchor by Number
        anchor_idx = -1
        for i, token in enumerate(tokens):
            if any(char.isdigit() for char in token):
                anchor_idx = i
                break
                
        if anchor_idx != -1:
            street_tokens = tokens[:anchor_idx]
            rest_tokens = tokens[anchor_idx+1:]
            score = self._calculate_score(street_tokens)
            hypotheses.append(CutHypothesis(" ".join(street_tokens), " ".join(rest_tokens), score))
            return hypotheses
            
        # 3. Statistical Sliding (no comma, no number)
        for i in range(1, len(tokens) + 1):
            street_tokens = tokens[:i]
            rest_tokens = tokens[i:]
            score = self._calculate_score(street_tokens)
            hypotheses.append(CutHypothesis(" ".join(street_tokens), " ".join(rest_tokens), score))
            
        hypotheses.sort(key=lambda h: h.score, reverse=True)
        return hypotheses

