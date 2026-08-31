# streamlit_app.py — GovData Dashboard (Streamlit Cloud-ready)
import os
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="GovData — IBGE + INEP", layout="wide", page_icon="📊")

ASSETS = Path("assets")
DB_SECRETS = st.secrets.get("postgres", {}) if hasattr(st, "secrets") else {}

@st.cache_data(show_spinner=False)
def load_from_db_or_assets():
    """Tenta PostgreSQL (secrets/env), senão lê os CSVs de assets/."""
    # 1) tenta via secrets do Streamlit Cloud ou env local
    host = DB_SECRETS.get("host") or os.getenv("POSTGRES_HOST", "postgres")
    # fallback para localhost quando fora do Docker (igual ao loader)
    if host == "postgres":
        import socket
        try:
            socket.create_connection(("postgres", 5432), timeout=1).close()
        except OSError:
            host = "localhost"
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=host,
            port=DB_SECRETS.get("port") or os.getenv("POSTGRES_PORT", "5432"),
            dbname=DB_SECRETS.get("dbname") or os.getenv("POSTGRES_DB", "govdata"),
            user=DB_SECRETS.get("user") or os.getenv("POSTGRES_USER", "postgres"),
            password=DB_SECRETS.get("password") or os.getenv("POSTGRES_PASSWORD", "suasenha"),
            connect_timeout=3,
        )
        dfs = {
            "dim_estado": pd.read_sql("SELECT * FROM dim_estado ORDER BY id_estado", conn),
            "ideb_medio": pd.read_sql("SELECT * FROM vw_ideb_medio_regiao_ano ORDER BY ano", conn),
            "pib": pd.read_sql("SELECT * FROM vw_pib_por_uf_ano WHERE variavel LIKE 'Produto Interno Bruto%' ORDER BY valor DESC", conn),
            "ranking": pd.read_sql("SELECT * FROM vw_ideb_ranking_municipios WHERE ano=2025 AND rede='Pública' ORDER BY ideb DESC LIMIT 100", conn),
            "fato_ideb": pd.read_sql("SELECT codigo_municipio, nome_municipio, uf, rede, ano, ideb FROM fato_ideb ORDER BY ano DESC, ideb DESC LIMIT 5000", conn),
        }
        conn.close()
        dfs["source"] = f"PostgreSQL ({host})"
        return dfs
    except Exception as e:
        # 2) fallback para CSVs commitados (Streamlit Cloud sem banco)
        base = ASSETS if ASSETS.exists() else Path("assets")
        if not (base / "dim_estado.csv").exists():
            st.error(f"Sem banco e sem assets/ — {e}")
            st.stop()
        dfs = {
            "dim_estado": pd.read_csv(base / "dim_estado.csv"),
            "ideb_medio": pd.read_csv(base / "ideb_medio_regiao_ano.csv"),
            "pib": pd.read_csv(base / "pib_por_uf_ano.csv"),
            "ranking": pd.read_csv(base / "ideb_ranking.csv"),
            "fato_ideb": pd.read_csv(base / "fato_ideb.csv", usecols=["codigo_municipio","nome_municipio","uf","rede","ano","ideb"]),
        }
        # pib via view já filtrado; se veio do CSV genérico, filtra aqui
        if "variavel" in dfs["pib"].columns:
            dfs["pib"] = dfs["pib"][dfs["pib"]["variavel"].str.contains("Produto Interno", na=False)]
        dfs["source"] = "assets/*.csv (fallback estático)"
        return dfs

data = load_from_db_or_assets()

st.sidebar.title("GovData")
st.sidebar.caption(f"Fonte: {data['source']}")
st.sidebar.markdown("**IBGE** (SIDRA 4714/5938) + **INEP** (IDEB por município)")
st.sidebar.markdown("[GitHub](https://github.com/tiagomantovani/govdata-etl-pipeline) · [Airflow](http://localhost:8080) (local)")
st.sidebar.divider()
page = st.sidebar.radio("Navegação", ["Dashboard", "Explorer", "API Docs"], index=0)

