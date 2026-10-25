"""
Traducao da CONSULTA do usuario (portugues -> ingles) para o motor de busca.

  1) glossario de termos de TI (expressoes de varias palavras primeiro)
  2) palavras que ja existem no indice ficam como estao (python, docker, sql, linux...)
Assim nomes de tecnologias nunca sao "estragados" pelo tradutor, e o modelo
so e usado quando realmente necessario.
"""
import re
import unicodedata

from stemmer import stem

# Chaves SEM acento e em minusculas. Valores podem ter varias formas em ingles

GLOSSARIO = {
    # dados e bancos
    "banco de dados": "database databases",
    "bancos de dados": "database databases",
    "banco de dados relacional": "relational database",
    "dados": "data",
    "ciencia de dados": "data science scientists",
    "cientista de dados": "data science scientists",
    "analise de dados": "data analysis analytics",
    "visualizacao de dados": "data visualization",
    "mineracao de dados": "data mining",
    "armazem de dados": "data warehouse warehousing",
    "modelagem": "modeling model",
    "estatistica": "statistics statistical",
    "relatorio": "reports reporting",
    "relatorios": "reports reporting",
    "painel": "dashboard dashboards",
    "paineis": "dashboard dashboards",
    "planilha": "spreadsheet excel",
    "planilhas": "spreadsheet excel",
    "inteligencia artificial": "artificial intelligence machine learning",
    "aprendizado de maquina": "machine learning",
    "aprendizagem de maquina": "machine learning",
    "inteligencia de negocios": "business intelligence",
    # desenvolvimento
    "programacao": "programming code coding",
    "programar": "programming code coding",
    "programador": "programmers programming",
    "codigo": "code coding",
    "desenvolvimento": "development develop",
    "desenvolver": "develop development",
    "desenvolvedor": "developers development",
    "desenvolvimento web": "web development developers",
    "linguagem de programacao": "programming language",
    "aplicativo": "application applications app mobile",
    "aplicativos": "application applications app mobile",
    "celular": "mobile",
    "site": "website websites web",
    "sites": "website websites web",
    "depuracao": "debug debugging",
    "testes": "test testing tests",
    "teste": "test testing tests",
    "documentacao": "documentation",
    "requisitos": "requirements",
    "metodologias ageis": "agile",
    "agil": "agile",
    "jogos": "game games gaming video",
    "jogo": "game games gaming video",
    "jogos eletronicos": "video game games",
    "graficos": "graphics",
    "interface": "interface",
    "interface de usuario": "user interface",
    "experiencia do usuario": "user experience usability",
    "usabilidade": "usability",
    "acessibilidade": "accessibility",
    "prototipo": "prototypes",
    "prototipos": "prototypes",
    # redes e infraestrutura
    "rede": "network networks networking",
    "redes": "network networks networking",
    "redes de computadores": "computer network networks networking",
    "sem fio": "wireless",
    "roteador": "router",
    "roteadores": "router",
    "servidor": "server servers",
    "servidores": "server servers",
    "nuvem": "cloud",
    "computacao em nuvem": "cloud computing",
    "infraestrutura": "infrastructure",
    "armazenamento": "storage",
    "sistema operacional": "operating system",
    "sistemas operacionais": "operating system systems",
    "sistema": "system systems",
    "sistemas": "system systems",
    "automacao": "automation",
    "suporte": "support",
    "suporte tecnico": "technical support help desk",
    "atendimento": "customer support help",
    "solucao de problemas": "troubleshooting",
    "manutencao": "maintenance",
    "computador": "computer",
    "computadores": "computer",
    # seguranca
    "seguranca": "security",
    "seguranca da informacao": "information security cybersecurity",
    "ciberseguranca": "cybersecurity security",
    "seguranca cibernetica": "cybersecurity security",
    "teste de invasao": "penetration testing",
    "testes de invasao": "penetration testing",
    "invasao": "penetration hacking",
    "hacker": "hacking penetration",
    "vulnerabilidade": "vulnerability vulnerabilities",
    "vulnerabilidades": "vulnerability vulnerabilities",
    "criptografia": "encryption",
    "privacidade": "privacy",
    "forense": "forensic forensics",
    "forense digital": "digital forensics forensic",
    "incidente": "incident",
    "incidentes": "incident",
    "auditoria": "audit",
    "risco": "risk",
    "riscos": "risk",
    "conformidade": "compliance",
    "governanca": "governance",
    # gestao
    "gestao de projetos": "project management",
    "gerenciamento de projetos": "project management",
    "gerente de projetos": "project management managers",
    "gestao": "management",
    "gerente": "manager managers management",
    "gerentes": "manager managers management",
    "tecnologia da informacao": "information technology",
    "ti": "information technology computer",
    "administracao": "administration administer administrators",
    "administracao de sistemas": "systems administrators administration",
    "administrador": "administrators administration administer",
    "investigacao": "investigation investigations investigate evidence",
    "gerenciamento": "management",
    "lideranca": "management team",
    "equipe": "team",
    "orcamento": "budget",
    "planejamento": "planning plan",
    "negocios": "business",
    # hardware e robotica
    "eletronica": "electronic",
    "circuito": "circuit",
    "circuitos": "circuit",
    "sensor": "sensor",
    "sensores": "sensor",
    "embarcado": "embedded",
    "sistemas embarcados": "embedded systems",
    "robotica": "robotics robot robots",
    "robo": "robot robots robotics",
    "robos": "robot robots robotics",
    "fabricacao": "manufacturing",
    "mecanica": "mechanical",
    "contratos inteligentes": "smart contract",
    "criptomoeda": "cryptocurrency",
    "criptomoedas": "cryptocurrency",
}

