"""Quote calculation, persistence and history routes."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from ..config import db
from ..schemas import (
    QuoteCreate,
    QuoteItemInput,
    QuoteItemResponse,
    QuoteResponse,
    QuoteStatus,
    QuoteStatusUpdate,
)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/quotes", tags=["Orçamentos"])
COLLECTION_NAME = "quotes"


def _require_db():
    if db is None:
        raise HTTPException(
            status_code=500,
            detail="Firestore não está configurado para esta aplicação.",
        )
    return db


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _money(value: float) -> float:
    return round(value, 2)


def _currency(value: float) -> str:
    formatted = f"{value:,.2f}"
    return f"R$ {formatted.replace(',', 'X').replace('.', ',').replace('X', '.')}"


def _item_labor(item: QuoteItemInput) -> float:
    if item.horas_estimadas is not None and item.taxa_hora is not None:
        margin = item.margem_seguranca if item.margem_seguranca is not None else 1.25
        return _money(item.horas_estimadas * item.taxa_hora * margin)
    return _money(item.mao_de_obra)


def _whatsapp_message(
    quote: QuoteCreate,
    items: list[QuoteItemResponse],
    labor_values: list[float],
    total_labor: float,
    total_parts: float,
    gross_subtotal: float,
    total: float,
) -> str:
    lines = [
        "🧾 *Orçamento de serviços*",
        f"👤 Cliente: {quote.cliente.nome}",
    ]

    if quote.cliente.telefone:
        lines.append(f"📱 Telefone: {quote.cliente.telefone}")
    if quote.cliente.identificador_aparelho:
        lines.append(f"💻 Aparelho: {quote.cliente.identificador_aparelho}")

    lines.extend(["", "🛠️ *Itens do orçamento:*"])
    for item, labor in zip(items, labor_values):
        lines.append(f"• *{item.nome}*")
        if item.descricao_customizada:
            lines.append(f"  _{item.descricao_customizada}_")
        lines.append(f"  Mão de obra: {_currency(labor)}")
        if item.custo_peca > 0:
            lines.append(f"  Peça: {_currency(item.custo_peca)}")
        lines.append(f"  Subtotal: {_currency(item.subtotal)}")

    lines.extend(
        [
            "",
            f"🔧 Total mão de obra: {_currency(total_labor)}",
            f"🔩 Total peças: {_currency(total_parts)}",
            f"📋 Subtotal: {_currency(gross_subtotal)}",
        ],
    )

    if quote.desconto > 0:
        lines.append(f"🏷️ Desconto: -{_currency(quote.desconto)}")
    if quote.taxa_deslocamento > 0:
        lines.append(
            f"🚗 Taxa de deslocamento: {_currency(quote.taxa_deslocamento)}",
        )
    if quote.observacoes:
        lines.extend(["", f"📝 Prazo/observações: {quote.observacoes}"])

    lines.extend(["", f"✅ *Valor total: {_currency(total)}*"])
    return "\n".join(lines)


def _calculate_quote(
    quote: QuoteCreate,
) -> tuple[list[QuoteItemResponse], list[float], float, float, float, float, str, float]:
    response_items: list[QuoteItemResponse] = []
    labor_values: list[float] = []
    total_labor = 0.0
    total_parts = 0.0
    total_internal_cost = 0.0

    for item in quote.itens:
        labor = _item_labor(item)
        parts = _money(item.custo_peca)
        subtotal = _money(labor + parts)
        internal_cost = _money(item.custo_interno)
        gross_margin = _money(labor - internal_cost)

        labor_values.append(labor)
        total_labor = _money(total_labor + labor)
        total_parts = _money(total_parts + parts)
        total_internal_cost = _money(total_internal_cost + internal_cost)
        response_items.append(
            QuoteItemResponse(
                **item.model_dump(),
                subtotal=subtotal,
                margem_bruta=gross_margin,
            ),
        )

    gross_subtotal = _money(total_labor + total_parts)
    total = _money(
        gross_subtotal
        + _money(quote.taxa_deslocamento)
        - _money(quote.desconto),
    )
    message = _whatsapp_message(
        quote,
        response_items,
        labor_values,
        total_labor,
        total_parts,
        gross_subtotal,
        total,
    )

    return (
        response_items,
        labor_values,
        total_labor,
        total_parts,
        gross_subtotal,
        total,
        message,
        total_internal_cost,
    )


def _quote_payload(
    quote: QuoteCreate,
    response_items: list[QuoteItemResponse],
    total_labor: float,
    total_parts: float,
    gross_subtotal: float,
    total: float,
    message: str,
    status: str,
    created_at: datetime,
    total_internal_cost: float,
    updated_at: datetime | None = None,
) -> dict:
    payload = {
        "cliente": quote.cliente.model_dump(mode="json"),
        "itens": [
            {
                **item.model_dump(mode="json"),
                "subtotal": response_item.subtotal,
                "margem_bruta": response_item.margem_bruta,
            }
            for item, response_item in zip(quote.itens, response_items)
        ],
        "total_mao_de_obra": total_labor,
        "total_pecas": total_parts,
        "subtotal_bruto": gross_subtotal,
        "desconto": _money(quote.desconto),
        "taxa_deslocamento": _money(quote.taxa_deslocamento),
        "valor_total": total,
        "custo_interno_total": _money(total_internal_cost),
        "margem_bruta": _money(total_labor - total_internal_cost),
        "margem_percentual": _money((total_labor - total_internal_cost) / total_labor * 100) if total_labor else 0.0,
        "status": status,
        "criado_em": created_at,
        "observacoes": quote.observacoes,
        "mensagem_whatsapp": message,
    }
    if updated_at is not None:
        payload["atualizado_em"] = updated_at
    return payload


def _quote_from_snapshot(snapshot) -> QuoteResponse:
    data = snapshot.to_dict() or {}
    data["id"] = snapshot.id
    data.setdefault("status", QuoteStatus.RASCUNHO.value)
    data.setdefault("criado_em", getattr(snapshot, "create_time", _utc_now()))
    data.setdefault("observacoes", None)
    data.setdefault("mensagem_whatsapp", "")
    data.setdefault("custo_interno_total", 0.0)
    data.setdefault("margem_bruta", _money(data.get("total_mao_de_obra", 0) - data.get("custo_interno_total", 0)))
    data.setdefault("margem_percentual", _money(data["margem_bruta"] / data["total_mao_de_obra"] * 100) if data.get("total_mao_de_obra", 0) else 0.0)
    for item in data.get("itens", []):
        item.setdefault("custo_interno", 0.0)
        item.setdefault("margem_bruta", _money(item.get("subtotal", 0) - item.get("custo_peca", 0) - item.get("custo_interno", 0)))
    return QuoteResponse.model_validate(data)


def _raise_firestore_error(operation: str, error: Exception) -> None:
    logger.exception("Erro ao %s no Firestore", operation)
    raise HTTPException(
        status_code=500,
        detail=f"Não foi possível {operation}.",
    ) from error


@router.post("", response_model=QuoteResponse, status_code=201)
def create_quote(quote: QuoteCreate) -> QuoteResponse:
    """Calculate, persist and return a new quote."""

    database = _require_db()
    (
        response_items,
        _labor_values,
        total_labor,
        total_parts,
        gross_subtotal,
        total,
        message,
        total_internal_cost,
    ) = _calculate_quote(quote)
    created_at = _utc_now()
    document = database.collection(COLLECTION_NAME).document()

    payload = _quote_payload(
        quote,
        response_items,
        total_labor,
        total_parts,
        gross_subtotal,
        total,
        message,
        QuoteStatus.RASCUNHO.value,
        created_at,
        total_internal_cost,
    )

    try:
        document.set(payload)
        return QuoteResponse.model_validate(
            {**payload, "id": document.id},
        )
    except Exception as error:
        _raise_firestore_error("criar o orçamento", error)


@router.get("", response_model=list[QuoteResponse])
def list_quotes() -> list[QuoteResponse]:
    """List quote history ordered from newest to oldest."""

    database = _require_db()
    try:
        quotes = [
            _quote_from_snapshot(snapshot)
            for snapshot in database.collection(COLLECTION_NAME).stream()
        ]
        return sorted(quotes, key=lambda quote: quote.criado_em, reverse=True)
    except HTTPException:
        raise
    except Exception as error:
        _raise_firestore_error("listar os orçamentos", error)


@router.get("/{quote_id}", response_model=QuoteResponse)
def get_quote(quote_id: str) -> QuoteResponse:
    """Return a single quote by its Firestore document ID."""

    database = _require_db()
    document = database.collection(COLLECTION_NAME).document(quote_id)

    try:
        snapshot = document.get()
        if not snapshot.exists:
            raise HTTPException(status_code=404, detail="Orçamento não encontrado.")
        return _quote_from_snapshot(snapshot)
    except HTTPException:
        raise
    except Exception as error:
        _raise_firestore_error("buscar o orçamento", error)


@router.put("/{quote_id}", response_model=QuoteResponse)
def update_quote(quote_id: str, quote: QuoteCreate) -> QuoteResponse:
    """Recalculate and replace an existing quote while preserving its ID."""

    database = _require_db()
    document = database.collection(COLLECTION_NAME).document(quote_id)

    try:
        snapshot = document.get()
        if not snapshot.exists:
            raise HTTPException(status_code=404, detail="Orçamento não encontrado.")

        current_data = snapshot.to_dict() or {}
        (
            response_items,
            _labor_values,
            total_labor,
            total_parts,
            gross_subtotal,
            total,
            message,
            total_internal_cost,
        ) = _calculate_quote(quote)
        created_at = current_data.get(
            "criado_em",
            getattr(snapshot, "create_time", _utc_now()),
        )
        updated_at = _utc_now()
        payload = _quote_payload(
            quote,
            response_items,
            total_labor,
            total_parts,
            gross_subtotal,
            total,
            message,
            current_data.get("status", QuoteStatus.RASCUNHO.value),
            created_at,
            total_internal_cost,
            updated_at,
        )
        document.set(payload)
        return QuoteResponse.model_validate({**payload, "id": document.id})
    except HTTPException:
        raise
    except Exception as error:
        _raise_firestore_error("atualizar o orçamento", error)


@router.delete("/{quote_id}")
def delete_quote(quote_id: str) -> dict[str, object]:
    """Delete an existing quote from Firestore."""

    database = _require_db()
    document = database.collection(COLLECTION_NAME).document(quote_id)

    try:
        snapshot = document.get()
        if not snapshot.exists:
            raise HTTPException(status_code=404, detail="Orçamento não encontrado.")

        document.delete()
        return {
            "success": True,
            "message": "Orçamento removido com sucesso",
        }
    except HTTPException:
        raise
    except Exception as error:
        _raise_firestore_error("remover o orçamento", error)


@router.patch("/{quote_id}/status", response_model=QuoteResponse)
def update_quote_status(
    quote_id: str,
    status_update: QuoteStatusUpdate,
) -> QuoteResponse:
    """Update only the status of an existing quote."""

    database = _require_db()
    document = database.collection(COLLECTION_NAME).document(quote_id)

    try:
        snapshot = document.get()
        if not snapshot.exists:
            raise HTTPException(status_code=404, detail="Orçamento não encontrado.")

        document.update({"status": status_update.status.value})
        data = snapshot.to_dict() or {}
        data["id"] = snapshot.id
        data["status"] = status_update.status.value
        data.setdefault("criado_em", getattr(snapshot, "create_time", _utc_now()))
        data.setdefault("mensagem_whatsapp", "")
        data.setdefault("custo_interno_total", 0.0)
        data.setdefault("margem_bruta", _money(data.get("total_mao_de_obra", 0) - data.get("custo_interno_total", 0)))
        data.setdefault("margem_percentual", _money(data["margem_bruta"] / data["total_mao_de_obra"] * 100) if data.get("total_mao_de_obra", 0) else 0.0)
        for item in data.get("itens", []):
            item.setdefault("custo_interno", 0.0)
            item.setdefault("margem_bruta", _money(item.get("subtotal", 0) - item.get("custo_peca", 0) - item.get("custo_interno", 0)))
        return QuoteResponse.model_validate(data)
    except HTTPException:
        raise
    except Exception as error:
        _raise_firestore_error("atualizar o status do orçamento", error)
