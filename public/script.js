/* Dados de exemplo de uma oficina; substitua-os pelos dados reais ao importar um CSV. */
const servicosDemo = [
  { servico: "Reparo de para-choque", categoria: "Funilaria", preco: 850 },
  { servico: "Alinhamento de lateral", categoria: "Funilaria", preco: 1250 },
  { servico: "Pintura de para-choque", categoria: "Pintura", preco: 1100 },
  { servico: "Pintura de porta", categoria: "Pintura", preco: 1450 },
  { servico: "Pintura completa", categoria: "Pintura", preco: 4800 },
  { servico: "Polimento técnico", categoria: "Estética automotiva", preco: 650 },
  { servico: "Martelinho de ouro", categoria: "Funilaria", preco: 580 },
  { servico: "Retoque de pintura", categoria: "Pintura", preco: 420 },
  { servico: "Vitrificação de pintura", categoria: "Estética automotiva", preco: 1300 }
];
const veiculosDemo = [
  { marca: "Chevrolet", modelos: ["Onix", "Prisma", "Tracker", "S10"] },
  { marca: "Fiat", modelos: ["Argo", "Mobi", "Toro", "Cronos"] },
  { marca: "Honda", modelos: ["Civic", "Fit", "City", "HR-V"] },
  { marca: "Toyota", modelos: ["Corolla", "Etios", "Hilux", "Yaris"] },
  { marca: "Volkswagen", modelos: ["Gol", "Polo", "T-Cross", "Saveiro"] }
];
const colunasExportacao = ["id_os", "data", "marca", "modelo", "servico", "categoria", "quantidade", "preco_unitario"];
const formatadorMoeda = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const formatadorNumero = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 });
const meses = new Intl.DateTimeFormat("pt-BR", { month: "short", year: "numeric", timeZone: "UTC" });

let vendas = [];
let chartInstances = {};
let sortColumn = "data";
let sortDirection = "desc";

const elementos = {
  dateFrom: document.querySelector("#date-from"),
  dateTo: document.querySelector("#date-to"),
  category: document.querySelector("#category-filter"),
  brand: document.querySelector("#brand-filter"),
  model: document.querySelector("#model-filter"),
  search: document.querySelector("#table-search"),
  tableBody: document.querySelector("#sales-table-body"),
  emptyState: document.querySelector("#empty-state"),
  recordCount: document.querySelector("#record-count"),
  tableSummary: document.querySelector("#table-summary"),
  quality: document.querySelector("#quality-message"),
  note: document.querySelector("#data-note"),
  entryForm: document.querySelector("#entry-form"),
  entryBrand: document.querySelector("#entry-brand"),
  entryModel: document.querySelector("#entry-model"),
  entryDate: document.querySelector("#entry-date"),
  entryService: document.querySelector("#entry-service"),
  entryCategory: document.querySelector("#entry-category"),
  entryQuantity: document.querySelector("#entry-quantity"),
  entryPrice: document.querySelector("#entry-price"),
  entryMessage: document.querySelector("#entry-message")
};

function criarDadosDemonstrativos() {
  // A mesma regra gera as 200 linhas de dados-exemplo.csv sem buscar arquivo local.
  return Array.from({ length: 200 }, (_, indice) => {
    const id = indice + 1;
    const mes = ((id - 1) % 12) + 1;
    const dia = 1 + ((id * 7) % 28);
    const servicoIndex = (id * 5 + Math.floor(id / 7)) % servicosDemo.length;
    const marcaIndex = (id * 3 + Math.floor(id / 13)) % veiculosDemo.length;
    const veiculo = veiculosDemo[marcaIndex];
    const modeloIndex = (id * 5 + Math.floor(id / 9)) % veiculo.modelos.length;
    const quantidade = 1 + ((id * 7) % 4);
    const servico = servicosDemo[servicoIndex];
    return {
      id_os: `OS-${String(id).padStart(4, "0")}`,
      data: `2025-${String(mes).padStart(2, "0")}-${String(dia).padStart(2, "0")}`,
      marca: veiculo.marca,
      modelo: veiculo.modelos[modeloIndex],
      servico: servico.servico,
      categoria: servico.categoria,
      quantidade,
      preco_unitario: servico.preco,
      faturamento: quantidade * servico.preco
    };
  });
}

