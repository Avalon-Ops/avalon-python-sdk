"""RN-SDK-06: o bloco python do README roda DE VERDADE contra o fake — só
uma linha de print ACRESCIDA (nunca editada), molde do console."""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from .fake_gateway import REQUEST_ID_DO_FAKE, FakeGateway


def test_bloco_do_readme_roda_ponta_a_ponta(fake: FakeGateway) -> None:
    readme = (Path(__file__).resolve().parent.parent / "README.md").read_text(encoding="utf-8")
    achado = re.search(r"```python\n(.*?)```", readme, re.DOTALL)
    assert achado, "o README precisa ter um bloco ```python"
    acrescimo = '\nimport json\nprint(json.dumps({"request_id": resposta.request_id, "total": len(modelos.data)}))'
    script = achado.group(1) + acrescimo
    resultado = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True, text=True, check=True,
        env={**os.environ, "AVALON_BASE_URL": fake.url, "AVALON_API_KEY": "gov_readme"},
    )
    ultima_linha = resultado.stdout.strip().splitlines()[-1]
    saida = json.loads(ultima_linha)
    assert saida["request_id"] == REQUEST_ID_DO_FAKE
    assert saida["total"] == 1