if page == "Dashboard":
    st.title("📊 GovData — Dashboard")
    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    try:
        total_pop = pd.read_csv(ASSETS / "fato_populacao.csv")["populacao"].sum() if (ASSETS / "fato_populacao.csv").exists() else 0
    except Exception:
        total_pop = 0
    c1.metric("Estados", len(data["dim_estado"]))
    c2.metric("Municípios (IDEB)", f"{len(data['fato_ideb']):,}".replace(",", "."))
    c3.metric("IDEB médio 2025 (pública)", f"{data['ideb_medio'][data['ideb_medio']['ano']==2025]['ideb_medio'].mean():.2f}" if not data["ideb_medio"].empty else "—")
    c4.metric("PIB total (R$ bi)", f"{data['pib']['valor'].sum()/1e6:.0f}" if not data["pib"].empty else "—")

    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("IDEB médio por região — 2005–2025 (rede pública)")
        pivot = data["ideb_medio"].pivot(index="ano", columns="nome_regiao", values="ideb_medio")
        st.line_chart(pivot, height=350)
    with col2:
        st.subheader("PIB por UF — último ano")
        pib_uf = data["pib"].groupby("uf", as_index=False)["valor"].sum().sort_values("valor", ascending=False)
        st.bar_chart(pib_uf.set_index("uf")["valor"] / 1e6, height=350)
        st.caption("Em R$ bilhões (Mil Reais → /1e6)")

    st.subheader("Top 10 municípios — IDEB 2025 (rede pública)")
    st.dataframe(data["ranking"].head(10)[["posicao","nome_municipio","uf","ideb"]], use_container_width=True, hide_index=True)

elif page == "Explorer":
    st.title("🔍 Explorer")
    df = data["fato_ideb"].copy()
    c1, c2, c3 = st.columns(3)
    ufs = sorted(df["uf"].dropna().unique().tolist())
    sel_uf = c1.multiselect("UF", ufs, default=ufs[:3] if len(ufs) > 3 else ufs)
    anos = sorted(df["ano"].dropna().unique().tolist())
    sel_ano = c2.select_slider("Ano", options=anos, value=anos[-1] if anos else 2025)
    redes = sorted(df["rede"].dropna().unique().tolist())
    sel_rede = c3.selectbox("Rede", ["Todas"] + redes, index=0)

    q = df.copy()
    if sel_uf:
        q = q[q["uf"].isin(sel_uf)]
    if sel_ano:
        q = q[q["ano"] == sel_ano]
    if sel_rede != "Todas":
        q = q[q["rede"] == sel_rede]
    q = q.sort_values("ideb", ascending=False, na_position="last")

    st.caption(f"{len(q):,} registros filtrados".replace(",", "."))
    st.dataframe(q.head(1000), use_container_width=True, hide_index=True)
    st.download_button("⬇️ Baixar CSV (filtro atual)", q.to_csv(index=False).encode("utf-8"), file_name="govdata_filtrado.csv", mime="text/csv")

else:  # API Docs
    st.title("🔌 API Docs")
    st.markdown("""
    Os dados do pipeline estão em **PostgreSQL** (`govdata`) e espelhados em `assets/*.csv` para a demo estática.

    **PostgreSQL (local ou Supabase/Neon):**
    ```python
    import psycopg2
    conn = psycopg2.connect(host=\"localhost\", dbname=\"govdata\", user=\"postgres\", password=\"suasenha\")
    df = pd.read_sql(\"SELECT * FROM vw_ideb_medio_regiao_ano\", conn)
    ```

    **CSV estático (Streamlit Cloud fallback):**
    ```python
    df = pd.read_csv(\"https://raw.githubusercontent.com/tiagomantovani/govdata-etl-pipeline/main/assets/ideb_medio_regiao_ano.csv\")
    ```

    **Views disponíveis (`sql/views.sql`):**
    - `vw_ideb_medio_regiao_ano` — média por região/ano
    - `vw_ideb_ranking_municipios` — ranking com `RANK()`
    - `vw_pib_por_uf_ano`, `vw_populacao_por_uf_ano`, `vw_painel_uf_ano`
    """)
    st.divider()
    st.subheader("Esquema")
    st.code("dim_estado 1—* fato_ideb/fato_pib/fato_populacao  (FK id_estado)", language="text")
    if st.checkbox("Mostrar `sql/views.sql`"):
        st.code(Path("sql/views.sql").read_text(encoding="utf-8"), language="sql")