function normalizarCabecalho(valor) {
  return String(valor ?? "")
    .replace(/^\uFEFF/, "")
    .trim()
    .toLocaleLowerCase("pt-BR")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_|_$/g, "");
}

function colunaCanonica(valor) {
  const coluna = normalizarCabecalho(valor);
  const apelidos = {
    id_venda: "id_os",
    id_ordem_servico: "id_os",
    numero_os: "id_os",
    ordem_servico: "id_os",
    ordem_de_servico: "id_os",
    produto: "servico",
    nome_servico: "servico",
    montadora: "marca",
    marca_veiculo: "marca",
    marca_do_veiculo: "marca",
    fabricante: "marca",
    modelo_veiculo: "modelo",
    modelo_do_veiculo: "modelo",
    modelo_carro: "modelo"
  };
  return apelidos[coluna] || coluna;
}

function converterNumero(valor) {
  if (valor === null || valor === undefined || String(valor).trim() === "") return null;
  let texto = String(valor).trim().replace(/\s/g, "").replace(/^R\$/i, "");
  if (texto.includes(",") && texto.includes(".")) {
    // Quando os dois separadores aparecem, o último é interpretado como decimal.
    texto = texto.lastIndexOf(",") > texto.lastIndexOf(".")
      ? texto.replace(/\./g, "").replace(",", ".")
      : texto.replace(/,/g, "");
  } else if (texto.includes(",")) {
    texto = texto.replace(",", ".");
  }
  const numero = Number(texto);
  return Number.isFinite(numero) ? numero : NaN;
}

function dataIsoValida(valor) {
  const texto = String(valor ?? "").trim();
  const partes = /^(\d{4})-(\d{2})-(\d{2})$/.exec(texto);
  if (!partes) return false;
  const data = new Date(Date.UTC(Number(partes[1]), Number(partes[2]) - 1, Number(partes[3])));
  return data.getUTCFullYear() === Number(partes[1]) &&
    data.getUTCMonth() === Number(partes[2]) - 1 &&
    data.getUTCDate() === Number(partes[3]);
}

function prepararLinhas(linhas, cabecalhos) {
  const obrigatorias = ["id_os", "data", "servico", "categoria", "quantidade", "preco_unitario"];
  const normalizados = cabecalhos.map(colunaCanonica);
  const ausentes = obrigatorias.filter((coluna) => !normalizados.includes(coluna));
  if (ausentes.length) {
    throw new Error(`Colunas obrigatórias ausentes: ${ausentes.join(", ")}.`);
  }

  const descartes = {};
  const validas = [];
  let veiculosIncompletos = 0;

  linhas.forEach((linha) => {
    const registro = {};
    Object.keys(linha).forEach((chave) => { registro[colunaCanonica(chave)] = linha[chave]; });
    const quantidade = converterNumero(registro.quantidade);
    const preco = converterNumero(registro.preco_unitario);
    let motivo = "";
    if (String(registro.id_os ?? "").trim() === "") motivo = "ID da OS ausente";
    else if (!dataIsoValida(registro.data)) motivo = "data ausente ou inválida (use AAAA-MM-DD)";
    else if (String(registro.servico ?? "").trim() === "") motivo = "serviço ausente";
    else if (String(registro.categoria ?? "").trim() === "") motivo = "categoria ausente";
    else if (quantidade === null || !Number.isFinite(quantidade) || quantidade < 0 || !Number.isInteger(quantidade)) motivo = "quantidade ausente ou inválida (use número inteiro igual ou maior que zero)";
    else if (preco === null || !Number.isFinite(preco) || preco < 0) motivo = "preço unitário ausente ou inválido (use número igual ou maior que zero)";

    if (motivo) {
      descartes[motivo] = (descartes[motivo] || 0) + 1;
      return;
    }

    const marca = String(registro.marca ?? "").trim();
    const modelo = String(registro.modelo ?? "").trim();
    if (!marca || !modelo) veiculosIncompletos += 1;
    validas.push({
      id_os: String(registro.id_os).trim(),
      data: String(registro.data).trim(),
      marca: marca || "Não informada",
      modelo: modelo || "Não informado",
      servico: String(registro.servico).trim(),
      categoria: String(registro.categoria).trim(),
      quantidade,
      preco_unitario: preco,
      faturamento: quantidade * preco
    });
  });
  return { validas, descartes, veiculosIncompletos };
}

