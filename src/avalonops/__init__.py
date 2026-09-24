"""SDK oficial da AvalonOps — wrapper fino sobre o SDK da OpenAI.

Spec: 2026-09-24-sdks-avalon-design.md (RN-SDK-01..07).
"""
from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

from openai import OpenAI

CABECALHO_REQUEST_ID = "x-avalon-request-id"

__all__ = ["CABECALHO_REQUEST_ID", "Avalon", "raiz_para_v1"]


def raiz_para_v1(raiz: str) -> str:
    """A raiz do gateway (a MESMA env AVALON_BASE_URL do tutorial) vira a
    base /v1 — sem duplicar quando já termina em /v1 (RN-SDK-02). Nenhuma
    URL default: o produto é auto-hospedado."""
    sem_barra = raiz.rstrip("/")
    return sem_barra if sem_barra.endswith("/v1") else sem_barra + "/v1"


class Avalon:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        chave = api_key or os.environ.get("AVALON_API_KEY")
        if not chave:
            raise ValueError("api_key ausente: passe api_key= ou defina a env AVALON_API_KEY.")
        raiz = base_url or os.environ.get("AVALON_BASE_URL")
        if not raiz:
            raise ValueError(
                "base_url ausente: passe base_url= ou defina a env AVALON_BASE_URL "
                "(a raiz do gateway, sem /v1)."
            )
        self._cliente = OpenAI(api_key=chave, base_url=raiz_para_v1(raiz))
        self._metadata_base: dict[str, Any] = dict(metadata or {})
