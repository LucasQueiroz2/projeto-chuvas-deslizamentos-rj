
from __future__ import annotations

import io

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

import interpretacao
import utils
from database import db
from utils import br

# ----------------------------------------------------------------------------
# Configuração da página
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="Chuvas e Deslizamentos no RJ",
    page_icon="🌧️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ----------------------------------------------------------------------------
# Carga de dados (cache) — banco SQLite via SQLAlchemy, com upload opcional
# ----------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def obter_engine():
    return db.get_engine()


@st.cache_data(show_spinner="Carregando dados do banco SQLite...")
def carregar_base() -> tuple[pd.DataFrame, dict]:
    """Lê a base do SQLite (criando o banco a partir do CSV se ele ainda não existir)."""
    engine = obter_engine()
    bruto = utils.carregar_csv(utils.CAMINHO_CSV)
    qualidade = utils.relatorio_qualidade(bruto)
    if not db.banco_pronto(engine):
        db.criar_banco(utils.preparar(bruto), engine)
    return utils.preparar(db.carregar_do_banco(engine)), qualidade


@st.cache_data(show_spinner="Lendo o arquivo enviado...")
def carregar_upload(conteudo: bytes) -> tuple[pd.DataFrame | None, dict | None, list[str]]:
    """Valida e prepara um CSV enviado pelo usuário (mesmo formato da base original)."""
    bruto = pd.read_csv(io.BytesIO(conteudo), encoding="utf-8-sig")
    faltando = utils.validar_colunas(bruto)
    if faltando:
        return None, None, faltando
    return utils.preparar(bruto), utils.relatorio_qualidade(bruto), []


@st.cache_data(show_spinner="Consultando a API Open-Meteo (chuva observada)...", ttl=3600)
def carregar_chuva_api(municipios: tuple[str, ...], ano_ini: int, ano_fim: int) -> pd.DataFrame:
    return utils.buscar_chuva_real_todos(municipios, ano_ini, ano_fim)


def mostrar(fig) -> None:
    """Exibe uma figura Matplotlib e libera a memória."""
    st.pyplot(fig)
    plt.close(fig)


# ----------------------------------------------------------------------------
# Cabeçalho
# ----------------------------------------------------------------------------
st.title("🌧️ Chuvas e Deslizamentos no Estado do Rio de Janeiro (2015–2024)")
st.caption("Projeto G1 — Análise e Visualização de Dados com Python · Lucas Queiroz Paes Leme · Dados simulados (Dados-Simulados-G2, Tema 2)")

with st.expander("📌 Descrição do problema", expanded=True):
    st.markdown(
        """
Chuvas intensas causam **enchentes, alagamentos e deslizamentos de terra**, principalmente em cidades serranas e áreas de encosta.
O Estado do Rio de Janeiro tem um histórico recorrente de desastres desse tipo, com desalojados e óbitos.

**Perguntas que este dashboard responde:**
1. Quais municípios têm mais chuva e mais deslizamentos? Quais são os mais críticos?
2. Há meses e períodos sazonais mais perigosos?
3. A chuva intensa aumenta os deslizamentos? Quão forte é essa relação?
4. Existem municípios com comportamento fora do padrão?

**Decisão apoiada:** onde priorizar obras e defesa civil, e quando operar em alerta.
Use os **filtros da barra lateral** (ano, mês, município, região e nível de risco) para explorar qualquer recorte.
"""
    )

# ----------------------------------------------------------------------------
# Barra lateral: fonte de dados e filtros
# ----------------------------------------------------------------------------
st.sidebar.header("🗂️ Fonte dos dados")
arquivo = st.sidebar.file_uploader(
    "Enviar outro CSV (mesmo formato da base)", type="csv",
    help="Opcional. O arquivo precisa ter as 14 colunas da base original (ano, mes, data, municipio, regiao_rj, ...).",
)

df_total, qualidade = carregar_base()
fonte = "Banco SQLite (database/chuvas.db)"
if arquivo is not None:
    df_up, q_up, faltando = carregar_upload(arquivo.getvalue())
    if faltando:
        st.sidebar.error("O arquivo enviado não tem as colunas: " + ", ".join(faltando))
    else:
        df_total, qualidade, fonte = df_up, q_up, f"Arquivo enviado ({arquivo.name})"
st.sidebar.caption(f"Fonte atual: {fonte}")

st.sidebar.header("🎛️ Filtros")
ano_min, ano_max = int(df_total["ano"].min()), int(df_total["ano"].max())
anos = st.sidebar.slider("Ano", ano_min, ano_max, (ano_min, ano_max)) if ano_min < ano_max else (ano_min, ano_max)

