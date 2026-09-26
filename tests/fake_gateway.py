"""Fake HTTP real do gateway (RN-SDK-06): porta efêmera, grava a última
requisição, responde formas fixas. NUNCA mock do transporte. Erro na forma
real do núcleo: {"erro": {"codigo", "mensagem"}}; toda resposta carrega
x-avalon-request-id."""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

REQUEST_ID_DO_FAKE = "11111111-2222-4333-8444-555555555555"
UUID_INEXISTENTE = "00000000-0000-4000-8000-000000000404"
REQUEST_ID_ERRO_500 = "00000000-0000-4000-8000-000000000500"

# Mensagem genérica para politicaDeForma (RN-FE-01/02/05): valor_invalido,
# peso_invalido, metadata_invalida devem devolver isso ao cliente; o motivo
# fica apenas no log do servidor.
MENSAGEM_GENERICA_POLICIA_DE_FORMA = "A requisição não está no formato aceito pela sua organização."

CHAT_COMPLETION = {
    "id": "chatcmpl-fake", "object": "chat.completion", "created": 1727180000, "model": "gpt-4",
    "choices": [{"index": 0, "message": {"role": "assistant", "content": "olá"}, "finish_reason": "stop"}],
    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
}

EMBEDDINGS = {
    "object": "list",
    "data": [{"object": "embedding", "index": 0, "embedding": [0.1, 0.2]}],
    "model": "text-embedding-3-small", "usage": {"prompt_tokens": 1, "total_tokens": 1},
}

MODELS = {
    "object": "list",
    "data": [{"id": "@teste/gpt-4", "object": "model", "created": 1727180000, "owned_by": "teste",
              "rotulo": None, "modelo": "gpt-4", "providerSlug": "openai"}],
}


def _chunk(conteudo: str) -> dict[str, Any]:
    return {
        "id": "chatcmpl-fake", "object": "chat.completion.chunk", "created": 1727180000,
        "model": "gpt-4",
        "choices": [{"index": 0, "delta": {"content": conteudo}, "finish_reason": None}],
    }


def _erro(codigo: str, mensagem: str) -> dict[str, Any]:
    return {"erro": {"codigo": codigo, "mensagem": mensagem}}


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *args: Any) -> None:  # silencia o stderr do CI
        pass

    def _gravar(self, corpo: dict[str, Any] | None) -> None:
        self.server.ultima = {  # type: ignore[attr-defined]
            "metodo": self.command,
            "rota": self.path,
            "headers": {k.lower(): v for k, v in self.headers.items()},
            "corpo": corpo,
        }

    def _responder(self, status: int, corpo: dict[str, Any]) -> None:
        dados = json.dumps(corpo).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("x-avalon-request-id", REQUEST_ID_DO_FAKE)
        self.send_header("content-length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def _responder_stream(self) -> None:
        self.send_response(200)
        self.send_header("content-type", "text/event-stream")
        self.send_header("x-avalon-request-id", REQUEST_ID_DO_FAKE)
        self.end_headers()
        for pedaco in ("o", "lá"):
            self.wfile.write(f"data: {json.dumps(_chunk(pedaco))}\n\n".encode())
        self.wfile.write(b"data: [DONE]\n\n")

    def do_GET(self) -> None:
        self._gravar(None)
        if self.path == "/v1/models":
            return self._responder(200, MODELS)
        return self._responder(404, _erro("rota_inexistente", "Recurso não encontrado."))

    def do_POST(self) -> None:
        tamanho = int(self.headers.get("content-length") or 0)
        corpo: dict[str, Any] = json.loads(self.rfile.read(tamanho) or b"{}")
        self._gravar(corpo)

        if self.path == "/v1/chat/completions":
            if str(corpo.get("model", "")).startswith("@nega/"):
                return self._responder(403, _erro("modelo_nao_permitido", "Você não tem permissão para esta ação."))
            if corpo.get("stream") is True:
                return self._responder_stream()
            return self._responder(200, CHAT_COMPLETION)
        if self.path == "/v1/embeddings":
            return self._responder(200, EMBEDDINGS)
        if self.path == "/v1/feedback":
            request_id = str(corpo.get("request_id", ""))
            valor = corpo.get("valor")
            if request_id == REQUEST_ID_ERRO_500:
                # RN-SDK-05/F5: conta só as chegadas do sentinela de retry —
                # não polui com os outros testes de feedback do mesmo fake.
                self.server.contagem_feedback_erro_500 += 1  # type: ignore[attr-defined]
                return self._responder(500, _erro("erro_interno", "Falha interna simulada."))
            if request_id == UUID_INEXISTENTE:
                return self._responder(404, _erro("nao_encontrado", "Recurso não encontrado."))
            # Literais copiados de governanca-plataforma/src/feedback/validacao.ts
            # (RN-FE-09) — fidelidade byte a byte com o gateway real, não só a
            # faixa: `valor` é INTEIRO (bool é subclasse de int em Python, por
            # isso a exclusão explícita), `peso` tem teto em 1 (não só piso em 0).
            if not isinstance(valor, int) or isinstance(valor, bool) or valor < -10 or valor > 10:
                # politicaDeForma(codigo, motivo) — genérica ao cliente
                return self._responder(
                    400, _erro("valor_invalido", MENSAGEM_GENERICA_POLICIA_DE_FORMA)
                )
            peso_bruto = corpo.get("peso")
            peso = 1 if peso_bruto is None else peso_bruto
            if not isinstance(peso, (int, float)) or isinstance(peso, bool) or peso < 0 or peso > 1:
                # politicaDeForma(codigo, motivo) — genérica ao cliente
                return self._responder(
                    400, _erro("peso_invalido", MENSAGEM_GENERICA_POLICIA_DE_FORMA)
                )
            return self._responder(201, {"id": "fb-1", "logId": request_id, "valor": valor, "peso": peso})
        return self._responder(404, _erro("rota_inexistente", "Recurso não encontrado."))


class FakeGateway:
    def __init__(self) -> None:
        self._servidor = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self._servidor.ultima = None  # type: ignore[attr-defined]
        self._servidor.contagem_feedback_erro_500 = 0  # type: ignore[attr-defined]
        self._thread = threading.Thread(target=self._servidor.serve_forever, daemon=True)
        self._thread.start()
        self.url = f"http://127.0.0.1:{self._servidor.server_address[1]}"

    def ultima(self) -> dict[str, Any]:
        gravada = self._servidor.ultima  # type: ignore[attr-defined]
        if gravada is None:
            raise AssertionError("nenhuma requisição chegou ao fake")
        return gravada

    def contagem_feedback(self) -> int:
        return self._servidor.contagem_feedback_erro_500  # type: ignore[attr-defined,no-any-return]

    def parar(self) -> None:
        self._servidor.shutdown()
        self._servidor.server_close()
