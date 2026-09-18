"""Pydantic schemas used by the services and quotes API."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    """Base model with strict payload handling for API boundaries."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class ServiceCategory(str, Enum):
    DEV = "dev"
    HARDWARE = "hardware"
    INFRA = "infra"
    OUTROS = "outros"


class PricingType(str, Enum):
    FIXO = "fixo"
    HORA = "hora"
    MISTO = "misto"


class QuoteStatus(str, Enum):
    RASCUNHO = "rascunho"
    ENVIADO = "enviado"
    NEGOCIACAO = "negociacao"
    APROVADO = "aprovado"
    RECUSADO = "recusado"
    CONCLUIDO = "concluido"


class ServiceBase(StrictModel):
    nome: str = Field(..., min_length=1, max_length=150)
    categoria: ServiceCategory
    tipo_cobranca: PricingType
    valor_base: float = Field(..., ge=0)
    custo_base: float = Field(default=0.0, ge=0)
    permite_peca: bool = False
    descricao_padrao: str | None = Field(default=None, max_length=1000)


class ServiceCreate(ServiceBase):
    pass


class ServiceResponse(ServiceBase):
    id: str = Field(..., min_length=1)
    criado_em: datetime


class AIRequest(StrictModel):
    mensagem: str = Field(..., min_length=1, max_length=5000)


class SuggestedService(StrictModel):
    service_id: str = Field(..., min_length=1, max_length=150)
    nome: str = Field(..., min_length=1, max_length=150)
    motivo: str = Field(..., min_length=1, max_length=500)


class AIInterpretation(StrictModel):
    resumo_problema: str = Field(..., min_length=1, max_length=1000)
    servicos_sugeridos: list[SuggestedService] = Field(default_factory=list)
    observacoes_tecnicas: str = Field(..., min_length=1, max_length=2000)


class ClientInfo(StrictModel):
    nome: str = Field(..., min_length=1, max_length=150)
    telefone: str | None = Field(default=None, max_length=40)
    identificador_aparelho: str | None = Field(default=None, max_length=200)


class QuoteItemInput(StrictModel):
    service_id: str = Field(..., min_length=1, max_length=150)
    nome: str = Field(..., min_length=1, max_length=200)
    categoria: ServiceCategory | None = None
    mao_de_obra: float = Field(..., ge=0)
    custo_interno: float = Field(default=0.0, ge=0)
    custo_peca: float = Field(default=0.0, ge=0)
    horas_estimadas: float | None = Field(default=None, ge=0)
    taxa_hora: float | None = Field(default=None, ge=0)
    margem_seguranca: float | None = Field(default=1.25, gt=0)
    descricao_customizada: str | None = Field(default=None, max_length=1000)


class QuoteItemResponse(QuoteItemInput):
    subtotal: float = Field(..., ge=0)
    margem_bruta: float = 0.0


class QuoteCreate(StrictModel):
    cliente: ClientInfo
    itens: list[QuoteItemInput] = Field(..., min_length=1)
    desconto: float = Field(default=0.0, ge=0)
    taxa_deslocamento: float = Field(default=0.0, ge=0)
    observacoes: str | None = Field(default=None, max_length=2000)


class QuoteStatusUpdate(StrictModel):
    status: QuoteStatus


class QuoteResponse(StrictModel):
    id: str = Field(..., min_length=1)
    cliente: ClientInfo
    itens: list[QuoteItemResponse] = Field(..., min_length=1)
    total_mao_de_obra: float = Field(..., ge=0)
    total_pecas: float = Field(..., ge=0)
    subtotal_bruto: float = Field(..., ge=0)
    desconto: float = Field(..., ge=0)
    taxa_deslocamento: float = Field(..., ge=0)
    valor_total: float
    custo_interno_total: float = 0.0
    margem_bruta: float = 0.0
    margem_percentual: float = 0.0
    status: QuoteStatus
    criado_em: datetime
    atualizado_em: datetime | None = None
    observacoes: str | None = None
    mensagem_whatsapp: str
