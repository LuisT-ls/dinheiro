import type { QuoteResponse, ServiceCategory } from './api';
import type { jsPDF as JsPDF } from 'jspdf';

const COLORS = {
  navy: { red: 15, green: 23, blue: 42 },
  indigo: { red: 79, green: 70, blue: 229 },
  slate800: { red: 30, green: 41, blue: 59 },
  slate500: { red: 100, green: 116, blue: 139 },
  slate200: { red: 226, green: 232, blue: 240 },
  slate50: { red: 248, green: 250, blue: 252 },
  white: { red: 255, green: 255, blue: 255 },
  red600: { red: 220, green: 38, blue: 38 },
};

const categoryLabels: Record<ServiceCategory, string> = {
  hardware: 'Hardware',
  dev: 'Dev',
  infra: 'Infra',
  outros: 'Outros',
};

function money(value: number) {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value || 0);
}

function safeDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? new Date() : date;
}

function dateLabel(value: string | Date) {
  const date = value instanceof Date ? value : safeDate(value);
  return new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' }).format(date);
}

function validityDateLabel(value: string) {
  const date = safeDate(value);
  date.setDate(date.getDate() + 15);
  return dateLabel(date);
}

function fileDate(value: string) {
  return safeDate(value).toISOString().slice(0, 10);
}

function slug(value: string) {
  return (
    value
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '')
      .slice(0, 48) || 'cliente'
  );
}

function proposalNumber(id: string) {
  const compactId = id.replace(/[^a-z0-9]/gi, '').slice(-6).toUpperCase().padStart(6, '0');
  return `#ORC-${compactId}`;
}

function setText(doc: JsPDF, color: keyof typeof COLORS) {
  const value = COLORS[color];
  doc.setTextColor(value.red, value.green, value.blue);
}

function setFill(doc: JsPDF, color: keyof typeof COLORS) {
  const value = COLORS[color];
  doc.setFillColor(value.red, value.green, value.blue);
}

function addFooter(doc: JsPDF) {
  const pages = doc.getNumberOfPages();
  for (let page = 1; page <= pages; page += 1) {
    doc.setPage(page);
    doc.setDrawColor(COLORS.slate200.red, COLORS.slate200.green, COLORS.slate200.blue);
    doc.setLineWidth(0.25);
    doc.line(18, 282, 192, 282);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(8);
    setText(doc, 'slate500');
    doc.text('Dinheiro - proposta comercial', 18, 288);
    doc.text(`Página ${page} de ${pages}`, 192, 288, { align: 'right' });
  }
}

function nextPageIfNeeded(doc: JsPDF, y: number, requiredSpace = 32) {
  if (y + requiredSpace <= 270) return y;
  doc.addPage();
  return 24;
}

