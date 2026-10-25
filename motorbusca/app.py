"""
Interface web (Streamlit) do motor de busca de profissoes de TI.

Traducao:
  - resultados (titulos e descricoes): lidos prontos de traducoes.json
    (gerado uma vez pelo pre_traduzir.py) -> nada e traduzido na hora
  - consulta do usuario: glossario de TI (traducao_consulta.py); o modelo
    MarianMT so e carregado se sobrar alguma palavra fora do glossario
"""
import json
import re
from pathlib import Path

import streamlit as st

from db_config import ConfigBancoAusente, conectar
from motor_busca import ARQUIVO_DADOS, K1, B, TOP, buscar, flag, obter_dados
from titulos_pt import TITULOS_PT
from traducao_consulta import traduzir_consulta

PASTA = Path(__file__).parent
ICONE = PASTA / "icone.png"   # se existir, vira o icone da aba
ARQUIVO_TRADUCOES = PASTA / "traducoes.json"

st.set_page_config(
    page_title="Busca de Profissoes de TI",
    page_icon=str(ICONE) if ICONE.exists() else None,
    layout="centered",
)



MODELO_PT_EN = "Helsinki-NLP/opus-mt-ROMANCE-en"   # usado so como plano B na consulta


@st.cache_data(show_spinner=False)
def carregar_traducoes():
    """Traducoes prontas dos resultados. Sem o arquivo, devolve {} (mostra em ingles)."""
    if not ARQUIVO_TRADUCOES.exists():
        return {}
    return json.loads(ARQUIVO_TRADUCOES.read_text(encoding="utf-8"))


@st.cache_resource(show_spinner="Carregando tradutor automático (só na 1ª vez)...")
def carregar_modelo_pt_en():
    # importa aqui dentro: o app abre rapido e funciona mesmo sem torch instalado
    from transformers import MarianMTModel, MarianTokenizer
    return MarianTokenizer.from_pretrained(MODELO_PT_EN), MarianMTModel.from_pretrained(MODELO_PT_EN)


@st.cache_data(show_spinner="Traduzindo termos...")
def tradutor_automatico(texto):
    import torch
    tok, modelo = carregar_modelo_pt_en()
    lote = tok([texto], return_tensors="pt", padding=True, truncation=True, max_length=128)
    with torch.no_grad():
        saida = modelo.generate(**lote, max_new_tokens=64, num_beams=4)
    return tok.batch_decode(saida, skip_special_tokens=True)[0].lower()


def titulo_pt(code, titulo_en, traducoes):
    return traducoes.get(code, {}).get("titulo_pt") or TITULOS_PT.get(code) or titulo_en



@st.cache_resource(show_spinner="Carregando indice...")
def carregar_indice():
    return obter_dados()


@st.cache_data(show_spinner=False)
def carregar_profissoes():
    """Dados exportados (dados_profissoes.json)"""
    if not Path(ARQUIVO_DADOS).exists():
        return None
    return json.loads(Path(ARQUIVO_DADOS).read_text(encoding="utf-8"))


def _sem_duplicatas(skills):
    """Remove skills repetidas (ignora maiusculas/minusculas), juntando as marcacoes."""
    vistas = {}
    for s, h, d in skills:
        if not s:
            continue
        chave = s.strip().lower()
        if chave in vistas:
            nome, hot0, dem0 = vistas[chave]
            vistas[chave] = (nome, hot0 or h, dem0 or d)
        else:
            vistas[chave] = (s.strip(), h, d)
    return list(vistas.values())


@st.cache_data(show_spinner=False)
def detalhes(code):
    """Descricao e skills de uma profissao"""
    profissoes = carregar_profissoes()
    if profissoes is not None:
        p = profissoes.get(code, {})
        return p.get("descricao", ""), _sem_duplicatas(p.get("skills", []))

    conn = conectar()
    cur = conn.cursor()
    cur.execute("SELECT description FROM occupation_data WHERE onetsoc_code = %s", (code,))
    row = cur.fetchone()
    descricao = row[0] if row else ""
    cur.execute(
        "SELECT workplace_example, hot_technology, in_demand "
        "FROM software_skills WHERE onetsoc_code = %s",
        (code,),
    )
    skills = [(s, flag(h), flag(d)) for s, h, d in cur.fetchall()]
    cur.close()
    conn.close()
    return descricao, _sem_duplicatas(skills)


