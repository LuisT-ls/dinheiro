import { browser } from '$app/environment';

export interface BusinessSettings {
  nome: string;
  subtitulo: string;
  telefone: string;
  email: string;
  endereco: string;
  validade_dias: number;
  pagamento: string;
  garantia_hardware: string;
  garantia_dev: string;
  rodape: string;
}

export const DEFAULT_BUSINESS_SETTINGS: BusinessSettings = {
  nome: 'LUÍS TEIXEIRA',
  subtitulo: 'SOLUÇÕES DIGITAIS & SUPORTE TÉCNICO',
  telefone: '',
  email: '',
  endereco: '',
  validade_dias: 15,
  pagamento: '50% de entrada / 50% na aprovação final',
  garantia_hardware: '90 dias sobre a mão de obra, conforme CDC.',
  garantia_dev: '30 dias de suporte para ajustes pós-deploy dentro do escopo.',
  rodape: 'Proposta Comercial & Orçamento Técnico • Documento gerado digitalmente',
};

const STORAGE_KEY = 'dinheiro.business-settings.v1';

export function getBusinessSettings(): BusinessSettings {
  if (!browser) return DEFAULT_BUSINESS_SETTINGS;

  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return { ...DEFAULT_BUSINESS_SETTINGS, ...(raw ? JSON.parse(raw) : {}) };
  } catch {
    return DEFAULT_BUSINESS_SETTINGS;
  }
}

export function saveBusinessSettings(settings: BusinessSettings) {
  if (browser) localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
}

export function resetBusinessSettings() {
  if (browser) localStorage.removeItem(STORAGE_KEY);
  return DEFAULT_BUSINESS_SETTINGS;
}