function preencherOpcoes(seletor, valores, textoPadrao) {
  const valorAtual = seletor.value;
  seletor.replaceChildren(new Option(textoPadrao, ""));
  [...new Set(valores)].sort((a, b) => a.localeCompare(b, "pt-BR")).forEach((valor) => {
    seletor.add(new Option(valor, valor));
  });
  seletor.value = [...seletor.options].some((opcao) => opcao.value === valorAtual) ? valorAtual : "";
}

function formatarData(valor) {
  const [ano, mes, dia] = valor.split("-");
  return `${dia}/${mes}/${ano}`;
}

function obterVendasFiltradas() {
  const inicio = elementos.dateFrom.value;
  const fim = elementos.dateTo.value;
  const categoria = elementos.category.value;
  const marca = elementos.brand.value;
  const modelo = elementos.model.value;
  return vendas.filter((venda) =>
    (!inicio || venda.data >= inicio) &&
    (!fim || venda.data <= fim) &&
    (!categoria || venda.categoria === categoria) &&
    (!marca || venda.marca === marca) &&
    (!modelo || venda.modelo === modelo)
  );
}

function calcularIndicadores(linhas) {
  const faturamento = linhas.reduce((soma, linha) => soma + linha.faturamento, 0);
  const unidades = linhas.reduce((soma, linha) => soma + linha.quantidade, 0);
  const ordensUnicas = new Set(linhas.map((linha) => linha.id_os)).size;
  return { faturamento, unidades, ordensUnicas, ticket: ordensUnicas ? faturamento / ordensUnicas : 0 };
}

function atualizarIndicadores(linhas) {
  const totais = calcularIndicadores(linhas);
  document.querySelector("#revenue-total").textContent = formatadorMoeda.format(totais.faturamento);
  document.querySelector("#sales-count").textContent = formatadorNumero.format(totais.ordensUnicas);
  document.querySelector("#units-count").textContent = formatadorNumero.format(totais.unidades);
  document.querySelector("#average-ticket").textContent = formatadorMoeda.format(totais.ticket);
}

function agregar(linhas, chave) {
  const grupos = new Map();
  linhas.forEach((linha) => grupos.set(chave(linha), (grupos.get(chave(linha)) || 0) + linha.faturamento));
  return [...grupos.entries()].sort((a, b) => a[0].localeCompare(b[0], "pt-BR"));
}

function formatarMes(chave) {
  return meses.format(new Date(`${chave}-01T00:00:00Z`)).replace(" de ", "/");
}

function corDoTema(nome, alternativa) {
  return getComputedStyle(document.documentElement).getPropertyValue(nome).trim() || alternativa;
}

function desenharGraficos(linhas) {
  Object.values(chartInstances).forEach((grafico) => grafico.destroy());
  chartInstances = {};
  if (typeof Chart === "undefined") {
    elementos.quality.hidden = false;
    elementos.quality.textContent = "Não foi possível carregar os gráficos. Confira sua conexão com a internet e atualize a página.";
    return;
  }
  const opcoesMoeda = (valor) => formatadorMoeda.format(valor);
  const corTextoGrafico = corDoTema("--chart-text", "#8190a0");
  const corGradeGrafico = corDoTema("--chart-grid", "#edf1f5");
  const corFundoGrafico = corDoTema("--paper", "#ffffff");
  const opcoesComuns = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 250 },
    plugins: {
      legend: { display: false },
      tooltip: { callbacks: { label: (contexto) => ` ${opcoesMoeda(contexto.chart.options.indexAxis === "y" ? contexto.parsed.x : contexto.parsed.y)}` } }
    },
    scales: {
      x: { grid: { display: false }, ticks: { color: corTextoGrafico, font: { family: "Arial", size: 10 } }, border: { display: false } },
      y: { beginAtZero: true, grid: { color: corGradeGrafico, drawTicks: false }, border: { display: false }, ticks: { color: corTextoGrafico, padding: 8, font: { family: "Arial", size: 10 }, callback: (valor) => formatadorNumero.format(valor) } }
    }
  };

  const mensal = agregar(linhas, (linha) => linha.data.slice(0, 7));
  chartInstances.mensal = new Chart(document.querySelector("#monthly-chart"), {
    type: "line",
    data: { labels: mensal.map(([chave]) => formatarMes(chave)), datasets: [{ label: "Faturamento", data: mensal.map(([, total]) => total), borderColor: "#3487e8", backgroundColor: "rgba(52,135,232,.10)", borderWidth: 2.5, fill: true, tension: .35, pointRadius: 3, pointHoverRadius: 5, pointBackgroundColor: corFundoGrafico, pointBorderColor: "#3487e8", pointBorderWidth: 2 }] },
    options: { ...opcoesComuns, interaction: { intersect: false, mode: "index" } }
  });

  {
    const dados = agregar(linhas, (linha) => linha.categoria).sort((a, b) => b[1] - a[1]);
    chartInstances.categoria = new Chart(document.getElementById("category-chart"), {
      type: "bar",
      data: { labels: dados.map(([nome]) => nome), datasets: [{ label: "Faturamento", data: dados.map(([, total]) => total), backgroundColor: dados.map((_, indice) => indice === 0 ? "#3985dd" : "#3985ddb8"), borderRadius: 5, maxBarThickness: 23 }] },
      options: { ...opcoesComuns, indexAxis: "y", scales: { x: { ...opcoesComuns.scales.y, ticks: { ...opcoesComuns.scales.y.ticks, callback: (valor) => formatadorNumero.format(valor) } }, y: { ...opcoesComuns.scales.x, grid: { display: false } } } }
    });
  }
}

