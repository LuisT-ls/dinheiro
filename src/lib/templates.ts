import { browser } from '$app/environment';

export interface QuoteTemplateItem {
  service_id: string;
  mao_de_obra: number;
  custo_interno: number;
  custo_peca: number;
  horas_estimadas: number | null;
  taxa_hora: number | null;
  margem_seguranca: number;
  descricao_customizada: string | null;
}

export interface QuoteTemplate {
  id: string;
  nome: string;
  itens: QuoteTemplateItem[];
  desconto: number;
  taxa_deslocamento: number;
  observacoes: string;
  criado_em: string;
}

const STORAGE_KEY = 'dinheiro.quote-templates.v1';

function readTemplates(): QuoteTemplate[] {
  if (!browser) return [];

  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const templates = raw ? (JSON.parse(raw) as QuoteTemplate[]) : [];
    return Array.isArray(templates) ? templates : [];
  } catch {
    return [];
  }
}

function writeTemplates(templates: QuoteTemplate[]) {
  if (!browser) return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(templates));
}

export function listQuoteTemplates() {
  return readTemplates().sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'));
}

export function saveQuoteTemplate(template: Omit<QuoteTemplate, 'id' | 'criado_em'>) {
  const id = typeof crypto !== 'undefined' && 'randomUUID' in crypto ? crypto.randomUUID() : `${Date.now()}`;
  const created: QuoteTemplate = { ...template, id, criado_em: new Date().toISOString() };
  writeTemplates([...readTemplates().filter((item) => item.nome.toLowerCase() !== created.nome.toLowerCase()), created]);
  return created;
}

export function removeQuoteTemplate(id: string) {
  writeTemplates(readTemplates().filter((template) => template.id !== id));
}
