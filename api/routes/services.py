"""CRUD routes for the Firestore services catalog."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

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
        nome="Landing Page Simples",
        categoria=ServiceCategory.DEV,
        tipo_cobranca=PricingType.FIXO,
        valor_base=1500.0,
        descricao_padrao="Landing page responsiva com publicação e configuração básica.",
    ),
    ServiceCreate(
        nome="Landing Page Avançada",
        categoria=ServiceCategory.DEV,
        tipo_cobranca=PricingType.FIXO,
        valor_base=3500.0,
        descricao_padrao="Landing page avançada com integrações, animações e otimização de conversão.",
    ),
    ServiceCreate(
        nome="Site Institucional",
        categoria=ServiceCategory.DEV,
        tipo_cobranca=PricingType.FIXO,
        valor_base=3000.0,
        descricao_padrao="Site institucional responsivo com páginas essenciais e publicação.",
    ),
    ServiceCreate(
        nome="Feature / Módulo Web",
        categoria=ServiceCategory.DEV,
        tipo_cobranca=PricingType.MISTO,
        valor_base=1200.0,
        descricao_padrao="Desenvolvimento de uma feature ou módulo web conforme escopo aprovado.",
    ),
    ServiceCreate(
        nome="MVP Sistema Web / SaaS",
        categoria=ServiceCategory.DEV,
        tipo_cobranca=PricingType.FIXO,
        valor_base=9000.0,
        descricao_padrao="MVP de sistema web ou SaaS com escopo, autenticação e fluxo principal.",
    ),
    ServiceCreate(
        nome="Aplicativo Mobile (MVP)",
        categoria=ServiceCategory.DEV,
        tipo_cobranca=PricingType.FIXO,
        valor_base=12000.0,
        descricao_padrao="MVP de aplicativo mobile com as funcionalidades essenciais do produto.",
    ),
    ServiceCreate(
        nome="Desenvolvimento sob Medida / Hora",
        categoria=ServiceCategory.DEV,
        tipo_cobranca=PricingType.HORA,
        valor_base=100.0,
        descricao_padrao="Desenvolvimento sob medida conforme demanda e escopo aprovado.",
    ),
    ServiceCreate(
        nome="Manutenção Básica - Sites / LPs",
        categoria=ServiceCategory.DEV,
        tipo_cobranca=PricingType.FIXO,
        valor_base=450.0,
        descricao_padrao="Até 3h/mês, SLA 48h, SSL, backups e uptime",
    ),
    ServiceCreate(
        nome="Manutenção Intermediária - Portais / E-commerce",
        categoria=ServiceCategory.DEV,
        tipo_cobranca=PricingType.FIXO,
        valor_base=1100.0,
        descricao_padrao="Até 8h/mês, SLA 24h, preventiva, banco de dados e APIs",
    ),
    ServiceCreate(
        nome="Manutenção Avançada - SaaS / Web App",
        categoria=ServiceCategory.DEV,
        tipo_cobranca=PricingType.FIXO,
        valor_base=2500.0,
        descricao_padrao="Até 20h/mês, SLA 12h, monitoramento Sentry, correções e deploys",
    ),
    ServiceCreate(
        nome="Limpeza Preventiva + Troca de Pasta Térmica",
        categoria=ServiceCategory.HARDWARE,
        tipo_cobranca=PricingType.FIXO,
        valor_base=150.0,
        descricao_padrao="Limpeza interna, remoção de poeira e troca de pasta térmica.",
    ),
    ServiceCreate(
        nome="Troca de SSD / Armazenamento",
        categoria=ServiceCategory.HARDWARE,
        tipo_cobranca=PricingType.MISTO,
        valor_base=120.0,
        permite_peca=True,
        descricao_padrao="Instalação do SSD ou armazenamento e configuração inicial do sistema.",
    ),
    ServiceCreate(
        nome="Upgrade de Memória RAM",
        categoria=ServiceCategory.HARDWARE,
        tipo_cobranca=PricingType.MISTO,
        valor_base=80.0,
        permite_peca=True,
        descricao_padrao="Instalação e teste do novo módulo de memória.",
    ),
    ServiceCreate(
        nome="Formatação + Instalação de Sistema",
        categoria=ServiceCategory.HARDWARE,
        tipo_cobranca=PricingType.FIXO,
        valor_base=130.0,
        descricao_padrao="Formatação, instalação do sistema e configurações essenciais.",
    ),
)


LEGACY_SERVICE_ALIASES = {
    "Limpeza Preventiva + Troca de Pasta Térmica": {
        "Limpeza preventiva",
    },
    "Troca de SSD / Armazenamento": {
        "Troca de SSD (mão de obra)",
    },
    "Upgrade de Memória RAM": {
        "Upgrade de memória RAM (mão de obra)",
    },
    "Formatação + Instalação de Sistema": {
        "Formatação e configuração",
    },
    "Desenvolvimento sob Medida / Hora": {
        "Desenvolvimento sob medida (hora)",
    },
}


LEGACY_DEFAULT_NAMES = {
    "Configuração de infraestrutura",
}


def _normalize_name(value: str) -> str:
    return " ".join(value.casefold().split())


def _service_payload(service: ServiceCreate, created_at: datetime) -> dict:
    payload = service.model_dump(mode="json")
    payload["criado_em"] = created_at
    return payload


def _existing_service_matches(service: ServiceCreate, snapshot) -> bool:
    current_name = snapshot.to_dict().get("nome", "")
    accepted_names = {service.nome, *LEGACY_SERVICE_ALIASES.get(service.nome, set())}
    return _normalize_name(current_name) in {
        _normalize_name(name) for name in accepted_names
    }


def _is_legacy_default(snapshot) -> bool:
    current_name = snapshot.to_dict().get("nome", "")
    return _normalize_name(current_name) in {
        _normalize_name(name) for name in LEGACY_DEFAULT_NAMES
    }


def _seed_catalog(database, existing_snapshots: list, force: bool) -> list[ServiceResponse]:
    collection = database.collection(COLLECTION_NAME)
    batch = database.batch()
    created_at = _utc_now()
    references = []
    matched_ids = set()

    for service in DEFAULT_SERVICES:
        matching_snapshot = next(
            (
                snapshot
                for snapshot in existing_snapshots
                if snapshot.id not in matched_ids
                and _existing_service_matches(service, snapshot)
            ),
            None,
        )
        document = collection.document(matching_snapshot.id) if matching_snapshot else collection.document()
        current_data = matching_snapshot.to_dict() if matching_snapshot else {}
        payload = _service_payload(
            service,
            current_data.get("criado_em", created_at),
        )
        batch.set(document, payload)
        references.append((document, payload))
        if matching_snapshot:
            matched_ids.add(matching_snapshot.id)

    if force:
        for snapshot in existing_snapshots:
            if snapshot.id in matched_ids:
                continue
            if _is_legacy_default(snapshot):
                batch.delete(collection.document(snapshot.id))

    batch.commit()

    if force:
        return _sort_services(
            [
                _service_from_snapshot(snapshot)
                for snapshot in collection.stream()
            ],
        )

    return _sort_services(
        [
            ServiceResponse.model_validate(
                {**payload, "id": document.id},
            )
            for document, payload in references
        ],
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
def seed_services(
    force: bool = Query(
        default=False,
        description="Atualiza o catálogo oficial mesmo quando já existem serviços.",
    ),
) -> list[ServiceResponse]:
    """Populate or synchronize the official catalog."""

    database = _require_db()
    collection = database.collection(COLLECTION_NAME)

    try:
        existing_snapshots = list(collection.stream())
        existing = [
            _service_from_snapshot(snapshot)
            for snapshot in existing_snapshots
        ]
        if existing and not force:
            return _sort_services(existing)

        return _seed_catalog(database, existing_snapshots, force=force)
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
