"""
Stemmer de Porter (Porter, 1980) para ingles, implementado sem dependencias.
Referencia: Porter, M. F. (1980). An algorithm for suffix stripping.
Program, 14(3), 130-137.
"""
_VOGAIS = set("aeiou")


def _consoante(p, i):
    if p[i] in _VOGAIS:
        return False
    if p[i] == "y":
        return i == 0 or not _consoante(p, i - 1)
    return True


def _medida(radical):
    """m em [C](VC)^m[V]: quantas sequencias vogal-consoante o radical tem."""
    m, i, n = 0, 0, len(radical)
    while i < n and _consoante(radical, i):
        i += 1
    while i < n:
        while i < n and not _consoante(radical, i):
            i += 1
        if i >= n:
            break
        while i < n and _consoante(radical, i):
            i += 1
        m += 1
    return m


def _tem_vogal(radical):
    return any(not _consoante(radical, i) for i in range(len(radical)))


def _dupla_consoante(p):
    return len(p) >= 2 and p[-1] == p[-2] and _consoante(p, len(p) - 1)


def _cvc(p):
    """termina em consoante-vogal-consoante, e a ultima nao e w, x ou y"""
    return (len(p) >= 3 and _consoante(p, len(p) - 3) and not _consoante(p, len(p) - 2)
            and _consoante(p, len(p) - 1) and p[-1] not in "wxy")


def _trocar(p, regras, m_min):
    for suf, novo in regras:
        if p.endswith(suf):
            radical = p[: len(p) - len(suf)]
            return radical + novo if _medida(radical) > m_min else p
    return p


def _passo1(p):
    # 1a
    if p.endswith("sses"):
        p = p[:-2]
    elif p.endswith("ies"):
        p = p[:-2]
    elif p.endswith("ss"):
        pass
    elif p.endswith("s"):
        p = p[:-1]
    # 1b
    extra = False
    if p.endswith("eed"):
        if _medida(p[:-3]) > 0:
            p = p[:-1]
    elif p.endswith("ed") and _tem_vogal(p[:-2]):
        p, extra = p[:-2], True
    elif p.endswith("ing") and _tem_vogal(p[:-3]):
        p, extra = p[:-3], True
    if extra:
        if p.endswith(("at", "bl", "iz")):
            p += "e"
        elif _dupla_consoante(p) and p[-1] not in "lsz":
            p = p[:-1]
        elif _medida(p) == 1 and _cvc(p):
            p += "e"
    # 1c
    if p.endswith("y") and _tem_vogal(p[:-1]):
        p = p[:-1] + "i"
    return p


_PASSO2 = [
    ("ational", "ate"), ("tional", "tion"), ("enci", "ence"), ("anci", "ance"),
    ("izer", "ize"), ("abli", "able"), ("alli", "al"), ("entli", "ent"), ("eli", "e"),
    ("ousli", "ous"), ("ization", "ize"), ("ation", "ate"), ("ator", "ate"),
    ("alism", "al"), ("iveness", "ive"), ("fulness", "ful"), ("ousness", "ous"),
    ("aliti", "al"), ("iviti", "ive"), ("biliti", "ble"),
]
_PASSO3 = [
    ("icate", "ic"), ("ative", ""), ("alize", "al"), ("iciti", "ic"),
    ("ical", "ic"), ("ful", ""), ("ness", ""),
]
_PASSO4 = [
    "al", "ance", "ence", "er", "ic", "able", "ible", "ant", "ement", "ment",
    "ent", "ion", "ou", "ism", "ate", "iti", "ous", "ive", "ize",
]


def _passo2(p):
    # ordena por tamanho para casar o sufixo mais longo
    return _trocar(p, sorted(_PASSO2, key=lambda r: -len(r[0])), 0)


def _passo3(p):
    return _trocar(p, sorted(_PASSO3, key=lambda r: -len(r[0])), 0)


def _passo4(p):
    for suf in sorted(_PASSO4, key=len, reverse=True):
        if p.endswith(suf):
            radical = p[: len(p) - len(suf)]
            if _medida(radical) > 1:
                if suf == "ion" and not radical.endswith(("s", "t")):
                    return p
                return radical
            return p
    return p


def _passo5(p):
    if p.endswith("e"):
        radical = p[:-1]
        m = _medida(radical)
        if m > 1 or (m == 1 and not _cvc(radical)):
            p = radical
    if _medida(p) > 1 and _dupla_consoante(p) and p.endswith("l"):
        p = p[:-1]
    return p


_cache = {}


def stem(palavra):
    """Radical de uma palavra em minusculas (palavras de ate 2 letras ficam iguais)."""
    if palavra in _cache:
        return _cache[palavra]
    p = palavra
    if len(p) > 2 and p.isalpha():
        p = _passo5(_passo4(_passo3(_passo2(_passo1(p)))))
    _cache[palavra] = p
    return p
