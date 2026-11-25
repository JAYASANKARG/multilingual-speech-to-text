from pathlib import Path

import pytest
import yaml

from app.main import app

CONTRACT = (
    Path(__file__).parents[3] / "specs/001-realtime-speech-transcription/contracts/rest-api.yaml"
)
# Operations not built yet; emptied as the stories that own them land.
PENDING: set[str] = set()


def _operations() -> list[tuple[str, str, str, set[str]]]:
    spec = yaml.safe_load(CONTRACT.read_text())
    ops = []
    for path, item in spec["paths"].items():
        for method, op in item.items():
            if method in ("get", "post", "patch", "delete"):
                ops.append((f"/api{path}", method, op["operationId"], set(op["responses"])))
    return ops


@pytest.mark.parametrize(("path", "method", "op_id", "codes"), _operations())
def test_contract_operation_exists(path: str, method: str, op_id: str, codes: set[str]) -> None:
    if op_id in PENDING:
        pytest.skip("not implemented yet")
    generated = app.openapi()["paths"]
    assert path in generated, f"missing path {path}"
    assert method in generated[path], f"missing {method} {path}"
    operation = generated[path][method]
    assert operation["operationId"] == op_id
    assert codes <= set(operation["responses"]), (
        f"{op_id}: missing {codes - set(operation['responses'])}"
    )
