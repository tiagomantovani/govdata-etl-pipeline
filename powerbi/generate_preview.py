# powerbi/generate_preview.py
"""Gera previews estáticos dos visuais do Power BI a partir do PostgreSQL.

Uso:
    python -m powerbi.generate_preview
Saída:
    powerbi/preview_ideb_linhas.png
    powerbi/preview_pib_uf.png
"""
import os

import matplotlib.pyplot as plt
import pandas as pd
import psycopg2
from dotenv import load_dotenv

load_dotenv()

HOST = "localhost"
if os.getenv("POSTGRES_HOST") == "postgres":
    # tenta resolver automaticamente (igual ao loader)
    import socket
    try:
        socket.create_connection(("postgres", 5432), timeout=2).close()
        HOST = "postgres"
    except OSError:
        HOST = "localhost"

conn = psycopg2.connect(
    host=HOST,
    port=os.getenv("POSTGRES_PORT", "5432"),
    dbname=os.getenv("POSTGRES_DB", "govdata"),
    user=os.getenv("POSTGRES_USER", "postgres"),
    password=os.getenv("POSTGRES_PASSWORD", "suasenha"),
)

# 1) IDEB médio por região/ano — linhas
df_ideb = pd.read_sql("SELECT * FROM vw_ideb_medio_regiao_ano ORDER BY ano", conn)
pivot = df_ideb.pivot(index="ano", columns="nome_regiao", values="ideb_medio")

plt.figure(figsize=(10, 6))
for col in pivot.columns:
    plt.plot(pivot.index, pivot[col], marker="o", label=col)
plt.title("IDEB médio (rede pública) por região — 2005–2025")
plt.xlabel("Ano")
plt.ylabel("IDEB médio")
plt.legend(title="Região")
plt.grid(True, alpha=0.3)
plt.tight_layout()
out1 = os.path.join(os.path.dirname(__file__), "preview_ideb_linhas.png")
plt.savefig(out1, dpi=150)
plt.close()
print(f"✅ Preview IDEB salvo em: {out1} ({len(df_ideb)} linhas)")

# 2) PIB por UF (último ano disponível) — barras
df_pib = pd.read_sql(
    """
    SELECT uf, nome_uf, valor FROM vw_pib_por_uf_ano
    WHERE variavel LIKE 'Produto Interno Bruto%' AND ano = (SELECT MAX(ano) FROM vw_pib_por_uf_ano)
    ORDER BY valor DESC
    """,
    conn,
)
plt.figure(figsize=(12, 6))
plt.bar(df_pib["uf"], df_pib["valor"] / 1e6)
plt.title(f"PIB por UF — {df_pib['uf'].iloc[0] if False else ''} (último ano, R$ bilhões)")
# título com ano real
ano_pib = int(pd.read_sql("SELECT MAX(ano) AS ano FROM vw_pib_por_uf_ano", conn)["ano"].iloc[0])
plt.title(f"PIB por UF — {ano_pib} (R$ bilhões)")
plt.xlabel("UF")
plt.ylabel("PIB (R$ bilhões)")
plt.xticks(rotation=45)
plt.tight_layout()
out2 = os.path.join(os.path.dirname(__file__), "preview_pib_uf.png")
plt.savefig(out2, dpi=150)
plt.close()
print(f"✅ Preview PIB salvo em: {out2} ({len(df_pib)} UFs)")

conn.close()
print("Previews gerados com sucesso.")