def _tokens(texto):
    """Palavras minusculas de um texto (mantem C++, C#, .NET, Node.js)."""
    achados = re.findall(r"[a-z0-9\+\#\.]+", (texto or "").lower())
    return {t.strip(".") for t in achados if t.strip(".")}


def selecionar_skills(skills, termos_busca, limite=7):
    """Escolhe as skills mais relevantes, sem repeticoes parecidas.
    Ordem de relevancia: bate com a busca > hot technology > em demanda > ordem alfabetica.
    Pula skills cujo nome e igual/subconjunto de uma ja escolhida
    (ex.: 'Java' depois de 'Oracle Java'; ignora a palavra 'software')."""
    def bate(nome):
        return bool(_tokens(nome) & termos_busca)

    ordenadas = sorted(skills, key=lambda x: (not bate(x[0]), not x[1], not x[2], x[0].lower()))
    escolhidas, usados = [], []
    for nome, hot, demand in ordenadas:
        tokens = _tokens(nome) - {"software"}
        if not tokens or any(tokens <= u or u <= tokens for u in usados):
            continue
        escolhidas.append((nome, bate(nome)))
        usados.append(tokens)
        if len(escolhidas) == limite:
            break
    return escolhidas


st.title("Busca de Profissões de TI")
st.caption("Digite suas habilidades e veja as profissões mais compatíveis.")

dados = carregar_indice()
vocabulario = set(dados["indice"])
traducoes = carregar_traducoes()

# configuracoes fixas (antes ficavam na barra lateral)
mostrar_pt = True          # resultados em portugues
usar_modelo = True         # tradutor automatico para termos fora do glossario (se instalado)
top, k1, b = TOP, K1, B    # quantidade de resultados e parametros do BM25 (motor_busca.py)

consulta = st.text_input("Suas habilidades", placeholder="ex.: python, banco de dados, docker")

if consulta.strip():
    
    # se o modelo falhar (sem torch, sem internet na 1a vez), a busca segue sem ele
    tradutor = tradutor_automatico if usar_modelo else None
    consulta_en, nao_reconhecidas = traduzir_consulta(consulta, vocabulario, tradutor)

    if consulta_en:
        st.caption(f"Buscando por: **{consulta_en}**")
    if nao_reconhecidas:
        st.caption("Termos não reconhecidos: " + ", ".join(nao_reconhecidas))

    resultados = buscar(consulta_en, dados, top=top, k1=k1, b=b) if consulta_en else []

    if not resultados:
        st.warning("Nenhum resultado. Tente outros termos.")
    else:
        maior = resultados[0][2] or 1
        st.subheader(f"{len(resultados)} profissões encontradas")
        for i, (code, titulo_en, score) in enumerate(resultados, 1):
            titulo = titulo_pt(code, titulo_en, traducoes) if mostrar_pt else titulo_en
            with st.expander(f"{i}. {titulo}"):
                st.progress(min(score / maior, 1.0), text=f"Relevância relativa: {score / maior:.0%}")
                if mostrar_pt and titulo != titulo_en:
                    st.caption(f"Título original: {titulo_en}")

                try:
                    descricao, skills = detalhes(code)
                except ConfigBancoAusente as e:
                    st.error(str(e))
                    st.stop()
                except Exception:
                    # mensagem generica: nao mostra detalhes da conexao na tela
                    st.error("Não foi possível conectar ao banco de dados.")
                    st.stop()

                descricao_pt = traducoes.get(code, {}).get("descricao_pt")
                texto = descricao_pt if (mostrar_pt and descricao_pt) else descricao
                if texto:
                    st.write(texto)

                if skills:
                    # nomes de tecnologias NAO sao traduzidos (Python, Docker, SQL...)
                    selecionadas = selecionar_skills(skills, _tokens(consulta_en), limite=7)
                    linhas = [f"- **{nome}**" if bate else f"- {nome}" for nome, bate in selecionadas]
                    st.markdown("**Principais tecnologias:**\n\n" + "\n".join(linhas))
else:
    st.info("Digite algumas habilidades acima para começar.")

st.caption("Dados: O*NET 30 Database, U.S. Department of Labor/Employment and Training "
           "Administration (USDOL/ETA), licença CC BY 4.0.")