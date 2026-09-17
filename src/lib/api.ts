export type ServiceCategory = 'dev' | 'hardware' | 'infra' | 'outros';
export type PricingType = 'fixo' | 'hora' | 'misto';
export type QuoteStatus = 'rascunho' | 'enviado' | 'aprovado' | 'recusado' | 'concluido';

export interface Service {
  id: string;
  nome: string;
  categoria: ServiceCategory;
  tipo_cobranca: PricingType;
  valor_base: number;
  permite_peca: boolean;
  descricao_padrao: string | null;
  criado_em: string;
}

export interface ClientInfo {
  nome: string;
  telefone?: string | null;
  identificador_aparelho?: string | null;
}

export interface QuoteItemInput {
  service_id: string;
  nome: string;
  categoria?: ServiceCategory | null;
  mao_de_obra: number;
  custo_peca?: number;
  horas_estimadas?: number | null;
  taxa_hora?: number | null;
  margem_seguranca?: number | null;
  descricao_customizada?: string | null;
}

export interface QuoteCreate {
  cliente: ClientInfo;
  itens: QuoteItemInput[];
  desconto?: number;
  taxa_deslocamento?: number;
  observacoes?: string | null;
}

export interface QuoteItemResponse extends QuoteItemInput {
  subtotal: number;
}

export interface QuoteResponse {
  id: string;
  cliente: ClientInfo;
  itens: QuoteItemResponse[];
  total_mao_de_obra: number;
  total_pecas: number;
  subtotal_bruto: number;
  desconto: number;
  taxa_deslocamento: number;
  valor_total: number;
  status: QuoteStatus;
  criado_em: string;
  atualizado_em?: string | null;
  observacoes?: string | null;
  mensagem_whatsapp: string;
}

export interface SuggestedService {
  service_id: string;
  nome: string;
  motivo: string;
}

export interface AIInterpretation {
  resumo_problema: string;
  servicos_sugeridos: SuggestedService[];
  observacoes_tecnicas: string;
}

export interface ServiceCreate {
  nome: string;
  categoria: ServiceCategory;
  tipo_cobranca: PricingType;
  valor_base: number;
  permite_peca: boolean;
  descricao_padrao?: string | null;
}

const API_BASE_URL = import.meta.env.VITE_API_URL ?? '/api';

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has('content-type')) {
    headers.set('content-type', 'application/json');
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
  });
  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const detail = data && typeof data.detail === 'string' ? data.detail : 'Não foi possível concluir a operação.';
    throw new Error(detail);
  }

  return data as T;
}

export function getServices(): Promise<Service[]> {
  return request<Service[]>('/services');
}

export function seedServices(): Promise<Service[]> {
  return request<Service[]>('/services/seed', { method: 'POST' });
}

export function createService(service: ServiceCreate): Promise<Service> {
  return request<Service>('/services', {
    method: 'POST',
    body: JSON.stringify(service),
  });
}

export function createQuote(quoteData: QuoteCreate): Promise<QuoteResponse> {
  return request<QuoteResponse>('/quotes', {
    method: 'POST',
    body: JSON.stringify(quoteData),
  });
}

export function getQuote(id: string): Promise<QuoteResponse> {
  return request<QuoteResponse>(`/quotes/${encodeURIComponent(id)}`);
}

export function updateQuote(id: string, quoteData: QuoteCreate): Promise<QuoteResponse> {
  return request<QuoteResponse>(`/quotes/${encodeURIComponent(id)}`, {
    method: 'PUT',
    body: JSON.stringify(quoteData),
  });
}

export async function deleteQuote(id: string): Promise<void> {
  await request<{ success: boolean; message: string }>(`/quotes/${encodeURIComponent(id)}`, {
    method: 'DELETE',
  });
}

export function getQuotes(): Promise<QuoteResponse[]> {
  return request<QuoteResponse[]>('/quotes');
}

export function updateQuoteStatus(id: string, status: QuoteStatus): Promise<QuoteResponse> {
  return request<QuoteResponse>(`/quotes/${encodeURIComponent(id)}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  });
}

export function parseClientRequest(mensagem: string): Promise<AIInterpretation> {
  return request<AIInterpretation>('/ai/parse-request', {
    method: 'POST',
    body: JSON.stringify({ mensagem }),
  });
}