function valorOrdenacao(venda, coluna) {
  if (coluna === "faturamento") return venda.faturamento;
  if (coluna === "data") return venda.data;
  if (coluna === "quantidade" || coluna === "preco_unitario") return venda[coluna];
  return venda[coluna].toLocaleLowerCase("pt-BR");
}

function obterVendasDaTabela(linhas) {
  const termo = elementos.search.value.trim().toLocaleLowerCase("pt-BR");
  return linhas.filter((linha) => !termo || [linha.id_os, linha.data, linha.marca, linha.modelo, linha.servico, linha.categoria, linha.quantidade, linha.preco_unitario, linha.faturamento]
    .some((valor) => String(valor).toLocaleLowerCase("pt-BR").includes(termo)))
    .sort((a, b) => {
      const primeiro = valorOrdenacao(a, sortColumn);
      const segundo = valorOrdenacao(b, sortColumn);
      const comparacao = typeof primeiro === "number" ? primeiro - segundo : primeiro.localeCompare(segundo, "pt-BR");
      return comparacao * (sortDirection === "asc" ? 1 : -1);
    });
}

function desenharTabela(linhasFiltradas) {
  const linhas = obterVendasDaTabela(linhasFiltradas);
  elementos.tableBody.replaceChildren();
  linhas.forEach((venda) => {
    const tr = document.createElement("tr");
    const valores = [venda.id_os, formatarData(venda.data), venda.servico, venda.categoria, venda.marca, venda.modelo, formatadorNumero.format(venda.quantidade), formatadorMoeda.format(venda.preco_unitario), formatadorMoeda.format(venda.faturamento)];
    valores.forEach((valor, indice) => {
      const td = document.createElement("td");
      td.textContent = valor;
      if (indice > 5) td.className = "numeric";
      tr.append(td);
    });
    elementos.tableBody.append(tr);
  });
  elementos.emptyState.hidden = linhas.length !== 0;
  const textoContagem = `${formatadorNumero.format(linhas.length)} ${linhas.length === 1 ? "registro" : "registros"}`;
  elementos.recordCount.textContent = `${textoContagem} na tabela após filtros e pesquisa`;
  elementos.tableSummary.textContent = `Exibindo ${textoContagem}`;
}

function atualizarPainel() {
  const filtradas = obterVendasFiltradas();
  atualizarIndicadores(filtradas);
  desenharGraficos(filtradas);
  desenharTabela(filtradas);
}