todos_meses = list(range(1, 13))
meses = st.sidebar.multiselect("Mês", todos_meses, default=todos_meses, format_func=lambda m: utils.NOMES_MESES[m])

regioes_opc = sorted(df_total["regiao_rj"].unique())
regioes = st.sidebar.multiselect("Região", regioes_opc, default=regioes_opc)

muns_opc = sorted(df_total[df_total["regiao_rj"].isin(regioes)]["municipio"].unique())
municipios = st.sidebar.multiselect("Município", muns_opc, default=muns_opc)

niveis = st.sidebar.multiselect("Nível de risco", utils.ORDEM_RISCO, default=utils.ORDEM_RISCO)

df = utils.filtrar(df_total, anos=anos, meses=meses, municipios=municipios, regioes=regioes, niveis=niveis)

st.sidebar.markdown("---")
st.sidebar.metric("Registros no recorte", br(len(df), 0), help=f"De um total de {br(len(df_total), 0)} registros município-mês.")

if df.empty:
    st.warning("Nenhum dado corresponde aos filtros selecionados. Ajuste a barra lateral para continuar.")
    st.stop()

# ----------------------------------------------------------------------------
# KPIs
# ----------------------------------------------------------------------------
k = utils.calcular_kpis(df)
st.subheader("📊 Indicadores-chave (KPIs)")
c1, c2, c3 = st.columns(3)
c1.metric("Volume total de chuva", f"{br(k['volume_chuva'], 0)} mm",
          help="Soma da chuva de todos os registros município-mês do recorte.")
c2.metric("Média de chuva", f"{br(k['media_chuva'], 1)} mm/mês", help="Média mensal por município.")
c3.metric("Total de deslizamentos", br(k["total_deslizamentos"], 0))
c4, c5, c6 = st.columns(3)
c4.metric("Município mais crítico", k["mun_critico"][0], f"{br(k['mun_critico'][1], 0)} deslizamentos", delta_color="off")
c5.metric("Total de desalojados", br(k["desalojados"], 0), f"{br(k['obitos'], 0)} óbitos", delta_color="off")
c6.metric("Correlação chuva × deslizamentos", br(k["corr"], 2) if not np.isnan(k["corr"]) else "–",
          utils.classificar_forca(k["corr"]), delta_color="off", help="Pearson entre chuva_mm e ocorrencias_deslizamento.")

# ----------------------------------------------------------------------------
# Seções (abas)
# ----------------------------------------------------------------------------
aba_geral, aba_mun, aba_saz, aba_corr, aba_risco, aba_tab, aba_concl = st.tabs([
    "📈 Evolução temporal", "🏙️ Municípios", "🗓️ Sazonalidade",
    "🔗 Chuva × deslizamentos", "⚠️ Nível de risco", "🧮 Tabelas e SQL", "📝 Interpretação e conclusão",
])

# ---- 1) Evolução temporal --------------------------------------------------
with aba_geral:
    col_a, col_b = st.columns([1, 4])
    with col_a:
        agrupar = st.radio("Agrupar linhas por", ["Nenhum (estado)", "Região"])
        janela = st.slider("Média móvel (meses)", 1, 12, 3)
    por = {"Nenhum (estado)": None, "Região": "regiao_rj"}[agrupar]
    with col_b:
        st.markdown("**Evolução da chuva** (média entre municípios)")
        st.plotly_chart(utils.plotly_serie(df, "chuva_mm", "mean", "Chuva (mm/mês)", por=por, janela=janela))
        st.markdown("**Evolução dos deslizamentos** (total por mês)")
        st.plotly_chart(utils.plotly_serie(df, "ocorrencias_deslizamento", "sum", "Deslizamentos por mês", por=por, janela=janela))
    st.caption("Gráficos interativos (zoom, passe o mouse, clique na legenda). Os picos se repetem todo verão, sinal de forte sazonalidade.")
    if df["ano"].nunique() > 1:
        ta = utils.totais_anuais(df)
        ca, cb = st.columns(2)
        with ca:
            mostrar(utils.fig_barras_ano(ta["chuva_anual_mm"], "Chuva anual (média dos municípios)", "mm no ano",
                                         cor=utils.COR_CHUVA))
        with cb:
            mostrar(utils.fig_barras_ano(ta["deslizamentos"], "Deslizamentos por ano", "Deslizamentos", cor=utils.COR_DESLIZ))

