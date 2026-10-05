"""Gera o index.html (página do projeto para o GitHub Pages) com os números calculados a partir da base."""
import utils
from utils import br

df = utils.preparar(utils.carregar_csv())
k = utils.calcular_kpis(df)
rk = utils.ranking_municipios(df)
es = utils.resumo_estacao(df)
ch, rs = es.loc[utils.ROTULO_CHUVOSA], es.loc[utils.ROTULO_MENOS]
c = utils.correlacao(df, "chuva_mm", "ocorrencias_deslizamento")
reta = utils.reta_ajuste(df, "chuva_mm", "ocorrencias_deslizamento")
al = utils.resumo_alerta(df)
top3 = list(rk.index[:3])
pct_top3 = rk["ocorrencias"].iloc[:3].sum() / rk["ocorrencias"].sum() * 100
pct_obitos = ch["obitos_total"] / es["obitos_total"].sum() * 100
lag = utils.correlacao_defasada(df)["r"]

HTML = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Chuvas e Deslizamentos no Rio de Janeiro (2015–2024) — Projeto G1</title>
<meta name="description" content="Projeto de análise e visualização de dados com Python: chuvas e deslizamentos no Estado do Rio de Janeiro, dashboard Streamlit e notebook.">
<style>
  :root {{ --bg:#f4f7fa; --card:#fff; --ink:#1c2733; --muted:#5b6b7b; --acc:#d95f02; --acc2:#1f6fa8; --line:#e0e7ef; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; background:var(--bg); color:var(--ink); line-height:1.6; }}
  header {{ background:linear-gradient(135deg,#0f2a43,#1f6fa8); color:#fff; padding:56px 20px 48px; text-align:center; }}
  header h1 {{ margin:0 0 8px; font-size:clamp(1.6rem,4vw,2.4rem); }}
  header p {{ margin:0 auto; max-width:780px; opacity:.93; }}
  .botoes {{ margin-top:24px; display:flex; gap:12px; justify-content:center; flex-wrap:wrap; }}
  .botoes a {{ background:#fff; color:#0f2a43; padding:10px 20px; border-radius:8px; text-decoration:none; font-weight:600; }}
  .botoes a.sec {{ background:transparent; color:#fff; border:2px solid #fff; }}
  nav {{ background:#fff; border-bottom:1px solid var(--line); position:sticky; top:0; z-index:5; }}
  nav ul {{ list-style:none; margin:0 auto; padding:0 12px; max-width:1050px; display:flex; gap:4px; overflow-x:auto; }}
  nav a {{ display:block; padding:14px 12px; color:var(--muted); text-decoration:none; font-size:.92rem; white-space:nowrap; }}
  nav a:hover {{ color:var(--acc2); }}
  main {{ max-width:1050px; margin:0 auto; padding:8px 20px 60px; }}
  section {{ margin-top:44px; }}
  h2 {{ font-size:1.5rem; margin:0 0 14px; border-left:5px solid var(--acc); padding-left:12px; }}
  .grid {{ display:grid; gap:16px; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); }}
  .card {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:18px; }}
  .kpi small {{ color:var(--muted); display:block; }}
  .kpi strong {{ font-size:1.5rem; color:var(--acc2); display:block; }}
  .kpi span {{ font-size:.85rem; color:var(--muted); }}
  figure {{ margin:0; background:var(--card); border:1px solid var(--line); border-radius:12px; padding:12px; }}
  figure img {{ width:100%; height:auto; border-radius:6px; }}
  figcaption {{ font-size:.9rem; color:var(--muted); margin-top:8px; }}
  .duas {{ display:grid; gap:16px; grid-template-columns:repeat(auto-fit,minmax(340px,1fr)); }}
  .aviso {{ background:#fff7ed; border:1px solid #fed7aa; border-radius:12px; padding:16px 18px; }}
  table {{ width:100%; border-collapse:collapse; background:#fff; border:1px solid var(--line); border-radius:12px; overflow:hidden; font-size:.93rem; }}
  th, td {{ padding:10px 12px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }}
  th {{ background:#eaf1f8; }}
  code, pre {{ background:#eaf1f8; border-radius:6px; font-size:.88rem; }}
  code {{ padding:1px 5px; }} pre {{ padding:14px; overflow-x:auto; }}
  .tags span {{ display:inline-block; background:#e3eefa; color:#14507f; border-radius:20px; padding:3px 12px; margin:3px 4px 3px 0; font-size:.85rem; }}
  footer {{ text-align:center; color:var(--muted); padding:28px 20px; border-top:1px solid var(--line); font-size:.9rem; }}
</style>
</head>
<body>
<header>
  <h1>🌧️ Chuvas e Deslizamentos no Estado do Rio de Janeiro (2015–2024)</h1>
  <p>Projeto de análise e visualização de dados com Python: tratamento da base, KPIs, estatística, banco SQLite, API de chuva, dashboard interativo em Streamlit e publicação online.</p>
  <div class="botoes">
    <a id="lnk-dash" href="#">Abrir o dashboard</a>
    <a id="lnk-repo" class="sec" href="#">Código no GitHub</a>
    <a id="lnk-nb" class="sec" href="#">Notebook</a>
  </div>
</header>

<nav><ul>
  <li><a href="#problema">Problema</a></li><li><a href="#base">Base</a></li><li><a href="#kpis">KPIs</a></li>
  <li><a href="#graficos">Gráficos</a></li><li><a href="#achados">Resultados</a></li><li><a href="#tecnologias">Tecnologias</a></li>
  <li><a href="#estrutura">Estrutura</a></li><li><a href="#executar">Como executar</a></li>
</ul></nav>

<main>
<section id="problema">
  <h2>O problema</h2>
  <p>Chuvas intensas causam <strong>enchentes, alagamentos e deslizamentos de terra</strong>, principalmente em cidades serranas e áreas de encosta. O Estado do Rio de Janeiro tem um histórico recorrente de desastres desse tipo, com desalojados e óbitos. O projeto investiga:</p>
  <ul>
    <li>Quais municípios têm mais chuva e mais deslizamentos? Quais são os mais críticos?</li>
    <li>Há meses e períodos sazonais mais perigosos?</li>
    <li>A chuva intensa aumenta os deslizamentos? Há municípios fora do padrão?</li>
  </ul>
  <p><strong>Decisão apoiada:</strong> onde priorizar obras e defesa civil e quando operar em alerta.</p>
</section>

<section id="base">
  <h2>A base de dados</h2>
  <p><code>simulacao_chuvas_deslizamentos_rj.csv</code>: <strong>{br(len(df), 0)} linhas × 14 colunas</strong>, 8 municípios × 120 meses (janeiro/2015 a dezembro/2024), em 5 regiões do estado. São <strong>dados simulados</strong> fornecidos pelo professor (repositório Dados-Simulados-G2).</p>
  <div class="aviso"><strong>Limitações documentadas:</strong> a coluna <code>populacao</code> muda a cada mês no mesmo município (de ~120 mil a ~6,5 milhões), por isso não foram calculadas taxas por habitante; <code>desalojados</code> é quase proporcional aos deslizamentos; e <code>nivel_risco</code> não é função exata da chuva.</div>
</section>

<section id="kpis">
  <h2>Indicadores-chave</h2>
  <div class="grid">
    <div class="card kpi"><small>Volume total de chuva</small><strong>{br(k['volume_chuva'], 0)} mm</strong><span>soma de todos os registros</span></div>
    <div class="card kpi"><small>Média de chuva</small><strong>{br(k['media_chuva'], 1)} mm/mês</strong><span>por município</span></div>
    <div class="card kpi"><small>Total de deslizamentos</small><strong>{br(k['total_deslizamentos'], 0)}</strong><span>{br(k['obitos'], 0)} óbitos no período</span></div>
    <div class="card kpi"><small>Município mais crítico</small><strong>{k['mun_critico'][0]}</strong><span>{br(k['mun_critico'][1], 0)} deslizamentos</span></div>
    <div class="card kpi"><small>Total de desalojados</small><strong>{br(k['desalojados'], 0)}</strong><span>pessoas</span></div>
    <div class="card kpi"><small>Correlação chuva × deslizamentos</small><strong>r = {br(k['corr'], 2)}</strong><span>muito forte</span></div>
  </div>
</section>

<section id="graficos">
  <h2>Principais visualizações</h2>
  <div class="duas">
    <figure><img src="imagens/02_linha_deslizamentos.png" alt="Deslizamentos por mês por região"><figcaption>Deslizamentos por mês: ciclo anual repetido e a região Serrana muito acima das demais.</figcaption></figure>
    <figure><img src="imagens/08_sazonalidade_chuva_deslizamentos.png" alt="Sazonalidade"><figcaption>Sazonalidade: de dezembro a março chove o dobro e há 2,8× mais deslizamentos por município.</figcaption></figure>
    <figure><img src="imagens/05_dispersao_chuva_deslizamentos.png" alt="Dispersão chuva x deslizamentos"><figcaption>Chuva × deslizamentos (r = {br(c['r'], 2)}): a Serrana fica acima da reta.</figcaption></figure>
    <figure><img src="imagens/03_barras_deslizamentos_municipio.png" alt="Deslizamentos por município"><figcaption>Três municípios serranos concentram {br(pct_top3, 0)}% dos deslizamentos.</figcaption></figure>
    <figure><img src="imagens/07_heatmap_deslizamentos_municipio_mes.png" alt="Heatmap município por mês"><figcaption>Heatmap município × mês: o verão serrano se destaca.</figcaption></figure>
    <figure><img src="imagens/12_municipios_fora_do_padrao.png" alt="Municípios fora do padrão"><figcaption>Municípios fora do padrão: só os serranos têm mais deslizamentos do que a chuva explica.</figcaption></figure>
  </div>
</section>

<section id="achados">
  <h2>Resultados e conclusão executiva</h2>
  <ul>
    <li><strong>A chuva é o principal gatilho:</strong> r = {br(c['r'], 2)} e cerca de +{br(reta[0] * 100, 1)} deslizamentos a cada 100 mm; efeito imediato (r = {br(lag.iloc[0], 2)} no mesmo mês e {br(lag.iloc[1], 2)} com 1 mês de defasagem).</li>
    <li><strong>Forte sazonalidade:</strong> dezembro a março têm {br(ch['chuva_media_mm'], 0)} mm de chuva média (contra {br(rs['chuva_media_mm'], 0)} mm) e concentram {br(ch['pct_das_ocorrencias'], 0)}% dos deslizamentos e {br(pct_obitos, 0)}% dos óbitos.</li>
    <li><strong>Região Serrana é a mais vulnerável:</strong> {", ".join(top3)} somam {br(pct_top3, 0)}% dos deslizamentos e têm mais ocorrências do que a chuva explicaria.</li>
    <li><strong>Regra de alerta:</strong> chuva ≥ 200 mm com solo saturado (≥ 0,8) são {br(al['pct_registros'], 0)}% dos meses, mas {br(al['pct_ocorrencias'], 0)}% dos deslizamentos.</li>
  </ul>
  <p><strong>Mensagem ao gestor:</strong> os deslizamentos seguem a chuva e o lugar. Concentrar obras e defesa civil nos três municípios serranos, operar em alerta de dezembro a março e acionar o alarme por chuva forte com solo saturado.</p>
</section>

<section id="tecnologias">
  <h2>Tecnologias e funcionalidades</h2>
  <div class="tags"><span>Python</span><span>Pandas</span><span>NumPy</span><span>Matplotlib</span><span>Seaborn</span><span>Streamlit</span><span>Plotly</span><span>SciPy</span><span>SQLAlchemy</span><span>SQLite</span><span>Requests</span><span>GitHub</span><span>GitHub Pages</span></div>
  <table>
    <tr><th>Funcionalidade</th><th>Como foi feita</th></tr>
    <tr><td>Consumo de API + múltiplas fontes</td><td><code>requests</code> na API Open-Meteo (chuva observada) comparada à chuva da base; resultado gravado no banco.</td></tr>
    <tr><td>Persistência em banco + modelagem relacional</td><td>SQLAlchemy + SQLite com 4 tabelas (regiões, municípios, registros, chuva_api) e uma view; consultas SQL no dashboard.</td></tr>
    <tr><td>Mapa interativo</td><td>Plotly: bolhas por município (deslizamentos e % crítico).</td></tr>
    <tr><td>Correlação estatística</td><td>Pearson, Spearman, ANOVA, Mann-Whitney e teste t.</td></tr>
    <tr><td>Séries temporais avançadas</td><td>Médias móveis, sazonalidade, correlação defasada e resíduos do modelo de chuva.</td></tr>
    <tr><td>Filtros, KPIs e interatividade</td><td>Ano, mês, município, região e nível de risco recalculam KPIs, gráficos e textos; upload de CSV; tabela dinâmica; download dos dados.</td></tr>
  </table>
</section>

<section id="estrutura">
  <h2>Estrutura do projeto</h2>
<pre>projeto-chuvas-deslizamentos-rj/
├── app.py                  # dashboard Streamlit
├── utils.py                # dados, KPIs, estatística, API e gráficos
├── interpretacao.py        # textos de interpretação e conclusão
├── requirements.txt
├── README.md
├── index.html              # esta página (GitHub Pages)
├── dados/                  # CSV original
├── database/               # SQLAlchemy + SQLite (db.py, chuvas.db)
├── notebooks/              # analise_chuvas_deslizamentos.ipynb
└── imagens/                # gráficos exportados do notebook</pre>
</section>

<section id="executar">
  <h2>Como executar</h2>
<pre>git clone https://github.com/SEU_USUARIO/projeto-chuvas-deslizamentos-rj.git
cd projeto-chuvas-deslizamentos-rj
pip install -r requirements.txt
streamlit run app.py</pre>
</section>
</main>

<footer>Lucas Queiroz Paes Leme · Linguagem de Programação — Análise e Visualização de Dados com Python · Prof. Alexandre Louzada · Outubro de 2026<br>Projeto acadêmico com dados simulados.</footer>

<script>
  // ► Edite só estas 3 linhas depois de publicar:
  const GITHUB_USUARIO = "SEU_USUARIO";
  const REPOSITORIO    = "projeto-chuvas-deslizamentos-rj";
  const URL_STREAMLIT  = "https://SEU-APP.streamlit.app";

  const repo = `https://github.com/${{GITHUB_USUARIO}}/${{REPOSITORIO}}`;
  document.getElementById("lnk-repo").href = repo;
  document.getElementById("lnk-nb").href   = `${{repo}}/blob/main/notebooks/analise_chuvas_deslizamentos.ipynb`;
  document.getElementById("lnk-dash").href = URL_STREAMLIT;
</script>
</body>
</html>
"""
open("index.html", "w", encoding="utf-8").write(HTML)
print("index.html gerado:", len(HTML), "bytes")
