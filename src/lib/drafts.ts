import { browser } from '$app/environment';

export interface SavedQuoteDraft {
  cliente: {
    nome: string;
    telefone?: string | null;
    identificador_aparelho?: string | null;
  };
  observacoes: string;
  clientMessage: string;
  desconto: number;
  taxa_deslocamento: number;
  itens: Array<{
    service_id: string;
    mao_de_obra: number;
    custo_interno: number;
    custo_peca: number;
    horas_estimadas: number | null;
    taxa_hora: number | null;
    margem_seguranca: number;
    descricao_customizada: string | null;
  }>;
  atualizado_em: string;
}

const STORAGE_KEY = 'dinheiro.quote-draft.v1';

export function loadSavedQuoteDraft(): SavedQuoteDraft | null {
  if (!browser) return null;

  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as SavedQuoteDraft) : null;
  } catch {
    return null;
  }
}

export function saveQuoteDraft(draft: SavedQuoteDraft) {
  if (!browser) return;

  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(draft));
  } catch {
    // Rascunho local é uma conveniência; falhas de storage não bloqueiam o orçamento.
  }
}

export function clearSavedQuoteDraft() {
  if (browser) localStorage.removeItem(STORAGE_KEY);
}