export async function gerarOrcamentoPDF(quote: QuoteResponse) {
  const [{ default: JsPDFConstructor }, { default: autoTable }] = await Promise.all([
    import('jspdf'),
    import('jspdf-autotable'),
  ]);
  const doc = new JsPDFConstructor({ unit: 'mm', format: 'a4' });
  const pageWidth = doc.internal.pageSize.getWidth();
  const margin = 18;
  const contentWidth = pageWidth - margin * 2;
  const rightEdge = pageWidth - margin;

  doc.setProperties({
    title: `Orçamento ${quote.id}`,
    subject: 'Proposta comercial e orçamento técnico',
    author: 'Dinheiro',
  });

  // Executive header.
  setFill(doc, 'navy');
  doc.rect(0, 0, pageWidth, 46, 'F');
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(19);
  setText(doc, 'white');
  doc.text('Dinheiro', margin, 16);
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(8.5);
  doc.setTextColor(203, 213, 225);
  doc.text('PROPOSTA COMERCIAL & ORÇAMENTO TÉCNICO', margin, 24);
  doc.setDrawColor(COLORS.indigo.red, COLORS.indigo.green, COLORS.indigo.blue);
  doc.setLineWidth(1.2);
  doc.line(margin, 29, margin + 34, 29);

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(13);
  setText(doc, 'white');
  doc.text(proposalNumber(quote.id), rightEdge, 14, { align: 'right' });
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(8);
  doc.setTextColor(203, 213, 225);
  doc.text(`EMISSÃO  ${dateLabel(quote.criado_em)}`, rightEdge, 23, { align: 'right' });
  doc.text(`VALIDADE  ${validityDateLabel(quote.criado_em)}`, rightEdge, 31, { align: 'right' });

  let y = 58;

  // Client information card.
  setText(doc, 'slate800');
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(10);
  doc.text('DADOS DO CLIENTE', margin, y);
  y += 5;
  setFill(doc, 'slate50');
  doc.roundedRect(margin, y, contentWidth, 31, 3, 3, 'F');
  doc.setDrawColor(COLORS.slate200.red, COLORS.slate200.green, COLORS.slate200.blue);
  doc.setLineWidth(0.25);
  doc.roundedRect(margin, y, contentWidth, 31, 3, 3, 'S');

  const clientX = margin + 7;
  const contactX = margin + 67;
  const projectX = margin + 119;
  const projectWidth = rightEdge - projectX - 7;
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(7.5);
  setText(doc, 'slate500');
  doc.text('CLIENTE', clientX, y + 9);
  doc.text('CONTATO', contactX, y + 9);
  doc.text('PROJETO / EQUIPAMENTO', projectX, y + 9);

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(9.5);
  setText(doc, 'slate800');
  doc.text(quote.cliente.nome || 'Não informado', clientX, y + 18);
  doc.text(quote.cliente.telefone || 'Não informado', contactX, y + 18);
  const project = quote.cliente.identificador_aparelho || 'Não informado';
  const projectLines = doc.splitTextToSize(project, projectWidth);
  doc.text(projectLines.slice(0, 2), projectX, y + 18);
  y += 43;

  // Services table.
  setText(doc, 'slate800');
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(10);
  doc.text('SERVIÇOS E ITENS DO ORÇAMENTO', margin, y);
  y += 4;

  autoTable(doc, {
    startY: y,
    margin: { left: margin, right: margin },
    head: [['DESCRIÇÃO DO SERVIÇO', 'CATEGORIA', 'MÃO DE OBRA', 'PEÇAS / REPOSIÇÃO', 'SUBTOTAL']],
    body: quote.itens.map((item) => [
      item.nome,
      item.categoria ? categoryLabels[item.categoria] : 'Serviço técnico',
      money(item.subtotal - (item.custo_peca || 0)),
      money(item.custo_peca || 0),
      money(item.subtotal),
    ]),
    theme: 'grid',
    styles: {
      font: 'helvetica',
      fontSize: 8.5,
      cellPadding: { top: 6, right: 4, bottom: 6, left: 4 },
      textColor: [30, 41, 59],
      lineColor: [226, 232, 240],
      lineWidth: 0.2,
      valign: 'middle',
    },
    headStyles: {
      fillColor: [15, 23, 42],
      textColor: [255, 255, 255],
      fontStyle: 'bold',
      fontSize: 8.5,
      halign: 'left',
      cellPadding: { top: 5, right: 4, bottom: 5, left: 4 },
    },
    alternateRowStyles: { fillColor: [248, 250, 252] },
    columnStyles: {
      0: { cellWidth: 61, fontStyle: 'bold' },
      1: { cellWidth: 27, halign: 'center' },
      2: { cellWidth: 28, halign: 'right' },
      3: { cellWidth: 28, halign: 'right' },
      4: { cellWidth: 28, halign: 'right', fontStyle: 'bold' },
    },
  });

  const tableEnd = (doc as JsPDF & { lastAutoTable?: { finalY: number } }).lastAutoTable?.finalY ?? y + 20;
  y = nextPageIfNeeded(doc, tableEnd + 12, 55);

  // Financial summary aligned to the right.
  setText(doc, 'slate800');
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(10);
  doc.text('RESUMO FINANCEIRO', rightEdge, y, { align: 'right' });
  y += 7;

  const summaryRows: Array<{ label: string; value: string; color?: keyof typeof COLORS }> = [
    { label: 'Subtotal serviços', value: money(quote.total_mao_de_obra) },
    { label: 'Subtotal peças', value: money(quote.total_pecas) },
  ];
  if (quote.taxa_deslocamento > 0) {
    summaryRows.push({ label: 'Taxa de deslocamento', value: money(quote.taxa_deslocamento) });
  }
  if (quote.desconto > 0) {
    summaryRows.push({ label: 'Desconto', value: `- ${money(quote.desconto)}`, color: 'red600' });
  }

  const summaryLeft = 117;
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(9);
  for (const row of summaryRows) {
    setText(doc, 'slate500');
    doc.text(row.label, summaryLeft, y);
    setText(doc, row.color ?? 'slate800');
    doc.text(row.value, rightEdge, y, { align: 'right' });
    y += 6;
  }

  setFill(doc, 'navy');
  doc.roundedRect(summaryLeft - 5, y - 2, rightEdge - summaryLeft + 5, 16, 2, 2, 'F');
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(12);
  setText(doc, 'white');
  doc.text('VALOR TOTAL', summaryLeft, y + 8);
  doc.text(money(quote.valor_total), rightEdge - 5, y + 8, { align: 'right' });
  y += 29;

  // Commercial terms and signature area.
  y = nextPageIfNeeded(doc, y, 73);
  doc.setDrawColor(COLORS.slate200.red, COLORS.slate200.green, COLORS.slate200.blue);
  doc.setLineWidth(0.25);
  doc.line(margin, y, rightEdge, y);
  y += 8;
  setText(doc, 'slate800');
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(10);
  doc.text('CONDIÇÕES GERAIS E GARANTIA', margin, y);
  y += 6;

  const cardGap = 6;
  const cardWidth = (contentWidth - cardGap) / 2;
  const cardHeight = 43;
  const termsCards = [
    {
      x: margin,
      title: 'PRAZOS E PAGAMENTO',
      lines: [
        'Prazo de execução e entrega: conforme escopo e agenda aprovados.',
        'Condição padrão: 50% de entrada e 50% na aprovação final.',
      ],
    },
    {
      x: margin + cardWidth + cardGap,
      title: 'GARANTIA TÉCNICA',
      lines: [
        'Hardware: 90 dias sobre a mão de obra, conforme CDC e condições acordadas.',
        'Desenvolvimento: 30 dias de suporte para ajustes pós-deploy dentro do escopo aprovado.',
      ],
    },
  ];

  for (const card of termsCards) {
    setFill(doc, 'slate50');
    doc.roundedRect(card.x, y, cardWidth, cardHeight, 3, 3, 'F');
    doc.setDrawColor(COLORS.slate200.red, COLORS.slate200.green, COLORS.slate200.blue);
    doc.roundedRect(card.x, y, cardWidth, cardHeight, 3, 3, 'S');
    setText(doc, 'indigo');
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(7.5);
    doc.text(card.title, card.x + 6, y + 9);
    setText(doc, 'slate500');
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(7.8);
    let cardY = y + 17;
    for (const line of card.lines) {
      const wrapped = doc.splitTextToSize(`- ${line}`, cardWidth - 12);
      doc.text(wrapped, card.x + 6, cardY);
      cardY += wrapped.length * 3.7 + 3;
    }
  }

  y += cardHeight + 12;
  y = nextPageIfNeeded(doc, y, 28);
  setText(doc, 'slate800');
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(8.5);
  doc.text('ASSINATURA / APROVAÇÃO', margin, y);
  y += 14;
  doc.setDrawColor(COLORS.slate500.red, COLORS.slate500.green, COLORS.slate500.blue);
  doc.setLineWidth(0.25);
  doc.line(margin, y, margin + 82, y);
  doc.line(margin + 98, y, rightEdge, y);
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7.5);
  setText(doc, 'slate500');
  doc.text('Nome e assinatura do cliente', margin, y + 5);
  doc.text('Data', margin + 98, y + 5);

  addFooter(doc);
  doc.save(`orcamento-${slug(quote.cliente.nome)}-${fileDate(quote.criado_em)}.pdf`);
}
