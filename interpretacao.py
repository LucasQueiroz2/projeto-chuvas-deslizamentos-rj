"""
interpretacao.py — textos analíticos gerados a partir dos dados filtrados.

Os números das interpretações vêm do próprio recorte selecionado no dashboard,
então o texto nunca fica desatualizado em relação aos gráficos.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import utils
from utils import br


def _p(p: float) -> str:
    """Texto curto sobre significância estatística."""
    if np.isnan(p):
        return "sem teste possível"
    if p < 0.001:
        return "estatisticamente significativa (p < 0,001)"
    return "estatisticamente significativa (p < 0,05)" if p < 0.05 else f"não significativa (p = {br(p, 2)})"


def _pv(p: float) -> str:
    """p-valor em texto: '< 0,001' ou '= 0,034'."""
    if np.isnan(p):
        return "= –"
    return "< 0,001" if p < 0.001 else f"= {br(p, 3)}"


def interpretar(df: pd.DataFrame) -> list[str]:
    """Lista de parágrafos (Markdown) interpretando o recorte atual."""
    k = utils.calcular_kpis(df)
    if k is None:
        return ["Não há dados para o recorte selecionado. Ajuste os filtros na barra lateral."]

    texto: list[str] = []
    texto.append(
        f"**Panorama.** O recorte tem {br(k['n_obs'], 0)} registros município-mês, com chuva média de "
        f"**{br(k['media_chuva'], 1)} mm/mês**, **{br(k['total_deslizamentos'], 0)} deslizamentos**, "
        f"**{br(k['desalojados'], 0)} desalojados** e **{br(k['obitos'], 0)} óbitos**."
    )

    # Municípios
    if df["municipio"].nunique() > 1:
        rk = utils.ranking_municipios(df)
        topo, base = rk.index[0], rk.index[-1]
        a = utils.anova(df, "municipio", "ocorrencias_deslizamento")
        texto.append(
            f"**Municípios.** **{topo}** é o mais crítico (índice {br(rk['indice_criticidade'].iloc[0], 0)}/100; "
            f"{br(rk['ocorrencias'].iloc[0], 0)} deslizamentos; {br(rk['pct_critico'].iloc[0], 1)}% dos registros em nível Crítico) e "
            f"**{base}** o menos crítico (índice {br(rk['indice_criticidade'].iloc[-1], 0)}). A diferença de deslizamentos médios "
            f"entre municípios é {_p(a['p'])}."
        )
    # Regiões
    if df["regiao_rj"].nunique() > 1 and df["ocorrencias_deslizamento"].sum() > 0:
        reg = df.groupby("regiao_rj")["ocorrencias_deslizamento"].sum().sort_values(ascending=False)
        pct = reg.iloc[0] / reg.sum() * 100
        texto.append(
            f"**Regiões.** A região **{reg.index[0]}** concentra **{br(pct, 1)}%** dos deslizamentos do recorte "
            f"({br(reg.iloc[0], 0)} de {br(reg.sum(), 0)})."
        )

    # Chuva x deslizamentos
    c = utils.correlacao(df, "chuva_mm", "ocorrencias_deslizamento")
    if not np.isnan(c["r"]):
        reta = utils.reta_ajuste(df, "chuva_mm", "ocorrencias_deslizamento")
        extra = f" Em média, cada 100 mm a mais de chuva se associa a cerca de **{br(reta[0] * 100, 1)} deslizamentos** a mais no mês." if reta else ""
        texto.append(
            f"**Chuva e deslizamentos.** A correlação é **{utils.classificar_forca(c['r'])}** "
            f"(Pearson r = {br(c['r'], 2)}; Spearman ρ = {br(c['rho'], 2)}; p {_pv(c['p'])}).{extra} "
            f"Correlação não implica causalidade: o solo saturado e a vulnerabilidade local também influenciam."
        )

    # Sazonalidade
    if df["mes"].nunique() >= 2:
        pm = utils.perfil_mensal(df)
        texto.append(
            f"**Sazonalidade.** O mês mais crítico é **{utils.NOMES_MESES[pm['ocorrencias'].idxmax()]}** "
            f"({br(pm['ocorrencias'].max(), 1)} deslizamentos por município) e o mais calmo é "
            f"**{utils.NOMES_MESES[pm['ocorrencias'].idxmin()]}** ({br(pm['ocorrencias'].min(), 1)})."
        )
    es = utils.resumo_estacao(df)
    if len(es) == 2:
        ch, rs = es.loc[utils.ROTULO_CHUVOSA], es.loc[utils.ROTULO_MENOS]
        t = utils.teste_estacao(df)
        texto.append(
            f"**Estação chuvosa (dez–mar).** Esses meses têm {br(ch['chuva_media_mm'], 0)} mm de chuva média contra "
            f"{br(rs['chuva_media_mm'], 0)} mm no resto do ano, e concentram **{br(ch['pct_das_ocorrencias'], 0)}%** dos deslizamentos "
            f"com apenas {br(ch['pct_dos_registros'], 0)}% dos meses. A diferença é {_p(t['p'])}."
        )

    # Risco
    texto.append(
        f"**Nível de risco.** {br(k['pct_critico'], 1)}% dos registros estão em nível “Crítico”."
    )

    # Evolução anual
    if df["ano"].nunique() >= 3:
        ta = utils.totais_anuais(df)
        texto.append(
            f"**Evolução.** O ano com mais deslizamentos foi **{ta['deslizamentos'].idxmax()}** "
            f"({br(ta['deslizamentos'].max(), 0)}) e o com menos foi **{ta['deslizamentos'].idxmin()}** "
            f"({br(ta['deslizamentos'].min(), 0)}), sem tendência clara de alta ou queda."
        )
    return texto


def conclusao_executiva(df: pd.DataFrame) -> str:
    """Conclusão executiva (Markdown) calculada sobre a base COMPLETA."""
    k = utils.calcular_kpis(df)
    rk = utils.ranking_municipios(df)
    fora = utils.municipios_fora_do_padrao(df)
    es = utils.resumo_estacao(df)
    ch, rs = es.loc[utils.ROTULO_CHUVOSA], es.loc[utils.ROTULO_MENOS]
    c = utils.correlacao(df, "chuva_mm", "ocorrencias_deslizamento")
    cs = utils.correlacao(df, "chuva_mm", "indice_solo")
    lag = utils.correlacao_defasada(df)["r"]
    reta = utils.reta_ajuste(df, "chuva_mm", "ocorrencias_deslizamento")
    reg = df.groupby("regiao_rj")["ocorrencias_deslizamento"].sum().sort_values(ascending=False)
    top3 = list(rk.index[:3])
    pct_top3 = rk["ocorrencias"].iloc[:3].sum() / rk["ocorrencias"].sum() * 100
    acima = list(fora.index[fora["classificacao"] == "acima do esperado"])
    al = utils.resumo_alerta(df)
    ta = utils.totais_anuais(df)
    tend = utils.correlacao(ta.reset_index(), "ano", "deslizamentos")

    return f"""
