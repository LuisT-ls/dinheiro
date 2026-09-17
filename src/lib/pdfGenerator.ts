import type { QuoteResponse, ServiceCategory } from './api';
import type { jsPDF as JsPDF } from 'jspdf';

const PROVIDER_NAME = 'LUÍS TEIXEIRA';
const PROVIDER_SUBTITLE = 'SOLUÇÕES DIGITAIS & SUPORTE TÉCNICO';
const FOOTER_LABEL = 'Proposta Comercial & Orçamento Técnico • Documento gerado digitalmente';

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
    doc.setFontSize(7.1);
    setText(doc, 'slate500');
    doc.text(FOOTER_LABEL, 18, 288);
    doc.text(`Página ${page} de ${pages}`, 192, 288, { align: 'right' });
  }
}

export async function gerarOrcamentoPDF(quote: QuoteResponse) {
  const [{ jsPDF: JsPDFConstructor }, { autoTable }] = await Promise.all([
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
    author: PROVIDER_NAME,
  });

  // Cabeçalho executivo compacto.
  setFill(doc, 'navy');
  doc.rect(0, 0, pageWidth, 42, 'F');
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(16.5);
  setText(doc, 'white');
  doc.text(PROVIDER_NAME, margin, 15);
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7.7);
  doc.setTextColor(203, 213, 225);
  doc.text(PROVIDER_SUBTITLE, margin, 22);
  doc.setDrawColor(COLORS.indigo.red, COLORS.indigo.green, COLORS.indigo.blue);
  doc.setLineWidth(1.1);
  doc.line(margin, 27, margin + 34, 27);

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(12.5);
  setText(doc, 'white');
  doc.text(proposalNumber(quote.id), rightEdge, 14, { align: 'right' });
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7.8);
  doc.setTextColor(203, 213, 225);
  doc.text(`EMISSÃO  ${dateLabel(quote.criado_em)}`, rightEdge, 22, { align: 'right' });
  doc.text(`VALIDADE  ${validityDateLabel(quote.criado_em)}`, rightEdge, 29, { align: 'right' });

  let y = 53;

  // Card de dados do cliente.
  setText(doc, 'slate800');
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(9.5);
  doc.text('DADOS DO CLIENTE', margin, y);
  y += 5;
  setFill(doc, 'slate50');
  doc.roundedRect(margin, y, contentWidth, 25, 3, 3, 'F');
  doc.setDrawColor(COLORS.slate200.red, COLORS.slate200.green, COLORS.slate200.blue);
  doc.setLineWidth(0.25);
  doc.roundedRect(margin, y, contentWidth, 25, 3, 3, 'S');

  const clientX = margin + 7;
  const contactX = margin + 67;
  const projectX = margin + 119;
  const projectWidth = rightEdge - projectX - 7;
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(7.2);
  setText(doc, 'slate500');
  doc.text('CLIENTE', clientX, y + 8);
  doc.text('CONTATO', contactX, y + 8);
  doc.text('PROJETO / EQUIPAMENTO', projectX, y + 8);

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(9);
  setText(doc, 'slate800');
  doc.text(quote.cliente.nome || 'Não informado', clientX, y + 16);
  doc.text(quote.cliente.telefone || 'Não informado', contactX, y + 16);
  const project = quote.cliente.identificador_aparelho || 'Não informado';
  doc.text(doc.splitTextToSize(project, projectWidth).slice(0, 2), projectX, y + 16);
  y += 35;

  // Tabela de serviços.
  setText(doc, 'slate800');
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(9.5);
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
      cellPadding: { top: 3, right: 4, bottom: 3, left: 4 },
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
      cellPadding: { top: 3, right: 4, bottom: 3, left: 4 },
    },
    alternateRowStyles: { fillColor: [248, 250, 252] },
    columnStyles: {
      0: { cellWidth: 59, fontStyle: 'bold' },
      1: { cellWidth: 26, halign: 'center' },
      2: { cellWidth: 28, halign: 'right' },
      3: { cellWidth: 28, halign: 'right' },
      4: { cellWidth: 29, halign: 'right', fontStyle: 'bold' },
    },
  });

  const tableEnd = (doc as JsPDF & { lastAutoTable?: { finalY: number } }).lastAutoTable?.finalY ?? y + 16;

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

  // O resumo começa abaixo da tabela e fica isolado na lateral direita.
  let finalY = tableEnd + 4;
  if (finalY > 230) {
    doc.addPage();
    finalY = 24;
  }

  const summaryStartX = 120;
  const summaryWidth = rightEdge - summaryStartX;
  const summaryHeight = 9 + summaryRows.length * 4.8 + 13;
  setFill(doc, 'slate50');
  doc.roundedRect(summaryStartX, finalY, summaryWidth, summaryHeight, 2.5, 2.5, 'F');
  doc.setDrawColor(COLORS.slate200.red, COLORS.slate200.green, COLORS.slate200.blue);
  doc.setLineWidth(0.25);
  doc.roundedRect(summaryStartX, finalY, summaryWidth, summaryHeight, 2.5, 2.5, 'S');
  setText(doc, 'slate800');
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(8.2);
  doc.text('RESUMO FINANCEIRO', summaryStartX + 5, finalY + 7);

  y = finalY + 13;
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7.8);
  for (const row of summaryRows) {
    setText(doc, 'slate500');
    doc.text(row.label, summaryStartX + 5, y);
    setText(doc, row.color ?? 'slate800');
    doc.text(row.value, rightEdge - 5, y, { align: 'right' });
    y += 4.8;
  }

  const totalY = finalY + summaryHeight - 13;
  setFill(doc, 'navy');
  doc.roundedRect(summaryStartX, totalY, summaryWidth, 13, 2, 2, 'F');
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(10.5);
  setText(doc, 'white');
  doc.text('VALOR TOTAL', summaryStartX + 5, totalY + 8.2);
  doc.text(money(quote.valor_total), rightEdge - 5, totalY + 8.2, { align: 'right' });

  // Condições compactas, mantidas na mesma página sempre que o finalY permitir.
  y = finalY + summaryHeight + 6;
  doc.setDrawColor(COLORS.slate200.red, COLORS.slate200.green, COLORS.slate200.blue);
  doc.setLineWidth(0.25);
  doc.line(margin, y, rightEdge, y);
  y += 5;
  setText(doc, 'slate800');
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(8.8);
  doc.text('CONDIÇÕES GERAIS E GARANTIA', margin, y);
  y += 5;

  const cardGap = 6;
  const cardWidth = (contentWidth - cardGap) / 2;
  const cardHeight = 29;
  const termsCards = [
    {
      x: margin,
      title: 'PRAZOS E PAGAMENTO',
      lines: [
        'Execução e entrega conforme escopo e agenda aprovados.',
        'Pagamento padrão: 50% de entrada e 50% na aprovação final.',
      ],
    },
    {
      x: margin + cardWidth + cardGap,
      title: 'GARANTIA TÉCNICA',
      lines: [
        'Hardware: 90 dias sobre a mão de obra, conforme CDC.',
        'Dev: 30 dias de suporte para ajustes pós-deploy dentro do escopo.',
      ],
    },
  ];

  for (const card of termsCards) {
    setFill(doc, 'slate50');
    doc.roundedRect(card.x, y, cardWidth, cardHeight, 2.5, 2.5, 'F');
    doc.setDrawColor(COLORS.slate200.red, COLORS.slate200.green, COLORS.slate200.blue);
    doc.roundedRect(card.x, y, cardWidth, cardHeight, 2.5, 2.5, 'S');
    setText(doc, 'indigo');
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(7.2);
    doc.text(card.title, card.x + 5, y + 7);
    setText(doc, 'slate500');
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(7.1);
    let cardY = y + 13;
    for (const line of card.lines) {
      const wrapped = doc.splitTextToSize(`- ${line}`, cardWidth - 10);
      doc.text(wrapped, card.x + 5, cardY);
      cardY += wrapped.length * 3.2 + 2;
    }
  }

  // Assinatura horizontal, sem bloco vertical adicional.
  y += cardHeight + 8;
  setText(doc, 'slate800');
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(7.8);
  doc.text('ASSINATURA / APROVAÇÃO', margin, y);
  y += 9;
  doc.setDrawColor(COLORS.slate500.red, COLORS.slate500.green, COLORS.slate500.blue);
  doc.setLineWidth(0.25);
  doc.line(margin, y, margin + 77, y);
  doc.line(margin + 97, y, rightEdge, y);
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7.2);
  setText(doc, 'slate500');
  doc.text('Prestador de Serviços', margin, y + 4.5);
  doc.text('Aceite do Cliente (Nome e Assinatura)', margin + 97, y + 4.5);

  addFooter(doc);
  doc.save(`orcamento-${slug(quote.cliente.nome)}-${fileDate(quote.criado_em)}.pdf`);
}
