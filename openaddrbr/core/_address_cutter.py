import json
import math
from typing import Dict, Any
from openaddrbr.core.models._models import TokenStats, CutHypothesis

class AddressCutter:
    def __init__(self, json_path: str, alpha: float = 1.0):
        self.stats: Dict[str, Dict[str, Dict[str, TokenStats]]] = {}
        self.weights: Dict[str, float] = {}
        
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        raw_tokens = data.get("tokens", {})
        
        total_global: Dict[str, Dict[str, int]] = {}
        total_token: Dict[str, int] = {}
        
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
            
        for token, roles in raw_tokens.items():
            self.weights[token] = math.log(total_token[token] + 1)
            self.stats[token] = {}
            for role, positions in roles.items():
                self.stats[token][role] = {}
                num_positions = len(total_global.get(role, {}))
                
                for pos, stats in positions.items():
                    qt_entities = stats["qt_entities"]
                    role_total = sum(total_global[role].values())
                    token_role_total = sum(p["qt_entities"] for p in roles[role].values())
                    p_pos_given_token = (qt_entities + alpha) / (token_role_total + alpha * num_positions)
                    p_media = total_global[role][pos] / role_total if role_total > 0 else 1e-5
                    llr = math.log(p_pos_given_token / p_media)
                    std = max(stats["std"], 0.5)
                    self.stats[token][role][pos] = TokenStats(llr=llr, mean=stats["mean"], std=std)
