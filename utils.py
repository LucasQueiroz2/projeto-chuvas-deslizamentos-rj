
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


RAIZ = Path(__file__).resolve().parent
CAMINHO_CSV = RAIZ / "dados" / "simulacao_chuvas_deslizamentos_rj.csv"

COLUNAS_OBRIGATORIAS = [
    "ano", "mes", "data", "municipio", "regiao_rj", "populacao", "chuva_mm",
    "temperatura_media", "ocorrencias_deslizamento", "desalojados", "obitos",
    "nivel_risco", "indice_solo", "umidade",
]
ORDEM_RISCO = ["Baixo", "Médio", "Alto", "Crítico"]
MESES_CHUVOSOS = [12, 1, 2, 3]
ROTULO_CHUVOSA = "Chuvosa (dez–mar)"
ROTULO_MENOS = "Menos chuvosa (abr–nov)"
LIMIAR_CHUVA_INTENSA = 200.0   # mm no mês
LIMIAR_SOLO_SATURADO = 0.8     # índice de saturação do solo
NOMES_MESES = {1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
               7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"}


COORDENADAS = {
    "Rio de Janeiro": (-22.9068, -43.1729),
    "Niterói": (-22.8832, -43.1034),
    "Nova Iguaçu": (-22.7592, -43.4510),
    "Petrópolis": (-22.5050, -43.1789),
    "Teresópolis": (-22.4120, -42.9660),
    "Nova Friburgo": (-22.2819, -42.5311),
    "Angra dos Reis": (-23.0067, -44.3181),
    "Campos dos Goytacazes": (-21.7545, -41.3244),
}

METRICAS = {  # rótulo amigável -> (coluna, agregação, formato)
    "Total de deslizamentos": ("ocorrencias_deslizamento", "sum", "{:,.0f}"),
    "Chuva média mensal (mm)": ("chuva_mm", "mean", "{:,.1f}"),
    "Total de desalojados": ("desalojados", "sum", "{:,.0f}"),
    "Total de óbitos": ("obitos", "sum", "{:,.0f}"),
    "% de registros em nível Crítico": ("critico_pct", "mean", "{:,.1f}"),
    "Índice médio de saturação do solo": ("indice_solo", "mean", "{:,.2f}"),
}

COR_DESTAQUE = "#d95f02"
COR_NEUTRA = "#9db4c8"
COR_PRINCIPAL = "#1f77b4"
COR_CHUVA = "#2a7ab0"
COR_DESLIZ = "#b5532a"
PALETA_REGIAO = {
    "Serrana": "#d95f02", "Metropolitana": "#1f77b4", "Baixada": "#7570b3",
    "Costa Verde": "#1b9e77", "Norte Fluminense": "#e6ab02",
}

sns.set_theme(style="whitegrid", context="notebook")
plt.rcParams.update({
    "figure.dpi": 110,
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
    "axes.labelsize": 10,
})


def br(valor, casas: int = 2, sinal: bool = False) -> str:
    """Formata número no padrão brasileiro (1.234,56). `sinal=True` mostra +/−."""
    if valor is None or (isinstance(valor, float) and np.isnan(valor)):
        return "–"
    txt = f"{valor:+,.{casas}f}" if sinal else f"{valor:,.{casas}f}"
    return txt.replace(",", "§").replace(".", ",").replace("§", ".")


def _loc(texto: str) -> str:
    """Troca separadores no padrão americano (1,234.5) para o brasileiro (1.234,5)."""
    return texto.replace(",", "§").replace(".", ",").replace("§", ".")


def carregar_csv(fonte=CAMINHO_CSV) -> pd.DataFrame:
    """Lê o CSV bruto (caminho ou arquivo em memória)."""
    return pd.read_csv(fonte, encoding="utf-8-sig")


def validar_colunas(df: pd.DataFrame) -> list[str]:
    """Retorna a lista de colunas obrigatórias que estão faltando."""
    return [c for c in COLUNAS_OBRIGATORIAS if c not in df.columns]


def relatorio_qualidade(df_bruto: pd.DataFrame) -> dict:
    """Resume problemas de qualidade encontrados na base bruta."""
    pop = df_bruto.groupby("municipio")["populacao"].nunique()
    return {
        "linhas": len(df_bruto),
        "colunas": df_bruto.shape[1],
        "nulos_total": int(df_bruto.isna().sum().sum()),
        "linhas_duplicadas_exatas": int(df_bruto.duplicated().sum()),
        "chaves_repetidas (data+município)": int(df_bruto.duplicated(["data", "municipio"]).sum()),
        "chuva_mm < 0": int((df_bruto["chuva_mm"] < 0).sum()),
        "ocorrências < 0": int((df_bruto["ocorrencias_deslizamento"] < 0).sum()),
        "indice_solo fora de [0, 1]": int((~df_bruto["indice_solo"].between(0, 1)).sum()),
        "umidade fora de [0, 100]": int((~df_bruto["umidade"].between(0, 100)).sum()),
        "municípios com população diferente a cada mês": int((pop > 1).sum()),
    }


def preparar(df_bruto: pd.DataFrame) -> pd.DataFrame:
    """Limpa tipos/textos e cria as variáveis derivadas usadas na análise."""
    df = df_bruto.copy()

  
    for col in ["municipio", "regiao_rj", "nivel_risco"]:
        df[col] = df[col].astype(str).str.strip()

    df["data"] = pd.to_datetime(df["data"], errors="coerce")
    for col in ["ano", "mes", "populacao", "chuva_mm", "temperatura_media", "ocorrencias_deslizamento",
                "desalojados", "obitos", "indice_solo", "umidade"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["data", "ano", "mes", "municipio", "chuva_mm", "ocorrencias_deslizamento"])
    df = df.drop_duplicates()
    df = df[(df["chuva_mm"] >= 0) & (df["ocorrencias_deslizamento"] >= 0)]
    for col in ["ano", "mes", "ocorrencias_deslizamento"]:
        df[col] = df[col].astype(int)
    for col in ["populacao", "desalojados", "obitos"]:
        df[col] = df[col].fillna(0).astype(int)
    df["indice_solo"] = df["indice_solo"].clip(0, 1)

    df["mes_nome"] = df["mes"].map(NOMES_MESES)
    df["trimestre"] = ((df["mes"] - 1) // 3 + 1).astype(int)
    df["estacao"] = pd.Categorical(
        np.where(df["mes"].isin(MESES_CHUVOSOS), ROTULO_CHUVOSA, ROTULO_MENOS),
        categories=[ROTULO_CHUVOSA, ROTULO_MENOS], ordered=True)
    df["nivel_risco"] = pd.Categorical(df["nivel_risco"], categories=ORDEM_RISCO, ordered=True)
    df["critico"] = (df["nivel_risco"] == "Crítico").astype(int)
    df["critico_pct"] = df["critico"] * 100
    df["chuva_intensa"] = (df["chuva_mm"] >= LIMIAR_CHUVA_INTENSA).astype(int)
    df["solo_saturado"] = (df["indice_solo"] >= LIMIAR_SOLO_SATURADO).astype(int)
    df["faixa_chuva"] = pd.cut(
        df["chuva_mm"], [-0.1, 50, 100, 150, 200, 300, np.inf],
        labels=["0–50 mm", "50–100 mm", "100–150 mm", "150–200 mm", "200–300 mm", "> 300 mm"])
    df["desalojados_por_ocorrencia"] = np.where(
        df["ocorrencias_deslizamento"] > 0, df["desalojados"] / df["ocorrencias_deslizamento"].replace(0, np.nan), np.nan)

    reta = reta_ajuste(df, "chuva_mm", "ocorrencias_deslizamento")
    a, b = reta if reta is not None else (0.0, df["ocorrencias_deslizamento"].mean())
    df["ocorrencias_esperadas"] = (a * df["chuva_mm"] + b).clip(lower=0)
    df["residuo"] = df["ocorrencias_deslizamento"] - df["ocorrencias_esperadas"]
    return df.sort_values(["data", "municipio"]).reset_index(drop=True)


def filtrar(df, anos=None, meses=None, municipios=None, regioes=None, niveis=None):
    """Aplica os filtros do dashboard. Parâmetro None = não filtra."""
    mask = pd.Series(True, index=df.index)
    if anos is not None:
        mask &= df["ano"].between(anos[0], anos[1])
    if meses is not None:
        mask &= df["mes"].isin(meses)
    if municipios is not None:
        mask &= df["municipio"].isin(municipios)
    if regioes is not None:
        mask &= df["regiao_rj"].isin(regioes)
    if niveis is not None:
        mask &= df["nivel_risco"].isin(niveis)
    return df[mask]


def classificar_forca(r: float) -> str:
    """Traduz o coeficiente de correlação em texto."""
    if r is None or np.isnan(r):
        return "indefinida"
    a = abs(r)
    if a < 0.10:
        return "praticamente nula"
    if a < 0.30:
        return "fraca"
    if a < 0.50:
        return "moderada"
    if a < 0.80:
        return "forte"
    return "muito forte"


def correlacao(df: pd.DataFrame, x: str, y: str = "ocorrencias_deslizamento") -> dict:
    """Correlação de Pearson e Spearman (com p-valores) entre duas colunas."""
    from scipy import stats

    d = df[[x, y]].dropna()
    vazio = {"r": np.nan, "p": np.nan, "rho": np.nan, "p_rho": np.nan, "n": len(d)}
    if len(d) < 3 or d[x].nunique() < 2 or d[y].nunique() < 2:
        return vazio
    r, p = stats.pearsonr(d[x], d[y])
    rho, p_rho = stats.spearmanr(d[x], d[y])
    return {"r": float(r), "p": float(p), "rho": float(rho), "p_rho": float(p_rho), "n": len(d)}


def reta_ajuste(df: pd.DataFrame, x: str, y: str = "ocorrencias_deslizamento"):
    """Coeficientes (a, b) da reta y = a*x + b ajustada por mínimos quadrados."""
    d = df[[x, y]].dropna()
    if len(d) < 3 or d[x].nunique() < 2:
        return None
    a, b = np.polyfit(d[x], d[y], 1)
    return float(a), float(b)


def anova(df: pd.DataFrame, por: str, y: str) -> dict:
    """ANOVA de um fator: os grupos de `por` têm médias de `y` diferentes? (F e p-valor)"""
    from scipy import stats

    grupos = [g[y].dropna().values for _, g in df.groupby(por, observed=True) if g[y].notna().sum() > 1]
    if len(grupos) < 2:
        return {"F": np.nan, "p": np.nan, "grupos": len(grupos)}
    f, p = stats.f_oneway(*grupos)
    return {"F": float(f), "p": float(p), "grupos": len(grupos)}


def teste_estacao(df: pd.DataFrame, y: str = "ocorrencias_deslizamento") -> dict:
    """Compara `y` entre a estação chuvosa e o resto do ano (Mann-Whitney, não paramétrico)."""
    from scipy import stats

    a = df.loc[df["estacao"] == ROTULO_CHUVOSA, y].dropna()
    b = df.loc[df["estacao"] == ROTULO_MENOS, y].dropna()
    if len(a) < 3 or len(b) < 3:
        return {"p": np.nan, "mediana_chuvosa": np.nan, "mediana_resto": np.nan}
    p = stats.mannwhitneyu(a, b, alternative="two-sided").pvalue
    return {"p": float(p), "mediana_chuvosa": float(a.median()), "mediana_resto": float(b.median())}


def resumo_estacao(df: pd.DataFrame) -> pd.DataFrame:
    """Resumo da estação chuvosa (dez–mar) x resto do ano."""
    g = df.groupby("estacao", observed=True)
    out = g.agg(
        registros=("chuva_mm", "size"),
        chuva_media_mm=("chuva_mm", "mean"),
        ocorrencias_media=("ocorrencias_deslizamento", "mean"),
        ocorrencias_total=("ocorrencias_deslizamento", "sum"),
        desalojados_total=("desalojados", "sum"),
        obitos_total=("obitos", "sum"),
        pct_critico=("critico_pct", "mean"),
    )
    total = out["ocorrencias_total"].sum()
    out["pct_das_ocorrencias"] = out["ocorrencias_total"] / total * 100 if total else np.nan
    out["pct_dos_registros"] = out["registros"] / out["registros"].sum() * 100
    return out


def perfil_mensal(df: pd.DataFrame) -> pd.DataFrame:
    """Média por mês do ano (jan–dez) — por município-mês."""
    return df.groupby("mes").agg(
        chuva_mm=("chuva_mm", "mean"),
        ocorrencias=("ocorrencias_deslizamento", "mean"),
        desalojados=("desalojados", "mean"),
        obitos=("obitos", "mean"),
    )


def _minmax(s: pd.Series) -> pd.Series:
    amp = s.max() - s.min()
    return (s - s.min()) / amp if amp else pd.Series(0.5, index=s.index)


def ranking_municipios(df: pd.DataFrame) -> pd.DataFrame:
    """Ranking de criticidade dos municípios.

    índice de criticidade (0–100) = média dos 4 indicadores normalizados (mín–máx):
    total de deslizamentos, % de registros em nível Crítico, total de desalojados e total de óbitos.
    """
    g = df.groupby("municipio")
    r = pd.DataFrame({
        "regiao": g["regiao_rj"].first(),
        "ocorrencias": g["ocorrencias_deslizamento"].sum(),
        "chuva_media_mm": g["chuva_mm"].mean(),
        "desalojados": g["desalojados"].sum(),
        "obitos": g["obitos"].sum(),
        "pct_critico": g["critico_pct"].mean(),
        "residuo_medio": g["residuo"].mean(),
    })
    r["ocorr_por_100mm"] = r["ocorrencias"] / g["chuva_mm"].sum() * 100
    comp = pd.concat([_minmax(r["ocorrencias"]), _minmax(r["pct_critico"]),
                      _minmax(r["desalojados"]), _minmax(r["obitos"])], axis=1)
    r["indice_criticidade"] = comp.mean(axis=1) * 100
    return r.sort_values("indice_criticidade", ascending=False)


def municipios_fora_do_padrao(df: pd.DataFrame) -> pd.DataFrame:
    """Compara, por município, os deslizamentos observados com o esperado pela chuva.

    `residuo_medio` > 0: mais deslizamentos do que a chuva "explica" (mais vulnerável).
    Teste t de uma amostra (H0: resíduo médio = 0).
    """
    from scipy import stats

    linhas = []
    for mun, g in df.groupby("municipio"):
        res = g["residuo"].dropna()
        if len(res) >= 3 and res.std() > 0:
            t, p = stats.ttest_1samp(res, 0.0)
        else:
            t, p = np.nan, np.nan
        classe = "dentro do padrão"
        if not np.isnan(p) and p < 0.01:
            classe = "acima do esperado" if res.mean() > 0 else "abaixo do esperado"
        linhas.append({"municipio": mun, "regiao": g["regiao_rj"].iloc[0], "observado_medio": g["ocorrencias_deslizamento"].mean(),
                       "esperado_medio": g["ocorrencias_esperadas"].mean(), "residuo_medio": res.mean(),
                       "t": t, "p": p, "classificacao": classe})
    return pd.DataFrame(linhas).set_index("municipio").sort_values("residuo_medio", ascending=False)


def eventos_extremos(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Registros com mais deslizamentos (ordem decrescente)."""
    cols = ["data", "municipio", "regiao_rj", "chuva_mm", "indice_solo", "ocorrencias_deslizamento",
            "desalojados", "obitos", "nivel_risco"]
    return df.sort_values(["ocorrencias_deslizamento", "chuva_mm"], ascending=False)[cols].head(n)


def outliers_iqr(df: pd.DataFrame, coluna: str) -> int:
    """Quantidade de valores fora de 1,5 x IQR."""
    q1, q3 = df[coluna].quantile([0.25, 0.75])
    iqr = q3 - q1
    return int(((df[coluna] < q1 - 1.5 * iqr) | (df[coluna] > q3 + 1.5 * iqr)).sum())


def resumo_alerta(df: pd.DataFrame) -> dict:
    """Registros com chuva intensa (>= 200 mm) E solo saturado (>= 0,8): quanto concentram do total?"""
    if df.empty:
        return {"pct_registros": np.nan, "pct_ocorrencias": np.nan, "pct_obitos": np.nan,
                "media_alerta": np.nan, "media_resto": np.nan, "pct_critico": np.nan, "n": 0}
    m = (df["chuva_intensa"] == 1) & (df["solo_saturado"] == 1)
    tot_o, tot_b = df["ocorrencias_deslizamento"].sum(), df["obitos"].sum()
    return {
        "pct_registros": m.mean() * 100,
        "pct_ocorrencias": df.loc[m, "ocorrencias_deslizamento"].sum() / tot_o * 100 if tot_o else np.nan,
        "pct_obitos": df.loc[m, "obitos"].sum() / tot_b * 100 if tot_b else np.nan,
        "media_alerta": df.loc[m, "ocorrencias_deslizamento"].mean() if m.any() else np.nan,
        "media_resto": df.loc[~m, "ocorrencias_deslizamento"].mean() if (~m).any() else np.nan,
        "pct_critico": df.loc[m, "critico_pct"].mean() if m.any() else np.nan,
        "n": int(m.sum()),
    }


def calcular_kpis(df: pd.DataFrame) -> dict | None:
    """KPIs do recorte atual. Retorna None se não houver dados."""
    if df.empty:
        return None
    por_mun = df.groupby("municipio")["ocorrencias_deslizamento"].sum()
    cor = correlacao(df, "chuva_mm", "ocorrencias_deslizamento")
    return {
        "volume_chuva": df["chuva_mm"].sum(),
        "media_chuva": df["chuva_mm"].mean(),
        "total_deslizamentos": int(df["ocorrencias_deslizamento"].sum()),
        "mun_critico": (por_mun.idxmax(), int(por_mun.max())),
        "desalojados": int(df["desalojados"].sum()),
        "obitos": int(df["obitos"].sum()),
        "corr": cor["r"],
        "pct_critico": df["critico_pct"].mean(),
        "n_obs": len(df),
    }


def serie_mensal(df: pd.DataFrame, coluna: str, agg: str, por: str | None = None, janela: int = 1) -> pd.DataFrame:
    """Série mensal de `coluna` (agg entre municípios), opcionalmente por grupo, com média móvel."""
    if por is None:
        s = df.groupby("data")[coluna].agg(agg).to_frame("Estado (total)" if agg == "sum" else "Estado (média)")
    else:
        s = df.pivot_table(index="data", columns=por, values=coluna, aggfunc=agg, observed=True)
    s = s.sort_index()
    if janela > 1:
        s = s.rolling(janela, min_periods=max(1, janela // 2)).mean()
    s.index.name = "data"
    s.columns.name = None
    return s


def totais_anuais(df: pd.DataFrame) -> pd.DataFrame:
    """Chuva (média entre municípios, somada no ano) e deslizamentos (total) por ano."""
    mensal = df.groupby(["ano", "mes"]).agg(chuva=("chuva_mm", "mean"), desl=("ocorrencias_deslizamento", "sum"))
    return mensal.groupby("ano").agg(chuva_anual_mm=("chuva", "sum"), deslizamentos=("desl", "sum"))


def correlacao_defasada(df: pd.DataFrame, max_lag: int = 3) -> pd.DataFrame:
    """Correlação entre os deslizamentos do mês t e a chuva de t-lag (série estadual mensal)."""
    s = df.groupby("data").agg(chuva=("chuva_mm", "mean"), desl=("ocorrencias_deslizamento", "sum")).sort_index()
    linhas = []
    for lag in range(0, max_lag + 1):
        r = s["desl"].corr(s["chuva"].shift(lag))
        linhas.append({"defasagem_meses": lag, "r": r})
    return pd.DataFrame(linhas).set_index("defasagem_meses")


def matriz_correlacao(df: pd.DataFrame) -> pd.DataFrame:
    """Matriz de correlação entre as principais variáveis numéricas (rótulos legíveis)."""
    cols = {"chuva_mm": "Chuva", "indice_solo": "Saturação do solo", "umidade": "Umidade",
            "temperatura_media": "Temperatura", "ocorrencias_deslizamento": "Deslizamentos",
            "desalojados": "Desalojados", "obitos": "Óbitos"}
    c = df[list(cols)].corr()
    c.index, c.columns = list(cols.values()), list(cols.values())
    return c



URL_API_CHUVA = "https://archive-api.open-meteo.com/v1/archive"


def buscar_chuva_real(municipio: str, ano_ini: int, ano_fim: int, timeout: int = 30) -> pd.DataFrame:
    """Consome a API pública Open-Meteo (histórico) e devolve a chuva mensal acumulada (mm) do município.

    Retorna colunas: municipio, ano, mes, chuva_real_mm. Levanta exceção se a API estiver
    indisponível (quem chama trata o erro).
    """
    import requests

    lat, lon = COORDENADAS[municipio]
    params = {
        "latitude": lat, "longitude": lon,
        "start_date": f"{ano_ini}-01-01", "end_date": f"{ano_fim}-12-31",
        "daily": "precipitation_sum", "timezone": "America/Sao_Paulo",
    }
    resposta = requests.get(URL_API_CHUVA, params=params, timeout=timeout)
    resposta.raise_for_status()
    dados = resposta.json()["daily"]
    d = pd.DataFrame({"data": pd.to_datetime(dados["time"]), "mm": pd.to_numeric(dados["precipitation_sum"], errors="coerce")})
    d["ano"], d["mes"] = d["data"].dt.year, d["data"].dt.month
    mensal = d.groupby(["ano", "mes"], as_index=False)["mm"].sum().rename(columns={"mm": "chuva_real_mm"})
    mensal.insert(0, "municipio", municipio)
    return mensal


def buscar_chuva_real_todos(municipios, ano_ini: int, ano_fim: int) -> pd.DataFrame:
    """Chama `buscar_chuva_real` para cada município que tenha coordenadas conhecidas."""
    partes = [buscar_chuva_real(m, ano_ini, ano_fim) for m in municipios if m in COORDENADAS]
    if not partes:
        raise ValueError("Nenhum município com coordenadas conhecidas.")
    return pd.concat(partes, ignore_index=True)


def comparar_com_api(df: pd.DataFrame, real: pd.DataFrame) -> dict:
    """Compara chuva simulada x observada: perfil sazonal, totais anuais e correlação mensal."""
    sim = df.groupby(["municipio", "ano", "mes"], as_index=False)["chuva_mm"].mean()
    j = sim.merge(real, on=["municipio", "ano", "mes"], how="inner")
    if j.empty:
        raise ValueError("Sem períodos em comum entre a base e a API.")
    sazonal = j.groupby("mes")[["chuva_mm", "chuva_real_mm"]].mean().rename(
        columns={"chuva_mm": "Simulada (base)", "chuva_real_mm": "Observada (Open-Meteo)"})
    anual = j.groupby(["municipio", "ano"])[["chuva_mm", "chuva_real_mm"]].sum().groupby("ano").mean().rename(
        columns={"chuva_mm": "Simulada (base)", "chuva_real_mm": "Observada (Open-Meteo)"})
    cor = correlacao(j, "chuva_mm", "chuva_real_mm")
    return {"sazonal": sazonal, "anual": anual, "r": cor["r"], "p": cor["p"], "n": cor["n"]}


def _formatar(ax, titulo, xlabel, ylabel):
    ax.set_title(titulo)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)


def fig_serie(df, coluna, agg, titulo, ylabel, por=None, janela=3, cor=COR_PRINCIPAL):
    """Linha temporal (média móvel) de uma variável, opcionalmente por grupo."""
    s = serie_mensal(df, coluna, agg, por=por, janela=janela)
    fig, ax = plt.subplots(figsize=(9, 4.6))
    for col in s.columns:
        c = PALETA_REGIAO.get(col) if por == "regiao_rj" else (cor if por is None else None)
        ax.plot(s.index, s[col], label=col, linewidth=1.6, color=c)
    _formatar(ax, titulo + (f" (média móvel de {janela} meses)" if janela > 1 else ""), "Data", ylabel)
    if len(s.columns) > 1:
        ax.legend(frameon=False, ncol=min(4, len(s.columns)), loc="upper center", bbox_to_anchor=(0.5, -0.15), fontsize=8)
    fig.tight_layout()
    return fig


def fig_barras(df, por, metrica, agg, titulo="", xlabel="", fmt="{:,.0f}", destacar=3):
    """Barras horizontais ordenadas; destaca em laranja os `destacar` maiores valores."""
    d = df.groupby(por, observed=True)[metrica].agg(agg).sort_values(ascending=False)
    cores = [COR_DESTAQUE if i < destacar else COR_NEUTRA for i in range(len(d))]
    fig, ax = plt.subplots(figsize=(8, max(3.0, 0.42 * len(d) + 1.4)))
    ax.barh(d.index.astype(str), d.values, color=cores)
    ax.invert_yaxis()
    ax.bar_label(ax.containers[0], labels=[_loc(fmt.format(v)) for v in d.values], padding=3, fontsize=8)
    limite = d.max() * 1.15 if d.max() > 0 else 1
    ax.set_xlim(min(0, d.min() * 1.15), limite)
    _formatar(ax, titulo, xlabel, {"municipio": "Município", "regiao_rj": "Região"}.get(por, por.capitalize()))
    fig.tight_layout()
    return fig


def fig_dispersao(df, x="chuva_mm", y="ocorrencias_deslizamento", titulo="", xlabel="", ylabel="", hue="regiao_rj"):
    """Dispersão com reta de ajuste e correlação de Pearson no título."""
    d = df[[x, y, hue]].dropna()
    fig, ax = plt.subplots(figsize=(7.8, 4.9))
    sns.scatterplot(data=d, x=x, y=y, hue=hue, palette=PALETA_REGIAO if hue == "regiao_rj" else None,
                    alpha=0.5, s=20, ax=ax)
    reta = reta_ajuste(d, x, y)
    if reta is not None:
        xs = np.linspace(d[x].min(), d[x].max(), 50)
        ax.plot(xs, reta[0] * xs + reta[1], color="black", linewidth=1.8, label="Reta de ajuste")
    c = correlacao(d, x, y)
    sufixo = f" (r = {c['r']:.2f}, n = {c['n']})" if not np.isnan(c["r"]) else ""
    _formatar(ax, f"{titulo}{sufixo}", xlabel, ylabel)
    ax.legend(frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=3)
    fig.tight_layout()
    return fig


def fig_heatmap(df, valor, agg, titulo, cmap="Blues", fmt=".0f", index="ano"):
    """Heatmap (ano ou município) x mês."""
    p = df.pivot_table(index=index, columns="mes", values=valor, aggfunc=agg)
    p.columns = [NOMES_MESES[m] for m in p.columns]
    altura = 4.8 if index == "ano" else 4.4
    fig, ax = plt.subplots(figsize=(9.5, altura))
    sns.heatmap(p, cmap=cmap, annot=True, fmt=fmt, annot_kws={"size": 7}, linewidths=0.4,
                cbar_kws={"label": ""}, ax=ax)
    _formatar(ax, titulo, "Mês", "Ano" if index == "ano" else "Município")
    fig.tight_layout()
    return fig


def fig_sazonal_dupla(df, titulo="Sazonalidade: chuva e deslizamentos por mês do ano"):
    """Barras (chuva média) + linha (deslizamentos médios) por mês do ano."""
    p = perfil_mensal(df)
    rotulos = [NOMES_MESES[m] for m in p.index]
    fig, ax = plt.subplots(figsize=(9, 4.8))
    cores = [COR_CHUVA if m in MESES_CHUVOSOS else COR_NEUTRA for m in p.index]
    ax.bar(rotulos, p["chuva_mm"], color=cores)
    ax.set_ylabel("Chuva média (mm/mês)", color=COR_CHUVA)
    ax2 = ax.twinx()
    ax2.plot(rotulos, p["ocorrencias"], color=COR_DESLIZ, marker="o", linewidth=2)
    ax2.set_ylabel("Deslizamentos por município-mês", color=COR_DESLIZ)
    ax2.grid(False)
    ax.set_title(titulo)
    ax.set_xlabel("Mês (barras escuras = dez–mar)")
    fig.tight_layout()
    return fig


def fig_boxplot_risco(df, y="ocorrencias_deslizamento", titulo="Deslizamentos por nível de risco", ylabel="Deslizamentos no mês"):
    """Boxplot de uma variável por nível de risco."""
    fig, ax = plt.subplots(figsize=(8, 4.6))
    sns.boxplot(data=df, x="nivel_risco", y=y, order=[n for n in ORDEM_RISCO if n in set(df["nivel_risco"])],
                hue="nivel_risco", palette="YlOrRd", legend=False, fliersize=2, ax=ax)
    _formatar(ax, titulo, "Nível de risco", ylabel)
    fig.tight_layout()
    return fig


def fig_correlacao(df, titulo="Matriz de correlação (Pearson)"):
    """Heatmap de correlação entre as principais variáveis."""
    c = matriz_correlacao(df)
    fig, ax = plt.subplots(figsize=(7, 5.4))
    sns.heatmap(c, cmap="RdBu_r", vmin=-1, vmax=1, annot=True, fmt=".2f", annot_kws={"size": 8},
                linewidths=0.4, cbar_kws={"label": "Correlação"}, ax=ax)
    ax.set_title(titulo)
    fig.tight_layout()
    return fig


def fig_defasagem(df, max_lag=3, titulo="Correlação com a chuva de meses anteriores"):
    """Barras da correlação defasada (deslizamentos em t x chuva em t-lag)."""
    c = correlacao_defasada(df, max_lag)
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    barras = ax.bar([f"{l} mês(es)" if l else "mesmo mês" for l in c.index], c["r"],
                    color=[COR_DESTAQUE if l == 0 else COR_NEUTRA for l in c.index])
    ax.bar_label(barras, labels=[_loc(f"{v:.2f}") for v in c["r"]], padding=2, fontsize=8)
    ax.set_ylim(min(0, c["r"].min() * 1.3), 1.05)
    ax.axhline(0, color="black", linewidth=0.8)
    _formatar(ax, titulo, "Defasagem da chuva", "Correlação (r)")
    fig.tight_layout()
    return fig


def fig_residuos(df, titulo="Deslizamentos: observado menos esperado pela chuva"):
    """Municípios acima/abaixo do padrão (resíduo médio do modelo de chuva)."""
    d = df.groupby("municipio")["residuo"].mean().sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(8, max(3.0, 0.42 * len(d) + 1.4)))
    ax.barh(d.index, d.values, color=[COR_DESTAQUE if v > 0 else COR_NEUTRA for v in d.values])
    ax.invert_yaxis()
    ax.axvline(0, color="black", linewidth=0.8)
    ax.bar_label(ax.containers[0], labels=[_loc(f"{v:+.2f}") for v in d.values], padding=3, fontsize=8)
    _formatar(ax, titulo, "Média mensal: a mais (+) ou a menos (−) que o esperado pela chuva", "Município")
    ax.margins(x=0.15)
    fig.tight_layout()
    return fig


def fig_ranking(df, titulo="Ranking de criticidade dos municípios (0–100)"):
    """Barras do índice de criticidade."""
    r = ranking_municipios(df)["indice_criticidade"]
    fig, ax = plt.subplots(figsize=(8, max(3.0, 0.42 * len(r) + 1.4)))
    ax.barh(r.index, r.values, color=[COR_DESTAQUE if i < 3 else COR_NEUTRA for i in range(len(r))])
    ax.invert_yaxis()
    ax.bar_label(ax.containers[0], labels=[_loc(f"{v:.0f}") for v in r.values], padding=3, fontsize=8)
    ax.set_xlim(0, 112)
    _formatar(ax, titulo, "Índice de criticidade", "Município")
    fig.tight_layout()
    return fig


def fig_barras_ano(serie, titulo, ylabel, cor=COR_PRINCIPAL, fmt="{:.0f}"):
    """Barras verticais por ano."""
    fig, ax = plt.subplots(figsize=(8, 4.4))
    barras = ax.bar(serie.index.astype(str), serie.values, color=cor)
    ax.bar_label(barras, labels=[_loc(fmt.format(v)) for v in serie.values], padding=2, fontsize=8)
    _formatar(ax, titulo, "Ano", ylabel)
    fig.tight_layout()
    return fig


def fig_distribuicao_chuva(df, titulo="Distribuição da chuva mensal por estação"):
    """Curvas de densidade da chuva por estação."""
    fig, ax = plt.subplots(figsize=(8, 4.4))
    sns.kdeplot(data=df, x="chuva_mm", hue="estacao", palette=[COR_CHUVA, COR_NEUTRA], common_norm=False,
                clip=(0, df["chuva_mm"].max()), linewidth=2, fill=True, alpha=0.25, ax=ax)
    ax.axvline(LIMIAR_CHUVA_INTENSA, color="gray", linestyle="--", linewidth=1)
    ax.text(LIMIAR_CHUVA_INTENSA + 4, ax.get_ylim()[1] * 0.9, f"{LIMIAR_CHUVA_INTENSA:.0f} mm", color="dimgray", fontsize=8)
    _formatar(ax, titulo, "Chuva no mês (mm)", "Densidade")
    fig.tight_layout()
    return fig


def fig_api_sazonal(sazonal, titulo="Perfil sazonal: chuva simulada x observada (API)"):
    """Compara o perfil mensal da base com a chuva observada (Open-Meteo)."""
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    s = sazonal.copy()
    s.index = [NOMES_MESES[m] for m in s.index]
    s.plot(kind="bar", ax=ax, color=[COR_DESTAQUE, COR_NEUTRA], width=0.8)
    ax.tick_params(axis="x", rotation=0)
    _formatar(ax, titulo, "Mês", "Chuva média (mm/mês)")
    ax.legend(frameon=False)
    fig.tight_layout()
    return fig


def plotly_serie(df, coluna, agg, ylabel, por=None, janela=3):
    """Linha temporal interativa (média móvel)."""
    import plotly.express as px

    s = serie_mensal(df, coluna, agg, por=por, janela=janela)
    longo = s.reset_index().melt(id_vars="data", var_name="grupo", value_name="valor")
    cores = PALETA_REGIAO if por == "regiao_rj" else None
    fig = px.line(longo, x="data", y="valor", color="grupo", color_discrete_map=cores,
                  labels={"data": "Data", "valor": ylabel, "grupo": ""})
    fig.update_layout(hovermode="x unified", legend=dict(orientation="h", y=-0.25), margin=dict(t=30))
    return fig


def plotly_dispersao(df, x, xlabel, y="ocorrencias_deslizamento", ylabel="Deslizamentos no mês"):
    """Dispersão interativa com reta de ajuste."""
    import plotly.express as px
    import plotly.graph_objects as go

    d = df.dropna(subset=[x, y])
    fig = px.scatter(d, x=x, y=y, color="regiao_rj", color_discrete_map=PALETA_REGIAO, opacity=0.55,
                     hover_data=["municipio", "ano", "mes"],
                     labels={x: xlabel, y: ylabel, "regiao_rj": "Região"})
    reta = reta_ajuste(d, x, y)
    if reta is not None:
        xs = np.linspace(d[x].min(), d[x].max(), 50)
        fig.add_trace(go.Scatter(x=xs, y=reta[0] * xs + reta[1], mode="lines", name="Reta de ajuste",
                                 line=dict(color="black", width=2)))
    fig.update_layout(title=f"{ylabel} x {xlabel}", legend=dict(orientation="h", y=-0.25))
    return fig


def plotly_mapa(df):
    """Mapa interativo dos municípios (bolha = total de deslizamentos; cor = % de registros críticos)."""
    import plotly.express as px

    r = ranking_municipios(df).reset_index()
    r = r[r["municipio"].isin(COORDENADAS)].copy()
    if r.empty:
        return None
    r["lat"] = r["municipio"].map(lambda m: COORDENADAS[m][0])
    r["lon"] = r["municipio"].map(lambda m: COORDENADAS[m][1])
    kwargs = dict(lat="lat", lon="lon", size="ocorrencias", color="pct_critico", hover_name="municipio",
                  hover_data={"ocorrencias": True, "desalojados": True, "obitos": True, "pct_critico": ":.1f",
                              "lat": False, "lon": False},
                  color_continuous_scale="YlOrRd", size_max=45, zoom=6.3,
                  center={"lat": -22.5, "lon": -43.0}, height=480,
                  labels={"pct_critico": "% crítico", "ocorrencias": "Deslizamentos"})
    if hasattr(px, "scatter_map"):  # Plotly >= 5.24
        fig = px.scatter_map(r, map_style="open-street-map", **kwargs)
    else:
        fig = px.scatter_mapbox(r, mapbox_style="open-street-map", **kwargs)
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
    return fig
