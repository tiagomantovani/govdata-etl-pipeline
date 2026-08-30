# Power BI — GovData

Esta pasta contém a camada semântica e a especificação do relatório.

| Arquivo | Descrição |
|---|---|
| `DATA_MODEL.md` | Tabelas, chaves e relacionamentos (star schema) |
| `MEASURES.dax` | Medidas DAX (copiar para o modelo) |
| `REPORT_SPEC.md` | Layout das 3 páginas, visuais e interações |
| `generate_preview.py` | Gera `preview_*.png` a partir do PostgreSQL (sem precisar do Power BI Desktop) |
| `preview_ideb_linhas.png` | Prévia: IDEB médio por região 2005–2025 |
| `preview_pib_uf.png` | Prévia: PIB por UF (último ano) |

## Como reproduzir o .pbix

1. Power BI Desktop → Obter Dados → PostgreSQL (`localhost:5432`, `govdata`).
2. Importe `dim_estado` + 3 fatos + execute `sql/views.sql` e importe as 5 views.
3. Crie as medidas de `MEASURES.dax` e os visuais de `REPORT_SPEC.md`.

O `.pbix` é binário e fica fora do git (ver `.gitignore`); versione via formato PBIP (`*.pbir`) se preferir.