function mostrarResumoQualidade(resultado, totalLinhas) {
  const { descartes, veiculosIncompletos = 0 } = resultado;
  const quantidadeDescartada = Object.values(descartes).reduce((soma, valor) => soma + valor, 0);
  const motivos = Object.entries(descartes).map(([motivo, quantidade]) => `${quantidade} por ${motivo}`).join("; ");
  const repetidos = vendas.length - new Set(vendas.map((venda) => venda.id_os)).size;
  const partes = [`${vendas.length} de ${totalLinhas} linhas válidas carregadas`];
  if (quantidadeDescartada) partes.push(`${quantidadeDescartada} descartada(s): ${motivos}`);
  if (veiculosIncompletos) partes.push(`${veiculosIncompletos} linha(s) sem marca ou modelo; exibidas como não informadas`);
  if (repetidos) partes.push(`${repetidos} linha(s) repetem um ID de OS; todas foram mantidas e o indicador conta OS únicas`);
  elementos.quality.hidden = !(quantidadeDescartada || repetidos || veiculosIncompletos);
  elementos.quality.textContent = partes.join(". ") + ". Valores zero são aceitos; campos vazios e valores inválidos são tratados separadamente.";
}

function carregarDados(resultado, totalLinhas, demonstrativo) {
  vendas = resultado.validas;
  elementos.dateFrom.value = "";
  elementos.dateTo.value = "";
  elementos.category.value = "";
  elementos.brand.value = "";
  elementos.model.value = "";
  elementos.search.value = "";
  preencherOpcoes(elementos.category, vendas.map((venda) => venda.categoria), "Todas as categorias");
  preencherOpcoes(elementos.brand, vendas.map((venda) => venda.marca), "Todas as marcas");
  preencherOpcoes(elementos.model, vendas.map((venda) => venda.modelo), "Todos os modelos");
  document.querySelector(".demo-badge").innerHTML = demonstrativo ? "<span></span> Dados demonstrativos" : "<span></span> Base importada";
  elementos.note.querySelector("span:last-child").textContent = demonstrativo
    ? "Base demonstrativa da SidCar: veículos, serviços e valores são fictícios. Os CSVs selecionados são lidos localmente no navegador."
    : "Base selecionada pelo usuário. O arquivo é lido localmente e não é enviado a um servidor.";
  mostrarResumoQualidade(resultado, totalLinhas);
  atualizarPainel();
}

function escaparCsv(valor) {
  let texto = String(valor ?? "");
  if (/^[=+@\-\t\r]/.test(texto)) texto = `'${texto}`;
  return `"${texto.replace(/"/g, '""')}"`;
}

