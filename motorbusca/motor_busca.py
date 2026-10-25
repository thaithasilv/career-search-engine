"""
Dependencia: pip install mysql-connector-python python-dotenv
"""
import json
import math
import os
import pickle
import re
from collections import Counter, defaultdict

from db_config import conectar  # conexao com o banco (credenciais no .env)
from stemmer import stem

ARQUIVO_DADOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dados_profissoes.json")
CACHE_FILE = "indice_v3.pkl"   # apague este arquivo para reconstruir o indice
USAR_STEMMING = False          # reduz palavras ao radical (databases -> databas)
TOP = 10

# Pesos por tipo de texto (skills pesam mais porque o usuario digita habilidades)
PESO = {"titulo": 3, "skills": 5, "descricao": 1, "tarefas": 1}

# Parametros do BM25
K1 = 1.5   # saturacao do TF (tipico: 1.2 a 2.0)
B = 0.75   # normalizacao pelo tamanho do documento (0 = ignora, 1 = total)

STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "for", "with", "on",
    "is", "are", "as", "by", "that", "this", "be", "from", "at", "it", "using",
}



def _tecnico(token):
    """Nomes de tecnologia (c++, c#, node.js, back-end, 3d) nao passam pelo stemmer."""
    return not token.isalpha()


def tokenizar(texto, stemming=USAR_STEMMING):
    """Minusculas + tokens que preservam C++, C#, Node.js etc.
    Com stemming, cada palavra vira seu radical (Porter)."""
    padrao = r"[a-z0-9][a-z0-9\+\#\.\-]*[a-z0-9\+\#]|[a-z0-9]"
    tokens = [t for t in re.findall(padrao, (texto or "").lower()) if t not in STOPWORDS]
    if stemming:
        tokens = [t if _tecnico(t) else stem(t) for t in tokens]
    return tokens


def flag(valor):
    """Interpreta Y/N, 1/0, True/False vindos do MySQL."""
    return str(valor).strip().upper() in {"Y", "YES", "1", "TRUE", "T"}



def carregar_docs():
    """Le as profissoes de dados_profissoes.json (versao publicada) ou, se ele
    nao existir, direto do MySQL (versao local)."""
    if os.path.exists(ARQUIVO_DADOS):
        with open(ARQUIVO_DADOS, encoding="utf-8") as f:
            return json.load(f)
    return carregar_docs_mysql()


def carregar_docs_mysql():
    conn = conectar()
    cur = conn.cursor()
    docs = {}

    cur.execute("SELECT onetsoc_code, title, description FROM occupation_data")
    for code, title, desc in cur.fetchall():
        docs[code] = {"titulo": title or "", "descricao": desc or "",
                      "skills": [], "tarefas": []}

    cur.execute(
        "SELECT onetsoc_code, workplace_example, hot_technology, in_demand "
        "FROM software_skills"
    )
    for code, skill, hot, demand in cur.fetchall():
        if code in docs and skill:
            docs[code]["skills"].append((skill, flag(hot), flag(demand)))

    cur.execute("SELECT onetsoc_code, task FROM task_statements")
    for code, task in cur.fetchall():
        if code in docs and task:
            docs[code]["tarefas"].append(task)

    cur.close()
    conn.close()
    return docs



def construir_indice(docs):
    indice = defaultdict(dict)   # termo -> {codigo: tf ponderado}
    tam_doc = {}                 # codigo -> tamanho ponderado do documento
    for code, d in docs.items():
        tf = Counter()
        for t in tokenizar(d["titulo"]):
            tf[t] += PESO["titulo"]
        for t in tokenizar(d["descricao"]):
            tf[t] += PESO["descricao"]
        for tarefa in d["tarefas"]:
            for t in tokenizar(tarefa):
                tf[t] += PESO["tarefas"]
        for skill, hot, demand in d["skills"]:
            bonus = 1 + (0.5 if hot else 0) + (0.25 if demand else 0)
            for t in tokenizar(skill):
                tf[t] += PESO["skills"] * bonus
        for termo, valor in tf.items():
            indice[termo][code] = valor
        tam_doc[code] = sum(tf.values())
    return dict(indice), tam_doc


def obter_dados():
    """Usa cache em disco; se nao existir, le do MySQL e constroi o indice."""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "rb") as f:
            dados = pickle.load(f)
        # se a configuracao mudou (pesos ou stemming), reconstroi automaticamente
        if dados.get("stemming") == USAR_STEMMING and dados.get("pesos") == PESO:
            return dados
        print("Configuracao mudou desde o ultimo indice.")
    print("Construindo indice...")
    docs = carregar_docs()
    indice, tam_doc = construir_indice(docs)
    dados = {
        "indice": indice,
        "tam_doc": tam_doc,
        "tam_medio": sum(tam_doc.values()) / len(tam_doc),
        "titulos": {code: d["titulo"] for code, d in docs.items()},
        "N": len(docs),
        "stemming": USAR_STEMMING,
        "pesos": dict(PESO),
    }
    with open(CACHE_FILE, "wb") as f:
        pickle.dump(dados, f)
    print(f"Indice pronto: {len(docs)} profissoes, {len(indice)} termos.")
    return dados



def buscar(consulta, dados, top=TOP, k1=K1, b=B):
    indice, titulos, N = dados["indice"], dados["titulos"], dados["N"]
    tam_doc, tam_medio = dados["tam_doc"], dados["tam_medio"]
    scores = defaultdict(float)
    # a consulta e processada do mesmo jeito que o indice foi construido
    for termo in set(tokenizar(consulta, stemming=dados.get("stemming", False))):
        postings = indice.get(termo)
        if not postings:
            continue
        df = len(postings)
        idf = math.log((N - df + 0.5) / (df + 0.5) + 1)
        for code, tf in postings.items():
            norm = k1 * (1 - b + b * tam_doc[code] / tam_medio)
            scores[code] += idf * (tf * (k1 + 1)) / (tf + norm)
    ranking = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top]
    return [(code, titulos[code], round(s, 3)) for code, s in ranking]


def main():
    dados = obter_dados()
    print("\nMotor de busca de profissoes de TI (BM25).")
    print("Digite suas habilidades (ex.: python sql docker). 'sair' para encerrar.")
    while True:
        q = input("\n> ").strip()
        if q.lower() in {"sair", "exit", "quit"}:
            break
        if not q:
            continue
        resultados = buscar(q, dados)
        if not resultados:
            print("Nenhum resultado.")
            continue
        for i, (code, titulo, score) in enumerate(resultados, 1):
            print(f"{i:>2}. {score:>8}  {code}  {titulo}")


if __name__ == "__main__":
    main()