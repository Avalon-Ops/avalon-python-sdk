# avalonops

SDK oficial da [AvalonOps](https://github.com/Avalon-Ops) para Python — governança de IA com a ergonomia que você já conhece: um wrapper fino sobre o [SDK da OpenAI](https://github.com/openai/openai-python), com metadata de primeira classe, request-id capturado e feedback por requisição.

Ergonomia inspirada nos SDKs open source da Portkey; código próprio, MIT.

## Uso

### Pré-requisitos

1. Tenha o gateway AvalonOps da sua organização no ar e crie uma chave de API no console (menu **Chaves**).
2. Instale o SDK e exporte a chave — o SDK já sabe onde o gateway mora (`api.avalonops.com.br`):

```bash
pip install avalonops

export AVALON_API_KEY="SUA_CHAVE"
```

### Fazendo uma requisição

O gateway adere à assinatura do SDK da OpenAI — troque `from openai import OpenAI` por `from avalonops import Avalon` e o resto do seu código continua igual. O `model` usa o id `@slug/modelo` que o catálogo do console mostra.

```python
from avalonops import Avalon

client = Avalon(metadata={"_user": "seu-usuario"})

resposta = client.chat.completions.create(
    model="@teste/gpt-4",
    messages=[{"role": "user", "content": "Explique governança de IA em uma frase."}],
)
```

### Metadata de primeira classe

A convenção `_user` identifica quem chamou: alimenta o filtro de logs, os limites por usuário e o expurgo LGPD do gateway. O metadata do construtor vale para todas as chamadas; o por-request vence o do construtor, chave a chave. (`user` no corpo, padrão OpenAI, continua valendo — e vence o header, regra do gateway.)

```python
client.chat.completions.create(
    model="@teste/gpt-4",
    messages=[{"role": "user", "content": "oi"}],
    metadata={"_user": "outro-usuario"},
)
```

### Feedback por requisição

Toda resposta carrega o `x-avalon-request-id`, exposto como `request_id` — avalie a requisição com ele (`valor` entre -1 e 1; `peso` opcional):

```python
client.feedback.create(request_id=resposta.request_id, valor=1)
```

### O catálogo da sua organização

No formato OpenAI, com os ids `@slug/modelo` prontos para copiar:

```python
modelos = client.models.list()
```

## Configuração

| Variável | Papel |
|---|---|
| `AVALON_API_KEY` | Chave da API (a mesma do console) — obrigatória |
| `AVALON_BASE_URL` | Opcional: outra instalação (dev/staging), como RAIZ sem `/v1` — o SDK completa. Sem ela, vale `https://api.avalonops.com.br` |

Ambas também podem vir no construtor (`api_key`, `base_url`), que vence a env; a base resolvida fica em `client.base_url`.

Streaming, tipos e retries são os do SDK `openai` — inclusive `stream=True`, cujo objeto de stream também expõe `request_id`.

## Licença

MIT — [LICENSE](https://github.com/Avalon-Ops/avalon-python-sdk/blob/main/LICENSE). Documentação completa na sua instalação do console, em `/docs/conectar`.
