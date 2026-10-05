"""
database/db.py — persistência em banco de dados (SQLAlchemy + SQLite).

Modelo relacional:

    regioes (id_regiao PK, nome)
    municipios (id_municipio PK, nome, id_regiao FK -> regioes, latitude, longitude)
    registros (id PK, data, ano, mes, id_municipio FK -> municipios, populacao, chuva_mm, ...)
    chuva_api (id_municipio FK, ano, mes, chuva_real_mm)   <- dados da API Open-Meteo
    vw_registros -> view que junta tudo numa tabela "larga" para análise
"""
from __future__ import annotations

import contextlib
import re
import sqlite3
from pathlib import Path

import pandas as pd

import utils

# SQLAlchemy é o motor principal. Se ele não puder ser carregado (por exemplo, uma política de
# segurança do Windows que bloqueia a extensão compilada), o projeto continua funcionando com o
# módulo `sqlite3` da biblioteca padrão do Python, usando o MESMO arquivo de banco e as mesmas tabelas.
try:
    from sqlalchemy import create_engine, text

    MOTOR = "SQLAlchemy + SQLite"
except Exception:  # ImportError, OSError (DLL bloqueada) etc.
    MOTOR = "sqlite3 (alternativa: SQLAlchemy indisponível neste computador)"

    class _ConexaoSqlite(sqlite3.Connection):
        """Conexão sqlite3 com a mesma interface mínima usada neste módulo (begin/execute)."""

        @contextlib.contextmanager
        def begin(self):
            try:
                yield self
                self.commit()
            except Exception:
                self.rollback()
                raise

        def execute(self, sql, *args):
            return super().execute(str(sql), *args)

    def create_engine(url: str):
        caminho = url.replace("sqlite:///", "", 1)
        return sqlite3.connect(caminho, check_same_thread=False, factory=_ConexaoSqlite)

    def text(sql: str) -> str:
        return sql

CAMINHO_DB = Path(__file__).resolve().parent / "chuvas.db"

DDL_APAGAR = [
    "DROP VIEW IF EXISTS vw_registros",
    "DROP TABLE IF EXISTS chuva_api",
    "DROP TABLE IF EXISTS registros",
    "DROP TABLE IF EXISTS municipios",
    "DROP TABLE IF EXISTS regioes",
]

DDL_CRIAR = [
    """CREATE TABLE IF NOT EXISTS regioes (
           id_regiao INTEGER PRIMARY KEY AUTOINCREMENT,
           nome      TEXT NOT NULL UNIQUE
       )""",
    """CREATE TABLE IF NOT EXISTS municipios (
           id_municipio INTEGER PRIMARY KEY AUTOINCREMENT,
           nome         TEXT NOT NULL UNIQUE,
           id_regiao    INTEGER NOT NULL REFERENCES regioes (id_regiao),
           latitude     REAL,
           longitude    REAL
       )""",
    """CREATE TABLE IF NOT EXISTS registros (
           id                       INTEGER PRIMARY KEY AUTOINCREMENT,
           data                     TEXT    NOT NULL,
           ano                      INTEGER NOT NULL,
           mes                      INTEGER NOT NULL,
           id_municipio             INTEGER NOT NULL REFERENCES municipios (id_municipio),
           populacao                INTEGER,
           chuva_mm                 REAL    NOT NULL,
           temperatura_media        REAL,
           ocorrencias_deslizamento INTEGER NOT NULL,
           desalojados              INTEGER,
           obitos                   INTEGER,
           nivel_risco              TEXT,
           indice_solo              REAL,
           umidade                  REAL
       )""",
    """CREATE TABLE IF NOT EXISTS chuva_api (
           id_municipio  INTEGER NOT NULL REFERENCES municipios (id_municipio),
           ano           INTEGER NOT NULL,
           mes           INTEGER NOT NULL,
           chuva_real_mm REAL,
           PRIMARY KEY (id_municipio, ano, mes)
       )""",
    "CREATE INDEX IF NOT EXISTS idx_registros_data ON registros (data)",
    "CREATE INDEX IF NOT EXISTS idx_registros_mun ON registros (id_municipio)",
    """CREATE VIEW IF NOT EXISTS vw_registros AS
       SELECT r.data, r.ano, r.mes, m.nome AS municipio, g.nome AS regiao_rj, r.populacao,
              r.chuva_mm, r.temperatura_media, r.ocorrencias_deslizamento, r.desalojados,
              r.obitos, r.nivel_risco, r.indice_solo, r.umidade
       FROM registros r
       JOIN municipios m ON m.id_municipio = r.id_municipio
       JOIN regioes g    ON g.id_regiao = m.id_regiao""",
]

