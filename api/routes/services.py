"""CRUD routes for the Firestore services catalog."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from ..config import db
from ..schemas import (
    PricingType,
    ServiceCategory,
    ServiceCreate,
    ServiceResponse,
)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/services", tags=["Serviços"])
COLLECTION_NAME = "services"


DEFAULT_SERVICES = (
    ServiceCreate(
        nome="Limpeza preventiva",
        categoria=ServiceCategory.HARDWARE,
        tipo_cobranca=PricingType.FIXO,
        valor_base=150.0,
        descricao_padrao="Limpeza interna, remoção de poeira e revisão básica.",
    ),
    ServiceCreate(
        nome="Troca de SSD (mão de obra)",
        categoria=ServiceCategory.HARDWARE,
        tipo_cobranca=PricingType.MISTO,
        valor_base=120.0,
        permite_peca=True,
        descricao_padrao="Instalação do SSD e configuração inicial do sistema.",
    ),
    ServiceCreate(
        nome="Upgrade de memória RAM (mão de obra)",
        categoria=ServiceCategory.HARDWARE,
        tipo_cobranca=PricingType.MISTO,
        valor_base=100.0,
        permite_peca=True,
        descricao_padrao="Instalação e teste do novo módulo de memória.",
    ),
    ServiceCreate(
        nome="Formatação e configuração",
        categoria=ServiceCategory.HARDWARE,
        tipo_cobranca=PricingType.FIXO,
        valor_base=180.0,
        descricao_padrao="Formatação, instalação do sistema e configurações essenciais.",
    ),
    ServiceCreate(
        nome="Landing Page Simples",
        categoria=ServiceCategory.DEV,
        tipo_cobranca=PricingType.FIXO,
        valor_base=1500.0,
        descricao_padrao="Landing page responsiva com publicação e configuração básica.",
    ),
    ServiceCreate(
        nome="Desenvolvimento sob medida (hora)",
        categoria=ServiceCategory.DEV,
        tipo_cobranca=PricingType.HORA,
        valor_base=150.0,
        descricao_padrao="Desenvolvimento de funcionalidades conforme escopo aprovado.",
    ),
    ServiceCreate(
        nome="Configuração de infraestrutura",
        categoria=ServiceCategory.INFRA,
        tipo_cobranca=PricingType.HORA,
        valor_base=180.0,
        descricao_padrao="Configuração de ambiente, deploy e serviços de infraestrutura.",
    ),
)


def _require_db():
    if db is None:
        raise HTTPException(
            status_code=500,
            detail="Firestore não está configurado para esta aplicação.",
        )
    return db


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _service_from_snapshot(snapshot) -> ServiceResponse:
    data = snapshot.to_dict() or {}
    data["id"] = snapshot.id
    data.setdefault("criado_em", _utc_now())
    return ServiceResponse.model_validate(data)


def _sort_services(services: list[ServiceResponse]) -> list[ServiceResponse]:
    return sorted(
        services,
        key=lambda service: (service.nome.casefold(), service.categoria.value),
    )


def _raise_firestore_error(operation: str, error: Exception) -> None:
    logger.exception("Erro ao %s no Firestore", operation)
    raise HTTPException(
        status_code=500,
        detail=f"Não foi possível {operation}.",
    ) from error


@router.get("", response_model=list[ServiceResponse])
def list_services() -> list[ServiceResponse]:
    """List all catalog services ordered by name and category."""

    database = _require_db()
    try:
        services = [
            _service_from_snapshot(snapshot)
            for snapshot in database.collection(COLLECTION_NAME).stream()
        ]
        return _sort_services(services)
    except HTTPException:
        raise
    except Exception as error:
        _raise_firestore_error("listar os serviços", error)


@router.post("", response_model=ServiceResponse, status_code=201)
def create_service(service: ServiceCreate) -> ServiceResponse:
    """Create a service in the catalog."""

    database = _require_db()
    created_at = _utc_now()
    document = database.collection(COLLECTION_NAME).document()
    payload = service.model_dump(mode="json")
    payload["criado_em"] = created_at

    try:
        document.set(payload)
        return ServiceResponse.model_validate(
            {**payload, "id": document.id},
        )
    except Exception as error:
        _raise_firestore_error("criar o serviço", error)


@router.post("/seed", response_model=list[ServiceResponse])
def seed_services() -> list[ServiceResponse]:
    """Populate the default catalog only when the collection is empty."""

    database = _require_db()
    collection = database.collection(COLLECTION_NAME)

    try:
        existing = [
            _service_from_snapshot(snapshot)
            for snapshot in collection.stream()
        ]
        if existing:
            return _sort_services(existing)

        batch = database.batch()
        created_at = _utc_now()
        references = []

        for service in DEFAULT_SERVICES:
            document = collection.document()
            payload = service.model_dump(mode="json")
            payload["criado_em"] = created_at
            batch.set(document, payload)
            references.append((document, payload))

        batch.commit()

        return _sort_services(
            [
                ServiceResponse.model_validate(
                    {**payload, "id": document.id},
                )
                for document, payload in references
            ],
        )
    except HTTPException:
        raise
    except Exception as error:
        _raise_firestore_error("popular o catálogo de serviços", error)


@router.put("/{service_id}", response_model=ServiceResponse)
def update_service(service_id: str, service: ServiceCreate) -> ServiceResponse:
    """Replace an existing catalog service."""

    database = _require_db()
    document = database.collection(COLLECTION_NAME).document(service_id)

    try:
        snapshot = document.get()
        if not snapshot.exists:
            raise HTTPException(status_code=404, detail="Serviço não encontrado.")

        current_data = snapshot.to_dict() or {}
        payload = service.model_dump(mode="json")
        payload["criado_em"] = current_data.get("criado_em", _utc_now())
        document.set(payload)
        return ServiceResponse.model_validate(
            {**payload, "id": document.id},
        )
    except HTTPException:
        raise
    except Exception as error:
        _raise_firestore_error("atualizar o serviço", error)


@router.delete("/{service_id}")
def delete_service(service_id: str) -> dict[str, str]:
    """Delete an existing catalog service."""

    database = _require_db()
    document = database.collection(COLLECTION_NAME).document(service_id)

    try:
        snapshot = document.get()
        if not snapshot.exists:
            raise HTTPException(status_code=404, detail="Serviço não encontrado.")

        document.delete()
        return {"message": "Serviço removido com sucesso."}
    except HTTPException:
        raise
    except Exception as error:
        _raise_firestore_error("remover o serviço", error)
