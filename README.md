# 🌧️ Chuvas e Deslizamentos no Estado do Rio de Janeiro (2015–2024)

Projeto da **Avaliação G1** — **Linguagem de Programação**: Análise e Visualização de Dados com Python.

| | |
|---|---|
| **Aluno** | Lucas Queiroz Paes Leme |
| **Disciplina** | Linguagem de Programação |
| **Professor** | Alexandre Louzada |
| **Tema** | 2 — Chuvas e Deslizamentos no Estado do Rio de Janeiro |

| Entrega | Link |
|---|---|
| Repositório (código-fonte) | `https://github.com/SEU_USUARIO/projeto-chuvas-deslizamentos-rj` |
| Página do projeto (GitHub Pages) | `https://SEU_USUARIO.github.io/projeto-chuvas-deslizamentos-rj/` |
| Dashboard (Streamlit Community Cloud) | `https://SEU-APP.streamlit.app` |
| Notebook | [`notebooks/analise_chuvas_deslizamentos.ipynb`](notebooks/analise_chuvas_deslizamentos.ipynb) |

## 1. O problema

Chuvas intensas causam enchentes, alagamentos e deslizamentos de terra, principalmente em cidades serranas e áreas de encosta. O projeto analisa chuva, deslizamentos, desalojados e óbitos em 8 municípios do Rio de Janeiro e responde:

1. Quais municípios têm mais chuva e mais deslizamentos? Quais são os mais críticos?
2. Existem meses e períodos sazonais mais perigosos?
3. A chuva intensa aumenta os deslizamentos? Quão forte é a relação?
4. Há municípios com comportamento fora do padrão?

**Decisão apoiada:** onde priorizar obras e defesa civil e quando operar em alerta.

## 2. Base de dados

`dados/simulacao_chuvas_deslizamentos_rj.csv` — 960 linhas × 14 colunas (8 municípios × 120 meses, jan/2015 a dez/2024), **dados simulados** fornecidos pelo professor (Dados-Simulados-G2, Tema 2).

Colunas: `ano, mes, data, municipio, regiao_rj, populacao, chuva_mm, temperatura_media, ocorrencias_deslizamento, desalojados, obitos, nivel_risco, indice_solo, umidade`.

**Limitações identificadas no tratamento:** a `populacao` muda a cada mês no mesmo município (de ~120 mil a ~6,5 milhões), então não foram calculadas taxas por habitante; `desalojados` é quase proporcional aos deslizamentos (r > 0,99); `nivel_risco` não é função exata da chuva. Detalhes no notebook.

## 3. Requisitos da avaliação × o que foi feito

**Tecnologias obrigatórias:** Python, Pandas, Matplotlib, Seaborn, Streamlit e GitHub ✔️

**Funcionalidades intermediárias (mínimo 2):**
- Filtros múltiplos no Streamlit (ano, mês, município, região, nível de risco) ✔️
- KPIs dinâmicos (recalculados a cada filtro) ✔️
- Gráficos interativos (Plotly) ✔️
- Análise temporal (médias móveis, heatmaps ano × mês, sazonalidade) ✔️
- Dashboard organizado em seções (7 abas) ✔️
- Visualizações comparativas (município, região, estação do ano) ✔️
- Upload de arquivos (CSV no mesmo formato) ✔️
- Integração entre tabelas (JOINs no SQLite) ✔️
- Análise geográfica (mapa dos municípios) ✔️

**Funcionalidades avançadas (mínimo 2):**
- **Consumo de API:** `requests` na API Open-Meteo (chuva observada) comparada à chuva da base ✔️
- **Persistência em banco:** SQLAlchemy + SQLite (`database/chuvas.db`) ✔️
- **Modelagem relacional:** `regioes`, `municipios`, `registros`, `chuva_api` e a view `vw_registros` ✔️
- **Mapa interativo:** Plotly (bolhas por município) ✔️
- **Séries temporais avançadas:** correlação defasada, sazonalidade e resíduos do modelo de chuva ✔️
- **Correlação estatística:** Pearson, Spearman, ANOVA, Mann-Whitney e teste t ✔️
- **Integração de múltiplas fontes:** CSV + banco + API ✔️

**Dashboard (itens obrigatórios):** título, descrição do problema, filtros, KPIs, tabelas, gráficos, interpretação textual e conclusão executiva ✔️

**KPIs pedidos no tema:** volume total de chuva, média de chuva, total de deslizamentos, município mais crítico, total de desalojados e correlação chuva × deslizamentos ✔️

## 4. Estrutura do projeto

```
projeto-chuvas-deslizamentos-rj/
├── app.py                  # dashboard Streamlit
├── utils.py                # leitura, limpeza, KPIs, estatística, API e gráficos
├── interpretacao.py        # textos de interpretação e conclusão executiva
├── build_index.py          # gera o index.html com os números da base
├── requirements.txt
├── README.md
├── index.html              # página do projeto (GitHub Pages)
├── dados/                  # CSV original
├── database/               # db.py (SQLAlchemy) + chuvas.db (SQLite)
├── notebooks/              # analise_chuvas_deslizamentos.ipynb
└── imagens/                # gráficos exportados pelo notebook
```

## 5. Como executar

```bash
git clone https://github.com/SEU_USUARIO/projeto-chuvas-deslizamentos-rj.git
cd projeto-chuvas-deslizamentos-rj
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

O banco `database/chuvas.db` é criado automaticamente a partir do CSV se não existir.

## 6. Publicação

1. **GitHub:** crie o repositório `projeto-chuvas-deslizamentos-rj` e envie todos os arquivos da pasta (inclusive `dados/`, `database/` e `imagens/`).
2. **GitHub Pages:** em *Settings → Pages*, escolha *Deploy from a branch* → `main` → `/ (root)`. A página (`index.html`) fica em `https://SEU_USUARIO.github.io/projeto-chuvas-deslizamentos-rj/`.
3. **Streamlit Community Cloud:** em share.streamlit.io, *Create app* → selecione o repositório, branch `main` e arquivo principal `app.py`.
4. Edite as 3 constantes no final do `index.html` (`GITHUB_USUARIO`, `REPOSITORIO`, `URL_STREAMLIT`) e os links deste README.

## 7. Principais resultados

- **A chuva é o principal gatilho:** correlação de 0,82 com os deslizamentos (cerca de +5,9 deslizamentos a cada 100 mm), com efeito imediato.
- **Forte sazonalidade:** de dezembro a março chove 214 mm em média (contra 98 mm no resto do ano) e ocorrem 58% dos deslizamentos e 66% dos óbitos.
- **Região Serrana é a mais vulnerável:** Teresópolis, Petrópolis e Nova Friburgo concentram 57% dos deslizamentos e têm mais ocorrências do que a chuva explicaria.
- **Regra de alerta:** chuva ≥ 200 mm com solo saturado (≥ 0,8) são 20% dos meses, mas 47% dos deslizamentos.

**Decisões sugeridas:** priorizar obras e defesa civil na Serrana; operar em alerta de dezembro a março; acionar o alarme por chuva forte com solo saturado.
