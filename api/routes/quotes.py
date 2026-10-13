"""Quote calculation, persistence and history routes."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from ..config import db
from ..schemas import (
    QuoteCreate,
    QuoteItemInput,
    QuoteItemResponse,
    QuoteRevisionAction,
    QuoteRevisionResponse,
    QuoteResponse,
    QuoteStatus,
    QuoteStatusUpdate,
)
from ..security import make_share_token, require_authenticated_user, verify_share_token


logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/quotes",
    tags=["Orçamentos"],
    dependencies=[Depends(require_authenticated_user)],
)
public_router = APIRouter(prefix="/quotes/public", tags=["Orçamentos públicos"])
history_router = APIRouter(
    prefix="/quote-history",
    tags=["Histórico de alterações"],
    dependencies=[Depends(require_authenticated_user)],
)
COLLECTION_NAME = "quotes"
REVISION_COLLECTION_NAME = "quote_revisions"


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
    return _quote_from_data(
        snapshot.to_dict() or {},
        snapshot.id,
        getattr(snapshot, "create_time", None),
    )


def _quote_from_data(
    raw_data: dict,
    quote_id: str,
    fallback_created_at: datetime | None = None,
) -> QuoteResponse:
    data = dict(raw_data)
    data["id"] = quote_id
    data["share_token"] = make_share_token(quote_id) or None
    data.setdefault("status", QuoteStatus.RASCUNHO.value)
    data.setdefault("criado_em", fallback_created_at or _utc_now())
    data.setdefault("observacoes", None)
    data.setdefault("mensagem_whatsapp", "")
    data.setdefault("custo_interno_total", 0.0)
    data.setdefault("margem_bruta", _money(data.get("total_mao_de_obra", 0) - data.get("custo_interno_total", 0)))
    data.setdefault("margem_percentual", _money(data["margem_bruta"] / data["total_mao_de_obra"] * 100) if data.get("total_mao_de_obra", 0) else 0.0)
    data["itens"] = [dict(item) for item in data.get("itens", [])]
    for item in data["itens"]:
        item.setdefault("custo_interno", 0.0)
        item.setdefault("margem_bruta", _money(item.get("subtotal", 0) - item.get("custo_peca", 0) - item.get("custo_interno", 0)))
    return QuoteResponse.model_validate(data)


def _revision_payload(
    quote_id: str,
    action: QuoteRevisionAction,
    quote_data: dict,
    changed_at: datetime,
) -> dict:
    return {
        "quote_id": quote_id,
        "acao": action.value,
        "alterado_em": changed_at,
        "snapshot": quote_data,
    }


def _revision_from_snapshot(snapshot) -> QuoteRevisionResponse:
    data = snapshot.to_dict() or {}
    quote_data = data.get("snapshot") or {}
    quote = _quote_from_data(quote_data, data.get("quote_id", ""))
    return QuoteRevisionResponse(
        id=snapshot.id,
        quote_id=data.get("quote_id", ""),
        acao=data.get("acao", QuoteRevisionAction.EDICAO.value),
        alterado_em=data.get("alterado_em", _utc_now()),
        cliente=quote.cliente,
        valor_total=quote.valor_total,
        status=quote.status,
        quantidade_itens=len(quote.itens),
    )


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
            {
                **payload,
                "id": document.id,
                "share_token": make_share_token(document.id) or None,
            },
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
        revision_document = database.collection(REVISION_COLLECTION_NAME).document()
        batch = database.batch()
        batch.set(document, payload)
        batch.set(
            revision_document,
            _revision_payload(
                quote_id,
                QuoteRevisionAction.EDICAO,
                current_data,
                updated_at,
            ),
        )
        batch.commit()
        return QuoteResponse.model_validate(
            {
                **payload,
                "id": document.id,
                "share_token": make_share_token(document.id) or None,
            },
        )
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

        deleted_at = _utc_now()
        revision_document = database.collection(REVISION_COLLECTION_NAME).document()
        batch = database.batch()
        batch.set(
            revision_document,
            _revision_payload(
                quote_id,
                QuoteRevisionAction.EXCLUSAO,
                snapshot.to_dict() or {},
                deleted_at,
            ),
        )
        batch.delete(document)
        batch.commit()
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

        current_data = snapshot.to_dict() or {}
        if current_data.get("status") == status_update.status.value:
            return _quote_from_data(current_data, snapshot.id)

        changed_at = _utc_now()
        updated_data = dict(current_data)
        updated_data["status"] = status_update.status.value
        updated_data["atualizado_em"] = changed_at
        revision_document = database.collection(REVISION_COLLECTION_NAME).document()
        batch = database.batch()
        batch.set(document, updated_data)
        batch.set(
            revision_document,
            _revision_payload(
                quote_id,
                QuoteRevisionAction.STATUS,
                current_data,
                changed_at,
            ),
        )
        batch.commit()
        return _quote_from_data(updated_data, snapshot.id)
    except HTTPException:
        raise
    except Exception as error:
        _raise_firestore_error("atualizar o status do orçamento", error)


def _get_public_quote_snapshot(quote_id: str, token: str):
    if not verify_share_token(quote_id, token):
        raise HTTPException(
            status_code=404,
            detail="Link público inválido ou expirado.",
        )

    database = _require_db()
    document = database.collection(COLLECTION_NAME).document(quote_id)
    snapshot = document.get()
    if not snapshot.exists:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado.")
    return document, snapshot


def _public_quote_from_snapshot(snapshot) -> QuoteResponse:
    """Hide internal costs, margins and bearer tokens from client-facing links."""

    quote = _quote_from_snapshot(snapshot)
    data = quote.model_dump(mode="json")
    data["custo_interno_total"] = 0.0
    data["margem_bruta"] = 0.0
    data["margem_percentual"] = 0.0
    data["share_token"] = None
    for item in data.get("itens", []):
        item["custo_interno"] = 0.0
        item["margem_bruta"] = 0.0
    return QuoteResponse.model_validate(data)


@public_router.get("/{quote_id}", response_model=QuoteResponse)
def get_public_quote(
    quote_id: str,
    token: str = Query(..., min_length=20),
) -> QuoteResponse:
    """Read-only quote view used by a signed client-sharing link."""

    try:
        _document, snapshot = _get_public_quote_snapshot(quote_id, token)
        return _public_quote_from_snapshot(snapshot)
    except HTTPException:
        raise
    except Exception as error:
        _raise_firestore_error("buscar o orçamento compartilhado", error)


@public_router.patch("/{quote_id}/status", response_model=QuoteResponse)
def update_public_quote_status(
    quote_id: str,
    status_update: QuoteStatusUpdate,
    token: str = Query(..., min_length=20),
) -> QuoteResponse:
    """Allow a recipient to accept or decline a quote from its share link."""

    if status_update.status not in {QuoteStatus.APROVADO, QuoteStatus.RECUSADO}:
        raise HTTPException(
            status_code=400,
            detail="O cliente só pode aprovar ou recusar o orçamento por este link.",
        )

    try:
        document, snapshot = _get_public_quote_snapshot(quote_id, token)
        database = _require_db()
        current_data = snapshot.to_dict() or {}
        changed_at = _utc_now()
        updated_data = dict(current_data)
        updated_data["status"] = status_update.status.value
        updated_data["atualizado_em"] = changed_at
        revision_document = database.collection(REVISION_COLLECTION_NAME).document()
        batch = database.batch()
        batch.set(document, updated_data)
        batch.set(
            revision_document,
            _revision_payload(
                quote_id,
                QuoteRevisionAction.STATUS,
                current_data,
                changed_at,
            ),
        )
        batch.commit()
        return _public_quote_from_snapshot(document.get())
    except HTTPException:
        raise
    except Exception as error:
        _raise_firestore_error("atualizar o status do orçamento compartilhado", error)


@router.get("/{quote_id}/history", response_model=list[QuoteRevisionResponse])
def list_quote_history(quote_id: str) -> list[QuoteRevisionResponse]:
    """List the saved revisions for one quote, newest first."""

    database = _require_db()
    try:
        revisions = [
            _revision_from_snapshot(snapshot)
            for snapshot in database.collection(REVISION_COLLECTION_NAME)
            .where("quote_id", "==", quote_id)
            .stream()
        ]
        return sorted(revisions, key=lambda revision: revision.alterado_em, reverse=True)
    except Exception as error:
        _raise_firestore_error("listar o histórico do orçamento", error)


@router.post("/{quote_id}/restore/{revision_id}", response_model=QuoteResponse)
def restore_quote(quote_id: str, revision_id: str) -> QuoteResponse:
    """Restore a previous revision, including a quote that was deleted."""

    database = _require_db()
    quote_document = database.collection(COLLECTION_NAME).document(quote_id)
    revision_document = database.collection(REVISION_COLLECTION_NAME).document(revision_id)

    try:
        revision_snapshot = revision_document.get()
        if not revision_snapshot.exists:
            raise HTTPException(status_code=404, detail="Versão do orçamento não encontrada.")

        revision_data = revision_snapshot.to_dict() or {}
        if revision_data.get("quote_id") != quote_id:
            raise HTTPException(status_code=404, detail="Versão do orçamento não encontrada.")

        previous_snapshot = quote_document.get()
        restore_data = dict(revision_data.get("snapshot") or {})
        if not restore_data:
            raise HTTPException(status_code=422, detail="A versão selecionada não possui dados para restauração.")

        restored_at = _utc_now()
        restore_data["atualizado_em"] = restored_at
        audit_snapshot = previous_snapshot.to_dict() if previous_snapshot.exists else restore_data
        new_revision_document = database.collection(REVISION_COLLECTION_NAME).document()
        batch = database.batch()
        batch.set(quote_document, restore_data)
        batch.set(
            new_revision_document,
            _revision_payload(
                quote_id,
                QuoteRevisionAction.RESTAURACAO,
                audit_snapshot or {},
                restored_at,
            ),
        )
        batch.commit()
        return _quote_from_data(restore_data, quote_id)
    except HTTPException:
        raise
    except Exception as error:
        _raise_firestore_error("restaurar o orçamento", error)


@history_router.get("", response_model=list[QuoteRevisionResponse])
def list_all_quote_history(
    quote_id: str | None = Query(default=None),
) -> list[QuoteRevisionResponse]:
    """List the audit trail, including revisions of deleted quotes."""

    database = _require_db()
    try:
        query = database.collection(REVISION_COLLECTION_NAME)
        if quote_id:
            query = query.where("quote_id", "==", quote_id)
        revisions = [_revision_from_snapshot(snapshot) for snapshot in query.stream()]
        return sorted(revisions, key=lambda revision: revision.alterado_em, reverse=True)
    except Exception as error:
        _raise_firestore_error("listar o histórico de alterações", error)
