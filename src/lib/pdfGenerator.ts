import type { QuoteResponse, ServiceCategory } from './api';
import type { jsPDF as JsPDF } from 'jspdf';

const NAVY = { red: 15, green: 23, blue: 42 };
const INDIGO = { red: 79, green: 70, blue: 229 };
const SLATE = { red: 71, green: 85, blue: 105 };
const LIGHT_SLATE = { red: 241, green: 245, blue: 249 };

const categoryLabels: Record<ServiceCategory, string> = {
  hardware: 'Hardware',
  dev: 'Dev',
  infra: 'Infra',
  outros: 'Outros',
};

function money(value: number) {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value || 0);
}

function dateLabel(value: string) {
  return new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' }).format(new Date(value));
}

function fileDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return new Date().toISOString().slice(0, 10);
  return date.toISOString().slice(0, 10);
}

function slug(value: string) {
  return value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 48) || 'cliente';
}

function addFooter(doc: JsPDF) {
  const pages = doc.getNumberOfPages();
  for (let page = 1; page <= pages; page += 1) {
    doc.setPage(page);
    doc.setDrawColor(226, 232, 240);
    doc.line(18, 282, 192, 282);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(8);
    doc.setTextColor(SLATE.red, SLATE.green, SLATE.blue);
    doc.text('Dinheiro · orçamento de prestação de serviços', 18, 288);
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

  doc.setProperties({
    title: `Orçamento ${quote.id}`,
    subject: 'Orçamento de prestação de serviços',
    author: 'Dinheiro',
  });

  doc.setFillColor(NAVY.red, NAVY.green, NAVY.blue);
  doc.rect(0, 0, pageWidth, 35, 'F');
  doc.setTextColor(255, 255, 255);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(15);
  doc.text('ORÇAMENTO DE PRESTAÇÃO DE SERVIÇOS', margin, 16);
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(8.5);
  doc.setTextColor(203, 213, 225);
  doc.text('Uma proposta clara para o próximo passo do seu projeto.', margin, 24);
  doc.setTextColor(255, 255, 255);
  doc.setFontSize(8);
  doc.text(`EMISSÃO  ${dateLabel(quote.criado_em)}`, pageWidth - margin, 15, { align: 'right' });
  doc.text(`ID  ${quote.id}`, pageWidth - margin, 23, { align: 'right' });

  let y = 47;
  doc.setTextColor(NAVY.red, NAVY.green, NAVY.blue);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(10);
  doc.text('DADOS DO CLIENTE', margin, y);
  y += 5;
  doc.setFillColor(LIGHT_SLATE.red, LIGHT_SLATE.green, LIGHT_SLATE.blue);
  doc.roundedRect(margin, y, pageWidth - margin * 2, 25, 3, 3, 'F');
  doc.setFontSize(9);
  doc.setTextColor(NAVY.red, NAVY.green, NAVY.blue);
  doc.text('Nome', margin + 6, y + 8);
  doc.text('Telefone', margin + 78, y + 8);
  doc.text('Aparelho / projeto', margin + 126, y + 8);
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(9.5);
  doc.text(quote.cliente.nome || 'Não informado', margin + 6, y + 16);
  doc.text(quote.cliente.telefone || 'Não informado', margin + 78, y + 16);
  const project = quote.cliente.identificador_aparelho || 'Não informado';
  doc.text(doc.splitTextToSize(project, 52), margin + 126, y + 16);
  y += 38;

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(10);
  doc.setTextColor(NAVY.red, NAVY.green, NAVY.blue);
  doc.text('ITENS DO ORÇAMENTO', margin, y);
  y += 4;

  autoTable(doc, {
    startY: y,
    margin: { left: margin, right: margin },
    head: [['Descrição do serviço', 'Categoria', 'Mão de obra', 'Custo de peça', 'Subtotal']],
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
      cellPadding: 4,
      textColor: [51, 65, 85],
      lineColor: [226, 232, 240],
      lineWidth: 0.2,
      valign: 'middle',
    },
    headStyles: {
      fillColor: [79, 70, 229],
      textColor: [255, 255, 255],
      fontStyle: 'bold',
      halign: 'left',
    },
    alternateRowStyles: { fillColor: [248, 250, 252] },
    columnStyles: {
      0: { cellWidth: 61 },
      1: { cellWidth: 27 },
      2: { cellWidth: 28, halign: 'right' },
      3: { cellWidth: 28, halign: 'right' },
      4: { cellWidth: 28, halign: 'right', fontStyle: 'bold' },
    },
  });

  const tableEnd = (doc as JsPDF & { lastAutoTable?: { finalY: number } }).lastAutoTable?.finalY ?? y + 20;
  y = nextPageIfNeeded(doc, tableEnd + 12, 55);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(10);
  doc.setTextColor(NAVY.red, NAVY.green, NAVY.blue);
  doc.text('RESUMO FINANCEIRO', pageWidth - margin, y, { align: 'right' });
  y += 7;

  const summaryRows: [string, string][] = [
    ['Subtotal mão de obra', money(quote.total_mao_de_obra)],
    ['Subtotal peças', money(quote.total_pecas)],
  ];
  if (quote.taxa_deslocamento > 0) summaryRows.push(['Taxa de deslocamento', money(quote.taxa_deslocamento)]);
  if (quote.desconto > 0) summaryRows.push(['Desconto', `- ${money(quote.desconto)}`]);

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(9);
  for (const [label, value] of summaryRows) {
    doc.setTextColor(SLATE.red, SLATE.green, SLATE.blue);
    doc.text(label, 117, y);
    doc.setTextColor(NAVY.red, NAVY.green, NAVY.blue);
    doc.text(value, pageWidth - margin, y, { align: 'right' });
    y += 6;
  }

  doc.setFillColor(INDIGO.red, INDIGO.green, INDIGO.blue);
  doc.roundedRect(112, y - 1, pageWidth - margin - 112, 13, 2, 2, 'F');
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(10);
  doc.setTextColor(255, 255, 255);
  doc.text('VALOR TOTAL', 117, y + 7);
  doc.text(money(quote.valor_total), pageWidth - margin, y + 7, { align: 'right' });
  y += 25;

  y = nextPageIfNeeded(doc, y, 42);
  doc.setDrawColor(226, 232, 240);
  doc.line(margin, y, pageWidth - margin, y);
  y += 8;
  doc.setTextColor(NAVY.red, NAVY.green, NAVY.blue);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(9);
  doc.text('CONDIÇÕES COMERCIAIS', margin, y);
  y += 6;
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(8.5);
  doc.setTextColor(SLATE.red, SLATE.green, SLATE.blue);
  const terms = [
    'Validade desta proposta: 15 dias corridos a partir da data de emissão.',
    'Serviços de hardware: garantia de 90 dias sobre a mão de obra, conforme o CDC e as condições acordadas.',
    'Projetos de desenvolvimento: escopo, prazo, entregáveis e ajustes seguem o alinhamento comercial aprovado.',
  ];
  for (const term of terms) {
    const lines = doc.splitTextToSize(`• ${term}`, pageWidth - margin * 2);
    doc.text(lines, margin, y);
    y += lines.length * 4.5 + 1.5;
  }

  addFooter(doc);
  doc.save(`orcamento-${slug(quote.cliente.nome)}-${fileDate(quote.criado_em)}.pdf`);
}
