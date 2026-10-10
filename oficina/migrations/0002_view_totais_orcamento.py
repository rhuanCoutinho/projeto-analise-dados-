from django.db import migrations


VIEW_SQL = """
CREATE VIEW vw_orcamento_totais AS
SELECT
  o.id AS orcamento_id,
  COALESCE(SUM(i.quantidade * i.preco_unitario), 0) AS subtotal,
  COALESCE(SUM(i.quantidade * i.custo_unitario), 0) AS custo_total,
  o.desconto_percentual AS desconto_percentual,
  ROUND(COALESCE(SUM(i.quantidade * i.preco_unitario), 0) * o.desconto_percentual / 100.0, 2) AS valor_desconto,
  ROUND(COALESCE(SUM(i.quantidade * i.preco_unitario), 0) * (1 - o.desconto_percentual / 100.0), 2) AS total_final
FROM oficina_orcamento o
LEFT JOIN oficina_itemorcamento i ON i.orcamento_id = o.id
GROUP BY o.id, o.desconto_percentual
"""


class Migration(migrations.Migration):
    dependencies = [("oficina", "0001_initial")]
    operations = [migrations.RunSQL(VIEW_SQL, "DROP VIEW vw_orcamento_totais")]