# ---- 2) Municípios ---------------------------------------------------------
with aba_mun:
    rotulo = st.selectbox("Métrica de comparação", list(utils.METRICAS.keys()))
    coluna, agg, formato = utils.METRICAS[rotulo]
    col_a, col_b = st.columns(2)
    with col_a:
        mostrar(utils.fig_barras(df, "municipio", coluna, agg, f"{rotulo} por município", rotulo, formato))
    with col_b:
        mostrar(utils.fig_barras(df, "regiao_rj", coluna, agg, f"{rotulo} por região", rotulo, formato, destacar=1))

    st.markdown("#### Ranking de municípios críticos")
    st.caption("Índice de criticidade (0–100) = média de 4 indicadores normalizados: total de deslizamentos, % de registros em nível Crítico, "
               "desalojados e óbitos.")
    rk = utils.ranking_municipios(df)
    col_c, col_d = st.columns([3, 2])
    with col_c:
        mostrar(utils.fig_ranking(df))
    with col_d:
        st.dataframe(rk.rename(columns={
            "regiao": "Região", "ocorrencias": "Deslizamentos", "chuva_media_mm": "Chuva média (mm)", "desalojados": "Desalojados",
            "obitos": "Óbitos", "pct_critico": "% Crítico", "residuo_medio": "Resíduo médio", "ocorr_por_100mm": "Deslizam./100 mm",
            "indice_criticidade": "Índice"}).round(2))

    st.markdown("#### Mapa interativo")
    mapa = utils.plotly_mapa(df)
    if mapa is None:
        st.info("Os municípios deste arquivo não têm coordenadas cadastradas para o mapa.")
    else:
        st.plotly_chart(mapa)
        st.caption("Tamanho da bolha = total de deslizamentos; cor = % de registros em nível Crítico.")

    st.markdown("#### Municípios fora do padrão")
    st.caption("Compara os deslizamentos observados com o esperado pela chuva (reta ajustada em toda a base). "
               "Resíduo > 0: mais deslizamentos do que a chuva explica.")
    col_e, col_f = st.columns([3, 2])
    with col_e:
        mostrar(utils.fig_residuos(df))
    with col_f:
        fp = utils.municipios_fora_do_padrao(df)
        st.dataframe(fp[["regiao", "observado_medio", "esperado_medio", "residuo_medio", "classificacao"]].rename(columns={
            "regiao": "Região", "observado_medio": "Observado/mês", "esperado_medio": "Esperado/mês",
            "residuo_medio": "Resíduo", "classificacao": "Classificação"}).round(2))

# ---- 3) Sazonalidade -------------------------------------------------------
with aba_saz:
    col_a, col_b = st.columns(2)
    with col_a:
        mostrar(utils.fig_sazonal_dupla(df))
    with col_b:
        mostrar(utils.fig_distribuicao_chuva(df))
    escolha = st.radio("Heatmap de", ["Chuva média (mm)", "Deslizamentos (total)"], horizontal=True)
    if escolha.startswith("Chuva"):
        mostrar(utils.fig_heatmap(df, "chuva_mm", "mean", "Chuva média por ano e mês (mm)", cmap="Blues"))
        mostrar(utils.fig_heatmap(df, "chuva_mm", "mean", "Chuva média por município e mês (mm)", cmap="Blues", index="municipio"))
    else:
        mostrar(utils.fig_heatmap(df, "ocorrencias_deslizamento", "sum", "Deslizamentos por ano e mês", cmap="OrRd"))
        mostrar(utils.fig_heatmap(df, "ocorrencias_deslizamento", "sum", "Deslizamentos por município e mês", cmap="OrRd", index="municipio"))
    st.markdown("#### Estação chuvosa (dezembro a março) x resto do ano")
    es = utils.resumo_estacao(df)
    st.dataframe(es.rename(columns={
        "registros": "Registros", "chuva_media_mm": "Chuva média (mm)", "ocorrencias_media": "Deslizam. médios",
        "ocorrencias_total": "Deslizam. total", "desalojados_total": "Desalojados", "obitos_total": "Óbitos",
        "pct_critico": "% Crítico", "pct_das_ocorrencias": "% dos deslizamentos", "pct_dos_registros": "% dos meses"}).round(1))
    te = utils.teste_estacao(df)
    if not np.isnan(te["p"]):
        st.info(f"Mediana de deslizamentos: {br(te['mediana_chuvosa'], 0)} na estação chuvosa x {br(te['mediana_resto'], 0)} no resto do ano "
                f"(teste de Mann-Whitney: p {'< 0,001' if te['p'] < 0.001 else '= ' + br(te['p'], 3)}).")

