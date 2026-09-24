# avalonops

SDK oficial da [AvalonOps](https://github.com/Avalon-Ops) para Python — governança de IA com a ergonomia que você já conhece: um wrapper fino sobre o [SDK da OpenAI](https://github.com/openai/openai-python), com metadata de primeira classe, request-id capturado e feedback por requisição.

Ergonomia inspirada nos SDKs open source da Portkey; código próprio, MIT.

## Instalação

```bash
pip install avalonops
```

## Configuração

| Variável | Papel |
|---|---|
| `AVALON_API_KEY` | Chave da API (a mesma do console) |
| `AVALON_BASE_URL` | RAIZ do gateway da sua instalação, sem `/v1` — o SDK completa |

Ambas também podem vir no construtor (`api_key`, `base_url`), que vence a env.

## Uso

```python
from avalonops import Avalon

client = Avalon(metadata={"_user": "seu-usuario"})

resposta = client.chat.completions.create(
    model="@teste/gpt-4",
    messages=[{"role": "user", "content": "Explique governança de IA em uma frase."}],
)

# Metadata por request vence o do construtor, chave a chave.
client.chat.completions.create(
    model="@teste/gpt-4",
    messages=[{"role": "user", "content": "oi"}],
    metadata={"_user": "outro-usuario"},
)

# Toda resposta carrega o x-avalon-request-id — avalie a requisição com ele.
client.feedback.create(request_id=resposta.request_id, valor=1)

# O catálogo, no formato OpenAI: ids @slug/modelo.
modelos = client.models.list()
```

A convenção `_user` identifica quem chamou: alimenta o filtro de logs, os limites por usuário e o expurgo LGPD do gateway. `user` no corpo (padrão OpenAI) continua valendo — e vence o header, regra do gateway.

Streaming, tipos e retries são os do SDK `openai` — inclusive `stream=True`, cujo objeto de stream também expõe `request_id`.

## Licença

MIT — [LICENSE](https://github.com/Avalon-Ops/avalon-python-sdk/blob/main/LICENSE). Documentação completa na sua instalação do console, em `/docs/conectar`.