# Consultas prontas exibidas no dashboard (aba "Tabelas e SQL")
CONSULTAS_PRONTAS = {
    "Total de deslizamentos por município": """SELECT municipio, regiao_rj,
       SUM(ocorrencias_deslizamento) AS deslizamentos,
       SUM(desalojados) AS desalojados,
       SUM(obitos) AS obitos
FROM vw_registros
GROUP BY municipio, regiao_rj
ORDER BY deslizamentos DESC""",
    "Chuva e deslizamentos por mês do ano": """SELECT mes,
       ROUND(AVG(chuva_mm), 1) AS chuva_media_mm,
       SUM(ocorrencias_deslizamento) AS deslizamentos
FROM vw_registros
GROUP BY mes
ORDER BY mes""",
    "Estação chuvosa (dez–mar) x resto do ano": """SELECT CASE WHEN mes IN (12, 1, 2, 3) THEN 'Chuvosa (dez-mar)' ELSE 'Menos chuvosa (abr-nov)' END AS estacao,
       COUNT(*) AS registros,
       ROUND(AVG(chuva_mm), 1) AS chuva_media_mm,
       SUM(ocorrencias_deslizamento) AS deslizamentos,
       SUM(obitos) AS obitos
FROM vw_registros
GROUP BY estacao""",
    "% de registros em nível Crítico por região": """SELECT regiao_rj,
       COUNT(*) AS registros,
       SUM(CASE WHEN nivel_risco = 'Crítico' THEN 1 ELSE 0 END) AS criticos,
       ROUND(100.0 * SUM(CASE WHEN nivel_risco = 'Crítico' THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_criticos
FROM vw_registros
GROUP BY regiao_rj
ORDER BY pct_criticos DESC""",
    "10 maiores ocorrências de deslizamentos": """SELECT data, municipio, chuva_mm, indice_solo, ocorrencias_deslizamento, desalojados, obitos
FROM vw_registros
ORDER BY ocorrencias_deslizamento DESC, chuva_mm DESC
LIMIT 10""",
}

_PALAVRAS_PROIBIDAS = re.compile(
    r"\b(insert|update|delete|drop|alter|create|replace|attach|detach|pragma|vacuum|reindex)\b",
    flags=re.IGNORECASE,
)


def get_engine(caminho: Path | str = CAMINHO_DB):
    """Cria o engine do SQLAlchemy apontando para o arquivo SQLite."""
    return create_engine(f"sqlite:///{caminho}")


def criar_banco(df: pd.DataFrame, engine=None) -> None:
    """(Re)cria o esquema relacional e carrega os dados a partir do DataFrame limpo."""
    engine = engine or get_engine()
    with engine.begin() as conn:
        for comando in DDL_APAGAR + DDL_CRIAR:
            conn.execute(text(comando))

    regioes = pd.DataFrame({"nome": sorted(df["regiao_rj"].unique())})
    regioes.to_sql("regioes", engine, if_exists="append", index=False)
    mapa_reg = pd.read_sql_query(text("SELECT id_regiao, nome FROM regioes"), engine)
    mapa_reg = dict(zip(mapa_reg["nome"], mapa_reg["id_regiao"]))

    mun = df[["municipio", "regiao_rj"]].drop_duplicates().copy()
    mun["id_regiao"] = mun["regiao_rj"].map(mapa_reg)
    mun["latitude"] = mun["municipio"].map(lambda m: utils.COORDENADAS.get(m, (None, None))[0])
    mun["longitude"] = mun["municipio"].map(lambda m: utils.COORDENADAS.get(m, (None, None))[1])
    mun = mun.rename(columns={"municipio": "nome"})[["nome", "id_regiao", "latitude", "longitude"]]
    mun.to_sql("municipios", engine, if_exists="append", index=False)
    mapa_mun = pd.read_sql_query(text("SELECT id_municipio, nome FROM municipios"), engine)
    mapa_mun = dict(zip(mapa_mun["nome"], mapa_mun["id_municipio"]))

    fato = pd.DataFrame({
        "data": df["data"].dt.strftime("%Y-%m-%d"), "ano": df["ano"], "mes": df["mes"],
        "id_municipio": df["municipio"].map(mapa_mun), "populacao": df["populacao"],
        "chuva_mm": df["chuva_mm"], "temperatura_media": df["temperatura_media"],
        "ocorrencias_deslizamento": df["ocorrencias_deslizamento"], "desalojados": df["desalojados"],
        "obitos": df["obitos"], "nivel_risco": df["nivel_risco"].astype(str),
        "indice_solo": df["indice_solo"], "umidade": df["umidade"],
    })
    fato.to_sql("registros", engine, if_exists="append", index=False)