**Principal mensagem.** Os deslizamentos seguem a chuva **e** o lugar: a chuva explica grande parte das ocorrências
(r = {br(c['r'], 2)}; R² ≈ {br(c['r'] ** 2 * 100, 0)}%), mas **{br(pct_top3, 0)}% dos deslizamentos acontecem em apenas 3 dos {len(rk)} municípios**
({", ".join(top3)}), todos da região **{reg.index[0]}**. Esses municípios têm mais deslizamentos do que a chuva sozinha
prevê{" (os três)" if set(acima) == set(top3) else " (" + ", ".join(acima) + ")"}, o que indica vulnerabilidade própria (relevo, encostas, ocupação).

**O que se destaca.**
- **Sazonalidade marcante:** dezembro a março têm {br(ch['chuva_media_mm'], 0)} mm de chuva média (contra {br(rs['chuva_media_mm'], 0)} mm no resto do ano) e concentram
  **{br(ch['pct_das_ocorrencias'], 0)}% dos deslizamentos** e {br(ch['obitos_total'] / es['obitos_total'].sum() * 100 if es['obitos_total'].sum() else 0, 0)}% dos óbitos, com só {br(ch['pct_dos_registros'], 0)}% dos meses.
- **Chuva e solo saturado andam juntos** (r = {br(cs['r'], 2)}): o mecanismo esperado é chuva → solo encharcado → deslizamento. Cada 100 mm a mais de chuva se associa a ~{br(reta[0] * 100, 1)} deslizamentos a mais por município-mês.
- **O efeito é quase imediato:** a correlação com a chuva do mesmo mês é {br(lag.iloc[0], 2)}; com a chuva do mês anterior cai para {br(lag.iloc[1], 2)}.
- **Sem tendência ao longo dos anos:** o total anual de deslizamentos oscila entre {br(ta['deslizamentos'].min(), 0)} e {br(ta['deslizamentos'].max(), 0)}, sem alta ou queda consistente (p {_pv(tend['p'])}).

**Decisões e ações sugeridas.**
1. **Priorizar a região Serrana** ({", ".join(top3)}): obras de contenção, mapeamento de áreas de risco e defesa civil reforçada.
2. **Operar em modo de alerta de dezembro a março**: mobilização preventiva, sirenes e plano de evacuação antes da estação chuvosa.
3. **Acionar o alerta pelo volume de chuva e pelo solo**: registros com chuva ≥ {br(utils.LIMIAR_CHUVA_INTENSA, 0)} mm **e** solo saturado (índice ≥ {br(utils.LIMIAR_SOLO_SATURADO, 1)}) são só {br(al['pct_registros'], 0)}% dos meses, mas concentram {br(al['pct_ocorrencias'], 0)}% dos deslizamentos e {br(al['pct_obitos'], 0)}% dos óbitos ({br(al['media_alerta'], 1)} deslizamentos por município-mês, contra {br(al['media_resto'], 1)} nos demais).
4. **Monitorar fora da estação chuvosa**, pois {br(100 - ch['pct_das_ocorrencias'], 0)}% dos deslizamentos ocorrem nos outros meses.

**Limitações.** Dados simulados e apenas 8 municípios; uma observação por município e mês; a coluna `populacao` muda a cada mês no mesmo município (valores
entre ~120 mil e ~6,5 milhões, inclusive Niterói acima do Rio de Janeiro), então **não foi usada para taxas por habitante**; `desalojados` é quase proporcional
a `ocorrencias_deslizamento` (r > 0,99), logo não traz informação independente; `nivel_risco` não é função exata da chuva (as faixas se sobrepõem);
e o resíduo dos municípios é calculado contra uma reta global, que é puxada para cima pela região Serrana.
"""
