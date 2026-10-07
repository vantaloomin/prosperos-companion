import asyncio
import sys
import textwrap

from companion.providers import codex

FAKE_SERVER = '''
import json, sys
PAGES = {None: ([{"id": "a", "model": "gpt-6-sol", "displayName": "GPT-6-Sol", "hidden": False,
                  "supportedReasoningEfforts": [{"reasoningEffort": "low"}, {"reasoningEffort": "ultra"}]},
                 {"id": "h", "model": "hidden-one", "displayName": "Hidden", "hidden": True}], "next"),
         "next": ([{"id": "b", "model": "gpt-5.5", "displayName": "GPT-5.5", "hidden": False}], None)}
for line in sys.stdin:
    message = json.loads(line)
    if message.get("method") == "initialize":
        print(json.dumps({"method": "account/updated", "params": {}}))
        print(json.dumps({"id": message["id"], "result": {"userAgent": "fake/1"}}), flush=True)
    elif message.get("method") == "model/list":
        rows, cursor = PAGES[message["params"].get("cursor")]
        print(json.dumps({"id": 99, "method": "item/tool/requestUserInput", "params": {}}))
        print(json.dumps({"id": message["id"], "result": {"data": rows, "nextCursor": cursor}}), flush=True)
'''


def test_app_server_lists_visible_models_across_pages(tmp_path):
    script = tmp_path / 'fake_codex.py'
    script.write_text(textwrap.dedent(FAKE_SERVER))
    models = asyncio.run(codex.app_server_models([sys.executable, str(script)]))
    assert [model['id'] for model in models] == ['gpt-6-sol', 'gpt-5.5']
    assert models[0]['name'] == 'GPT-6-Sol' and models[0]['supported_efforts'] == ['low']
    assert 'supported_efforts' not in models[1] and models[1]['limit_source'] == 'unreported'


def test_a_cli_without_app_server_falls_back_to_common_models(tmp_path, monkeypatch):
    script = tmp_path / 'old_codex.py'
    script.write_text('import sys\nsys.exit(2)\n')
    original = codex.app_server_models
    monkeypatch.setattr(codex, 'app_server_models', lambda _command: original([sys.executable, str(script)]))
    models, reported = asyncio.run(codex.codex_models('codex'))
    assert not reported
    assert [model['id'] for model in models] == list(codex.FALLBACK_MODELS)