# ---- 4) Chuva x deslizamentos ---------------------------------------------
with aba_corr:
    st.markdown("#### Correlação estatística")
    opcoes = {"Chuva (mm)": "chuva_mm", "Saturação do solo (índice)": "indice_solo",
              "Umidade (%)": "umidade", "Temperatura média (°C)": "temperatura_media"}
    escolha_x = st.radio("Variável explicativa", list(opcoes.keys()), horizontal=True)
    x = opcoes[escolha_x]
    cor = utils.correlacao(df, x, "ocorrencias_deslizamento")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Pearson (r)", br(cor["r"], 2), help="Correlação linear.")
    m2.metric("Spearman (ρ)", br(cor["rho"], 2), help="Correlação de postos (robusta a outliers).")
    m3.metric("p-valor", "< 0,001" if cor["p"] < 0.001 else br(cor["p"], 3), help="p < 0,05 indica correlação significativa.")
    m4.metric("Registros (n)", br(cor["n"], 0))
    st.write(f"Força da relação com os deslizamentos: **{utils.classificar_forca(cor['r'])}**.")
    col_a, col_b = st.columns([3, 2])
    with col_a:
        st.plotly_chart(utils.plotly_dispersao(df, x, escolha_x))
    with col_b:
        mostrar(utils.fig_correlacao(df))

    if df["data"].nunique() > 6:
        st.markdown("#### Efeito defasado: a chuva de meses anteriores ainda importa?")
        cl, cr = st.columns([3, 2])
        with cl:
            mostrar(utils.fig_defasagem(df))
        with cr:
            st.write("Correlação entre os **deslizamentos do mês** e a **chuva do mesmo mês ou de meses anteriores** (série mensal do recorte). "
                     "Se a correlação cai rápido, o efeito é imediato.")

    al = utils.resumo_alerta(df)
    if al["n"] > 0:
        st.success(
            f"**Condição de alerta** (chuva ≥ {br(utils.LIMIAR_CHUVA_INTENSA, 0)} mm e solo ≥ {br(utils.LIMIAR_SOLO_SATURADO, 1)}): "
            f"{br(al['pct_registros'], 0)}% dos registros, mas {br(al['pct_ocorrencias'], 0)}% dos deslizamentos e "
            f"{br(al['pct_obitos'], 0)}% dos óbitos ({br(al['media_alerta'], 1)} deslizamentos por município-mês contra {br(al['media_resto'], 1)}).")

    st.markdown("#### Integração de fontes: chuva simulada × chuva observada (API Open-Meteo)")
    usar_api = st.checkbox("Consultar a API Open-Meteo (requests) e comparar com a base")
    if usar_api:
        try:
            real = carregar_chuva_api(tuple(sorted(df["municipio"].unique())), int(df["ano"].min()), int(df["ano"].max()))
            comp = utils.comparar_com_api(df, real)
            try:  # guarda a chuva observada no banco (persistência da 2ª fonte)
                n_salvas = db.salvar_chuva_api(real, obter_engine())
                st.caption(f"{br(n_salvas, 0)} registros mensais da API gravados na tabela `chuva_api` do banco.")
            except Exception:
                pass
            col_l, col_r = st.columns([3, 2])
            with col_l:
                mostrar(utils.fig_api_sazonal(comp["sazonal"]))
            with col_r:
                st.metric("Correlação mensal (simulada × observada)", br(comp["r"], 2), f"n = {br(comp['n'], 0)}", delta_color="off")
                st.dataframe(comp["anual"].round(0))
            st.caption("Fonte: Open-Meteo Historical Weather API (gratuita, sem chave). A chuva da base é simulada e "
                       "não precisa coincidir com a observada; a comparação mostra o quanto a base se parece com a realidade.")
        except Exception as erro:  # sem internet, API fora do ar etc.
            st.warning(f"Não foi possível consultar a API agora ({type(erro).__name__}). Tente novamente mais tarde.")

# ---- 5) Nível de risco -----------------------------------------------------
with aba_risco:
    st.markdown("#### Como o nível de risco se relaciona com chuva, solo e deslizamentos")
    col_a, col_b = st.columns(2)
    with col_a:
        mostrar(utils.fig_boxplot_risco(df))
    with col_b:
        mostrar(utils.fig_boxplot_risco(df, y="chuva_mm", titulo="Chuva por nível de risco", ylabel="Chuva no mês (mm)"))
    col_c, col_d = st.columns(2)
    with col_c:
        mostrar(utils.fig_barras(df, "municipio", "critico_pct", "mean", "% de registros em nível Crítico por município",
                                 "% de registros Crítico", "{:,.1f}"))
    with col_d:
        dist = df.groupby("nivel_risco", observed=True).size().reindex(utils.ORDEM_RISCO).fillna(0)
        st.markdown("**Distribuição dos registros por nível**")
        st.dataframe(pd.DataFrame({"Registros": dist.astype(int), "%": (dist / dist.sum() * 100).round(1)}))
        st.markdown("**Maiores ocorrências do recorte**")
        st.dataframe(utils.eventos_extremos(df, 8).assign(data=lambda d: d["data"].dt.strftime("%m/%Y")), hide_index=True)