STOPWORDS_PT = {
    "a", "o", "as", "os", "um", "uma", "uns", "umas", "de", "da", "do", "das", "dos",
    "e", "ou", "em", "na", "no", "nas", "nos", "com", "sem", "para", "pra", "por",
    "pelo", "pela", "que", "eu", "sei", "tenho", "gosto", "conheco", "trabalho",
    "experiencia", "habilidade", "habilidades", "conhecimento", "conhecimentos",
    "basico", "avancado", "intermediario", "muito", "bem", "mais", "area",
    "quero", "queria", "gostaria", "trabalhar", "atuar", "aprender", "usar", "uso", "saber",
    "fazer", "ser", "sou", "estou", "minha", "meu", "minhas", "meus",
}

STOPWORDS_EN = {
    "the", "a", "an", "and", "or", "of", "to", "in", "for", "with", "on", "using",
}

_MAX_EXPRESSAO = max(len(k.split()) for k in GLOSSARIO)


def normalizar(texto):
    """Minusculas e sem acentos (seguranca == segurança)."""
    texto = unicodedata.normalize("NFKD", (texto or "").lower())
    return "".join(c for c in texto if not unicodedata.combining(c))


def _tokens(texto):
    # mantem c++, c#, node.js, .net
    return re.findall(r"[a-z0-9\+\#\.\-]*[a-z0-9\+\#]", normalizar(texto))


def _parece_tecnico(palavra):
    return bool(re.search(r"[0-9\+\#\.]", palavra))


def traduzir_consulta(consulta, vocabulario, tradutor=None):
    """
    consulta:    texto digitado pelo usuario (portugues, ingles ou misturado)
    vocabulario: conjunto de termos do indice (dados["indice"].keys())
    tradutor:    funcao opcional texto -> texto (pt -> en) para as palavras que sobrarem

    Devolve (consulta_em_ingles, palavras_nao_reconhecidas).
    """
    tokens = _tokens(consulta)
    saida, desconhecidas = [], []
    i = 0
    while i < len(tokens):
        # 1) glossario: tenta a expressao mais longa primeiro
        for n in range(min(_MAX_EXPRESSAO, len(tokens) - i), 0, -1):
            expressao = " ".join(tokens[i:i + n])
            if expressao in GLOSSARIO:
                saida.append(GLOSSARIO[expressao])
                i += n
                break
        else:
            palavra = tokens[i]
            i += 1
            if palavra in STOPWORDS_PT or palavra in STOPWORDS_EN:
                continue                       # 3) palavra comum, descarta
            elif palavra in vocabulario or stem(palavra) in vocabulario or _parece_tecnico(palavra):
                saida.append(palavra)          # 2) ja e um termo do indice
            else:
                desconhecidas.append(palavra)  # 4) fica para o tradutor

    if desconhecidas and tradutor is not None:
        try:
            saida.append(tradutor(" ".join(desconhecidas)))
            desconhecidas = []
        except Exception:
            pass

    return " ".join(saida), desconhecidas