def banco_pronto(engine=None) -> bool:
    """True se o banco já existe e a tabela de registros tem dados."""
    engine = engine or get_engine()
    try:
        n = pd.read_sql_query(text("SELECT COUNT(*) AS n FROM registros"), engine)["n"].iloc[0]
        return int(n) > 0
    except Exception:
        return False


def carregar_do_banco(engine=None) -> pd.DataFrame:
    """Lê a view vw_registros (junção das tabelas) como DataFrame."""
    engine = engine or get_engine()
    return pd.read_sql_query(text("SELECT * FROM vw_registros"), engine)


def salvar_chuva_api(real: pd.DataFrame, engine=None) -> int:
    """Grava no banco a chuva observada (API) — substitui os registros anteriores. Retorna nº de linhas."""
    engine = engine or get_engine()
    mapa = pd.read_sql_query(text("SELECT id_municipio, nome FROM municipios"), engine)
    mapa = dict(zip(mapa["nome"], mapa["id_municipio"]))
    d = real.copy()
    d["id_municipio"] = d["municipio"].map(mapa)
    d = d.dropna(subset=["id_municipio"])
    d["id_municipio"] = d["id_municipio"].astype(int)
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM chuva_api"))
    d[["id_municipio", "ano", "mes", "chuva_real_mm"]].to_sql("chuva_api", engine, if_exists="append", index=False)
    return len(d)


def carregar_chuva_api(engine=None) -> pd.DataFrame:
    """Lê do banco a chuva observada guardada anteriormente (pode estar vazia)."""
    engine = engine or get_engine()
    return pd.read_sql_query(text(
        """SELECT m.nome AS municipio, a.ano, a.mes, a.chuva_real_mm
           FROM chuva_api a JOIN municipios m ON m.id_municipio = a.id_municipio"""), engine)


def consulta_segura(sql: str) -> tuple[bool, str]:
    """Aceita apenas UMA instrução de leitura (SELECT/WITH). Retorna (ok, mensagem)."""
    limpo = sql.strip().rstrip(";").strip()
    if not limpo:
        return False, "Digite uma consulta SQL."
    if ";" in limpo:
        return False, "Use apenas uma instrução por vez."
    if not limpo.lower().startswith(("select", "with")):
        return False, "Somente consultas de leitura (SELECT) são permitidas."
    if _PALAVRAS_PROIBIDAS.search(limpo):
        return False, "A consulta contém comandos não permitidos (somente leitura)."
    return True, limpo


def executar_consulta(sql: str, engine=None, limite: int = 1000) -> pd.DataFrame:
    """Executa uma consulta de leitura e devolve no máximo `limite` linhas."""
    ok, resultado = consulta_segura(sql)
    if not ok:
        raise ValueError(resultado)
    engine = engine or get_engine()
    return pd.read_sql_query(text(resultado), engine).head(limite)


def descrever_esquema(engine=None) -> pd.DataFrame:
    """Lista tabelas/views do banco e a quantidade de linhas de cada uma."""
    engine = engine or get_engine()
    objetos = pd.read_sql_query(
        text("SELECT name, type FROM sqlite_master WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%' ORDER BY type, name"),
        engine,
    )
    contagens = [int(pd.read_sql_query(text(f"SELECT COUNT(*) AS n FROM {n}"), engine)["n"].iloc[0]) for n in objetos["name"]]
    objetos["linhas"] = contagens
    return objetos.rename(columns={"name": "objeto", "type": "tipo"})
