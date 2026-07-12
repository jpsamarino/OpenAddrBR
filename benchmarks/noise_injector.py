import random

PREFIXES = {"RUA", "AVENIDA", "TRAVESSA", "RODOVIA", "PRACA", "ALAMEDA", "ESTRADA", "VIELA", "BECO", "LADEIRA"}

ABBREVIATIONS = {
    "AVENIDA": ["AV", "AV."],
    "DOUTOR": ["DR", "DR."],
    "PROFESSOR": ["PROF"],
    "PRESIDENTE": ["PRES"],
    "SÃO": ["S", "S."],
    "SANTO": ["STO"],
    "SANTA": ["STA"],
    "NOSSA SENHORA": ["N SRA", "NSA SRA", "N. SRA."],
    "GENERAL": ["GEN"],
    "CORONEL": ["CEL"],
    "CAPITAO": ["CAP"],
    "SARGENTO": ["SGT"],
}

PREPOSITIONS = {"DE", "DA", "DO", "DAS", "DOS"}

# Noise Configuration Probabilities
PROB_CLEAN = 0.65
PROB_DROP_PREFIX = 0.40
PROB_DROP_PREPOSITION = 0.20
PROB_ABBREVIATE = 0.25
PROB_TYPO = 0.10

def generate_typo(word: str) -> str:
    """Introduce a small typo in a word."""
    if len(word) < 4:
        return word
        
    chars = list(word)
    typo_type = random.random()
    
    if typo_type < 0.33:
        # Swap adjacent chars
        idx = random.randint(0, len(chars) - 2)
        chars[idx], chars[idx+1] = chars[idx+1], chars[idx]
    elif typo_type < 0.66:
        # Delete a char
        idx = random.randint(1, len(chars) - 2)
        del chars[idx]
    else:
        # Replace vowel
        vowels = "AEIOU"
        for i, c in enumerate(chars):
            if c in vowels:
                other = random.choice(vowels.replace(c, ""))
                chars[i] = other
                break
                
    return "".join(chars)

def inject_noise(street_clean: str) -> tuple[str, list[str]]:
    """
    Applies noise to a clean street string based on realistic typing habits.
    Returns the mutated string and a list of applied noise tags.
    """
    tags = []
    
    if random.random() < PROB_CLEAN:
        return street_clean, ["clean"]
        
    # We are in the NOISY group
    tokens = street_clean.split()
    if not tokens:
        return street_clean, ["clean"]
        
    # 1. Drop Prefix
    if random.random() < PROB_DROP_PREFIX and tokens[0] in PREFIXES and len(tokens) > 1:
        tokens.pop(0)
        tags.append("drop_prefix")
        
    if not tokens:
        return street_clean, ["clean"]
        
    # 2. Preposition dropping
    if random.random() < PROB_DROP_PREPOSITION:
        orig_len = len(tokens)
        tokens = [t for t in tokens if t not in PREPOSITIONS]
        if len(tokens) < orig_len:
            tags.append("drop_preposition")
        
    if not tokens:
        return street_clean, ["clean"]
        
    # 3. Abbreviations
    if random.random() < PROB_ABBREVIATE:
        abbreviated = False
        for i in range(len(tokens)):
            if tokens[i] in ABBREVIATIONS:
                tokens[i] = random.choice(ABBREVIATIONS[tokens[i]])
                abbreviated = True
        if abbreviated:
            tags.append("abbreviation")
                
    # 4. Typos
    if random.random() < PROB_TYPO:
        # Pick a random long word to typo
        long_words = [i for i, t in enumerate(tokens) if len(t) >= 4]
        if long_words:
            idx = random.choice(long_words)
            tokens[idx] = generate_typo(tokens[idx])
            tags.append("typo")
            
    if not tags:
        tags.append("clean")
        
    return " ".join(tokens), tags