function exportarCsv() {
  const linhas = obterVendasDaTabela(obterVendasFiltradas());
  if (!linhas.length) return;
  const cabecalho = [...colunasExportacao, "faturamento"];
  const conteudo = [cabecalho, ...linhas.map((linha) => [...colunasExportacao.map((coluna) => linha[coluna]), linha.faturamento])]
    .map((linha) => linha.map(escaparCsv).join(",")).join("\r\n");
  const arquivo = new Blob(["\uFEFF", conteudo], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(arquivo);
  const link = document.createElement("a");
  link.href = url;
  link.download = "ordens-servico-filtradas.csv";
  link.click();
  URL.revokeObjectURL(url);
}

function proximoIdOs() {
  const usados = new Set(vendas.map((venda) => venda.id_os));
  let numero = 1;
  let identificador = "";
  do {
    identificador = `OS-${String(numero).padStart(4, "0")}`;
    numero += 1;
  } while (usados.has(identificador));
  return identificador;
}

function registrarEntrada(evento) {
  evento.preventDefault();
  const quantidade = converterNumero(elementos.entryQuantity.value);
  const preco = converterNumero(elementos.entryPrice.value);
  const dados = {
    marca: elementos.entryBrand.value.trim(),
    modelo: elementos.entryModel.value.trim(),
    data: elementos.entryDate.value,
    servico: elementos.entryService.value.trim(),
    categoria: elementos.entryCategory.value
  };
  if (Object.values(dados).some((valor) => !valor) || !dataIsoValida(dados.data) ||
      quantidade === null || !Number.isInteger(quantidade) || quantidade < 1 ||
      preco === null || !Number.isFinite(preco) || preco < 0) {
    elementos.entryMessage.hidden = false;
    elementos.entryMessage.textContent = "Confira os campos e informe uma quantidade e um preço válidos.";
    return;
  }

  vendas.push({
    id_os: proximoIdOs(),
    ...dados,
    quantidade,
    preco_unitario: preco,
    faturamento: quantidade * preco
  });
  elementos.entryForm.reset();
  elementos.entryQuantity.value = "1";
  elementos.dateFrom.value = "";
  elementos.dateTo.value = "";
  elementos.category.value = "";
  elementos.brand.value = "";
  elementos.model.value = "";
  elementos.search.value = "";
  preencherOpcoes(elementos.category, vendas.map((venda) => venda.categoria), "Todas as categorias");
  preencherOpcoes(elementos.brand, vendas.map((venda) => venda.marca), "Todas as marcas");
  preencherOpcoes(elementos.model, vendas.map((venda) => venda.modelo), "Todos os modelos");
  elementos.entryMessage.hidden = false;
  elementos.entryMessage.textContent = "Entrada adicionada à lista desta sessão. Exporte o CSV para guardar uma cópia.";
  atualizarPainel();
}

function importarCsv(arquivo) {
  if (!arquivo) return;
  if (typeof Papa === "undefined") {
    elementos.quality.hidden = false;
    elementos.quality.textContent = "Não foi possível carregar o importador CSV. Confira sua conexão com a internet e atualize a página.";
    return;
  }
  Papa.parse(arquivo, {
    header: true,
    skipEmptyLines: "greedy",
    complete: (resultado) => {
      try {
        if (!resultado.meta.fields?.length) throw new Error("O arquivo não tem cabeçalhos reconhecíveis.");
        const preparado = prepararLinhas(resultado.data, resultado.meta.fields);
        if (!preparado.validas.length) throw new Error("Nenhuma linha válida foi encontrada. Confira as colunas e os valores obrigatórios.");
        carregarDados(preparado, resultado.data.length, false);
      } catch (erro) {
        elementos.quality.hidden = false;
        elementos.quality.textContent = `Não foi possível importar o arquivo: ${erro.message}`;
      }
      document.querySelector("#csv-file").value = "";
    },
    error: (erro) => {
      elementos.quality.hidden = false;
      elementos.quality.textContent = `Falha ao ler o CSV: ${erro.message}`;
    }
  });
}

document.querySelectorAll("#date-from, #date-to, #category-filter, #brand-filter, #model-filter").forEach((controle) => controle.addEventListener("change", atualizarPainel));
elementos.search.addEventListener("input", () => desenharTabela(obterVendasFiltradas()));
elementos.entryForm.addEventListener("submit", registrarEntrada);
document.querySelector("#clear-filters").addEventListener("click", () => {
  elementos.dateFrom.value = "";
  elementos.dateTo.value = "";
  elementos.category.value = "";
  elementos.brand.value = "";
  elementos.model.value = "";
  elementos.search.value = "";
  sortColumn = "data";
  sortDirection = "desc";
  atualizarPainel();
});
document.querySelector("#csv-file").addEventListener("change", (evento) => importarCsv(evento.target.files[0]));
document.querySelector("#export-csv").addEventListener("click", exportarCsv);
document.querySelectorAll("[data-sort]").forEach((botao) => botao.addEventListener("click", () => {
  if (sortColumn === botao.dataset.sort) sortDirection = sortDirection === "asc" ? "desc" : "asc";
  else { sortColumn = botao.dataset.sort; sortDirection = "asc"; }
  desenharTabela(obterVendasFiltradas());
}));

const botaoTema = document.querySelector("#theme-toggle");
const rotuloTema = document.querySelector("#theme-toggle-label");

function atualizarControleTema() {
  const escuroAtivo = document.documentElement.dataset.theme === "dark";
  botaoTema.setAttribute("aria-pressed", String(escuroAtivo));
  rotuloTema.textContent = escuroAtivo ? "Tema claro" : "Tema escuro";
  document.querySelector('meta[name="theme-color"]').content = escuroAtivo ? "#111923" : "#f5f7fa";
}

botaoTema.addEventListener("click", () => {
  const novoTema = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = novoTema;
  try {
    localStorage.setItem("tema-dashboard", novoTema);
  } catch (erro) {
    // A troca de tema funciona mesmo se o navegador não permitir salvar a preferência.
  }
  atualizarControleTema();
  atualizarPainel();
});
atualizarControleTema();

const demonstracao = criarDadosDemonstrativos();
const inicial = { validas: demonstracao, descartes: {} };
carregarDados(inicial, demonstracao.length, true);