# ---- 6) Tabelas e SQL ------------------------------------------------------
with aba_tab:
    st.markdown("#### Tabela dinâmica")
    dimensoes = {"Município": "municipio", "Região": "regiao_rj", "Ano": "ano", "Mês": "mes",
                 "Nível de risco": "nivel_risco", "Estação": "estacao", "Faixa de chuva": "faixa_chuva"}
    valores = {"Deslizamentos": "ocorrencias_deslizamento", "Chuva (mm)": "chuva_mm", "Desalojados": "desalojados",
               "Óbitos": "obitos", "Saturação do solo": "indice_solo"}
    cA, cB, cC, cD = st.columns(4)
    linhas = cA.selectbox("Linhas", list(dimensoes.keys()), index=0)
    colunas = cB.selectbox("Colunas", ["(nenhuma)"] + list(dimensoes.keys()), index=4)
    valor = cC.selectbox("Valor", list(valores.keys()))
    funcao = cD.selectbox("Função", ["sum", "mean", "median", "max", "min", "count"])
    if colunas == linhas:
        st.info("Escolha uma coluna diferente da linha para montar o cruzamento.")
    else:
        pivot = pd.pivot_table(df, index=dimensoes[linhas], columns=None if colunas == "(nenhuma)" else dimensoes[colunas],
                               values=valores[valor], aggfunc=funcao, observed=True)
        st.dataframe(pivot.round(2))

    st.markdown("#### Dados filtrados")
    mostrar_cols = ["data", "municipio", "regiao_rj", "chuva_mm", "indice_solo", "umidade", "temperatura_media",
                    "ocorrencias_deslizamento", "desalojados", "obitos", "nivel_risco"]
    st.dataframe(df[mostrar_cols].head(500), hide_index=True)
    st.caption(f"Mostrando até 500 de {br(len(df), 0)} linhas do recorte.")
    st.download_button("⬇️ Baixar dados filtrados (CSV)", df[mostrar_cols].to_csv(index=False).encode("utf-8"),
                       file_name="chuvas_deslizamentos_filtrado.csv", mime="text/csv")

    st.markdown("#### Consultas SQL no banco (SQLAlchemy + SQLite)")
    st.caption("As consultas usam o banco completo (todos os anos), independentemente dos filtros acima. Somente leitura.")
    with st.expander("Esquema relacional do banco"):
        st.caption(f"Motor de acesso ao banco: {db.MOTOR}")
        st.dataframe(db.descrever_esquema(obter_engine()), hide_index=True)
        st.code("regioes (id_regiao PK, nome)\nmunicipios (id_municipio PK, nome, id_regiao FK, latitude, longitude)\n"
                "registros (id PK, data, ano, mes, id_municipio FK, chuva_mm, ocorrencias_deslizamento, ...)\n"
                "chuva_api (id_municipio FK, ano, mes, chuva_real_mm)\nvw_registros = view com os JOINs", language="text")
    nome_consulta = st.selectbox("Consulta pronta", list(db.CONSULTAS_PRONTAS.keys()))
    sql = st.text_area("SQL (você pode editar)", db.CONSULTAS_PRONTAS[nome_consulta], height=150, key=f"sql_{nome_consulta}")
    if st.button("▶️ Executar consulta"):
        try:
            resultado = db.executar_consulta(sql, obter_engine())
            st.success(f"{len(resultado)} linha(s) retornada(s).")
            st.dataframe(resultado, hide_index=True)
        except Exception as erro:
            st.error(f"Erro na consulta: {erro}")

# ---- 7) Interpretação e conclusão -----------------------------------------
with aba_concl:
    st.markdown("### Interpretação do recorte selecionado")
    for paragrafo in interpretacao.interpretar(df):
        st.markdown(f"- {paragrafo}")

    st.markdown("### Conclusão executiva (base completa)")
    st.markdown(interpretacao.conclusao_executiva(df_total))

    with st.expander("🔍 Qualidade dos dados (base bruta)"):
        st.dataframe(pd.DataFrame({"verificação": list(qualidade.keys()), "resultado": list(qualidade.values())}), hide_index=True)

st.markdown("---")
st.caption("Projeto acadêmico com dados simulados — os resultados não representam a situação real dos municípios.")
