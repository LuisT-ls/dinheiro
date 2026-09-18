"""AI-assisted service suggestions for incoming client requests."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from ..config import db
from ..schemas import AIInterpretation, AIRequest
from ..rate_limit import enforce_rate_limit
from ..security import require_authenticated_user
from ..services.gemini_service import interpretar_pedido_cliente


logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/ai",
    tags=["IA"],
    dependencies=[Depends(require_authenticated_user)],
)
COLLECTION_NAME = "services"


def _require_db():
    if db is None:
        raise HTTPException(
            status_code=503,
            detail="Firestore não está configurado para buscar o catálogo de serviços.",
        )
    return db


def _active_services(database) -> list[dict]:
    catalogo: list[dict] = []
    for snapshot in database.collection(COLLECTION_NAME).stream():
        data = snapshot.to_dict() or {}
        if data.get("ativo", True) is False:
            continue
        data["service_id"] = snapshot.id
        catalogo.append(data)
    return catalogo


@router.post("/parse-request", response_model=AIInterpretation)
def parse_request(request: Request, payload: AIRequest) -> AIInterpretation:
    """Parse a free-form client message and suggest catalog services."""

    enforce_rate_limit(request, "ai-parse-request", limit=20, window_seconds=60)
    database = _require_db()
    try:
        catalogo = _active_services(database)
    except Exception as error:
        logger.exception("Erro ao buscar o catálogo para interpretação de IA.")
        raise HTTPException(
            status_code=500,
            detail="Não foi possível buscar o catálogo de serviços.",
        ) from error

    try:
        return AIInterpretation.model_validate(
            interpretar_pedido_cliente(payload.mensagem, catalogo),
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        logger.exception("Erro ao interpretar o pedido do cliente.")
        raise HTTPException(
            status_code=500,
            detail="Não foi possível interpretar o pedido do cliente.",
        ) from error
