# Painel SidCar — Funilaria e Pintura

Dashboard estático simples para acompanhar faturamento, serviços e veículos atendidos pela SidCar. É possível filtrar por período, categoria, marca e modelo.

## Abrir e usar

1. Abra `public/index.html` no navegador. O painel inicia com 200 ordens fictícias distribuídas ao longo de 12 meses.
2. Use os campos de data, categoria, marca e modelo para filtrar os resultados.
3. Abra **Registrar nova entrada na oficina** para adicionar marca, modelo e detalhes do serviço. A entrada fica na lista enquanto a página estiver aberta; exporte o CSV para guardar uma cópia.
4. Pesquise e ordene a tabela, limpe os filtros ou exporte os registros exibidos para CSV.
5. Selecione **Importar CSV** para carregar uma base própria. O arquivo é processado localmente no navegador.
6. Use o botão no cabeçalho para alternar entre tema claro e escuro. A preferência fica salva no navegador.

Chart.js 4.4.7 e Papa Parse 5.4.1 são carregados por CDN e exigem acesso à internet. A demonstração inicial já está incorporada em `script.js`, então não depende de `fetch` nem de servidor local para abrir o HTML.

## Base de exemplo e importação

O arquivo [dados-exemplo.csv](public/dados-exemplo.csv) contém dados demonstrativos fictícios, não resultados reais da SidCar. Inclui exemplos de marcas e modelos. Cada linha descreve um serviço em uma ordem de serviço.

| Coluna | Significado |
| --- | --- |
| `id_os` | Identificador da ordem de serviço. Se um ID aparecer mais de uma vez, as linhas são mantidas e o cartão conta IDs únicos. |
| `data` | Data do serviço, no formato `AAAA-MM-DD`. |
| `marca` | Marca do veículo atendido, por exemplo Chevrolet ou Toyota. |
| `modelo` | Modelo do veículo, por exemplo Onix ou Corolla. |
| `servico` | Serviço executado, como reparo de para-choque ou polimento técnico. |
| `categoria` | Área do serviço: Funilaria, Pintura ou Estética automotiva. |
| `quantidade` | Quantidade de itens ou serviços descritos na linha. |
| `preco_unitario` | Valor por item ou serviço, sem símbolo de moeda. |

Para importar, use cabeçalhos `id_os`, `data`, `servico`, `categoria`, `quantidade` e `preco_unitario`. As colunas `marca` e `modelo` são opcionais para manter compatibilidade com planilhas antigas; quando ausentes, aparecem como **Não informada** ou **Não informado**. Também são reconhecidos `montadora`, `marca_veiculo`, `marca_do_veiculo` e `fabricante` para `marca`; `modelo_veiculo`, `modelo_do_veiculo` e `modelo_carro` para `modelo`; `id_venda` para `id_os`; e `produto` para `servico`. Colunas adicionais são ignoradas.

Linhas com campos obrigatórios ausentes, datas inválidas, quantidade não inteira ou valores negativos/inválidos são descartadas e contabilizadas. Quantidade e preço iguais a zero são aceitos. O arquivo original [vendas_hamburgueria.csv](vendas_hamburgueria.csv), se presente no projeto, é preservado; ele representa outro negócio e não serve como base real da oficina.

## Indicadores e gráficos

- **Faturamento por linha:** `quantidade × preco_unitario`.
- **Faturamento total:** soma dos faturamentos das linhas filtradas.
- **Ordens de serviço:** quantidade de `id_os` únicos nas linhas filtradas.
- **Serviços realizados:** soma das quantidades nas linhas filtradas.
- **Ticket médio por OS:** faturamento total dividido pelas OS únicas. Sem OS, o resultado é `R$ 0,00`.
- Os gráficos apresentam a evolução mensal do faturamento e o faturamento por categoria, sempre com os mesmos filtros da tabela e dos indicadores.
- Marca e modelo ficam visíveis na tabela e podem ser pesquisados, ordenados, filtrados e exportados.

Os valores são exibidos em reais, no padrão brasileiro. A base importada permanece no navegador e não é enviada a um servidor.

## Publicar no Render pelo GitHub

Envie o projeto para um repositório GitHub e crie no Render um serviço **Static Site**. Configure:

| Configuração | Valor |
| --- | --- |
| Tipo de serviço | **Static Site** |
| Branch | A branch que contém o projeto, por exemplo `main` |
| Root Directory | Deixe vazio |
| Build Command | `echo "Site pronto"` |
| Publish Directory | `public` |

O Render publica os arquivos da pasta `public`; não há backend nem etapa de compilação.

## Como acessar
link do site publicado: https://projeto-analise-dados-5tgu.onrender.com/ 