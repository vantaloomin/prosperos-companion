"""LoRA training runs against a stand-in for AI Toolkit (the real trainer is not run in tests)."""
import json
import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from companion.identity import CLIENT_HEADER
from companion.lora import trainer, training
from companion.main import create_app
from companion.providers.vault import MemoryVault
from tests.test_images import FakeAdapter, ok
from tests.test_lora import add_picture, picture

STAND_IN = Path(__file__).parent / 'stand_in_trainer'


@pytest.fixture
def app(tmp_path, clock, provider):
    adapters = {'comfyui': FakeAdapter(), 'codex': FakeAdapter(), 'hosted': FakeAdapter()}
    return create_app(tmp_path / 'workspace' / 'companion.sqlite3', clock=clock, vault=MemoryVault(),
                      provider=provider, life_tasks=False, image_adapters=adapters, lora_maker=True)


@pytest.fixture
def client(app):
    with TestClient(app, headers={CLIENT_HEADER: 'workspace'}) as test_client:
        yield test_client


@pytest.fixture
def ready(client, companion, monkeypatch, tmp_path):
    """Five training pictures with stated rights, and the stand-in trainer configured."""
    record = tmp_path / 'trainer-record.jsonl'
    monkeypatch.setenv('FAKE_TRAINER_RECORD', str(record))
    for index in range(5):
        reference = ok(add_picture(client, picture(index), f'{index}.jpg'))
        caption = {0: 'm1ra smiling', 1: '[trigger] in a green coat'}.get(index, '')
        ok(client.put(f"/api/lora/references/{reference['id']}", json={'rights': 'own_work', 'caption': caption}))
    ok(client.put('/api/lora/settings', json={'python_path': sys.executable, 'trainer_dir': str(STAND_IN)}))
    return record


def start(client, **values):
    body = {'name': 'Mira look', 'trigger': 'm1ra', 'steps': 20, 'save_every': 5, 'accept_disclosure': True,
            'attest_fictional_adult': True, **values}
    return client.post('/api/lora/runs', json=body)


def wait(client, run_id, until=('completed', 'failed', 'cancelled'), seconds=20):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        run = ok(client.get(f'/api/lora/runs/{run_id}'))
        if run['status'] in until:
            return run
        time.sleep(0.05)
    raise AssertionError(f'run stayed {run["status"]}')


def test_trainer_description_names_the_exact_target_and_says_unverified(client, companion):
    described = ok(client.get('/api/lora/trainer'))
    assert described['name'] == 'AI Toolkit (ostris/ai-toolkit)' and described['tested'].startswith('commit ecee894')
    assert described['verified'] is False and described['arch'] == 'krea2'
    assert described['default_base_model'] == 'krea/Krea-2-Raw' and 'Hugging Face' in described['disclosure']
    assert not described['check']['ok']


def test_config_matches_the_ai_toolkit_layout(tmp_path):
    config = trainer.config('mira-abc', tmp_path / 'data', tmp_path / 'out',
                            {**trainer.DEFAULTS, 'network': 'lora', 'rank': 32}, 'krea/Krea-2-Raw')
    process = config['config']['process'][0]
    assert config['job'] == 'extension' and process['type'] == 'sd_trainer'
    assert process['model'] == {'name_or_path': 'krea/Krea-2-Raw', 'arch': 'krea2', 'quantize': True,
                                'quantize_te': True, 'low_vram': False}
    assert process['network'] == {'type': 'lora', 'linear': 32, 'linear_alpha': 32}
    assert process['datasets'][0]['resolution'] == [512, 1024] and process['train']['disable_sampling']
    assert trainer.progress('\rmira:  12%|#| 120/1000 [00:10<01:20]\rmira:  13%|#| 130/1000 [') == (130, 1000)
    assert trainer.progress('Loading transformer') is None


def test_training_needs_disclosure_attestation_and_a_ready_dataset(client, companion):
    ok(client.put('/api/lora/settings', json={'python_path': sys.executable, 'trainer_dir': str(STAND_IN)}))
    assert start(client, accept_disclosure=False).status_code == 422
    assert start(client, attest_fictional_adult=False).status_code == 422
    refused = start(client)
    assert refused.status_code == 409 and refused.json()["code"] == "dataset_not_ready", refused.text


def test_a_run_trains_reports_progress_and_registers_its_adapter(client, ready, app):
    run = ok(start(client))
    assert run['status'] == 'running' and run['verified_on_hardware'] is False
    assert start(client).status_code == 409
    done = wait(client, run['id'])
    assert done['status'] == 'completed', done['error']
    assert (done['progress_step'], done['progress_total']) == (20, 20)
    assert [item['step'] for item in done['checkpoints']] == [5, 10, 15, 20]
    assert all(item['verified'] for item in done['checkpoints']) and done['checkpoints'][-1]['final']
    adapters = ok(client.get('/api/lora/adapters'))['adapters']
    assert len(adapters) == 1 and adapters[0]['origin'] == 'trained' and adapters[0]['format'] == 'lokr'
    assert adapters[0]['trigger'] == 'm1ra' and 'ecee894' in adapters[0]['trainer']
    assert done['adapter_id'] == adapters[0]['id']
    # Nothing is adopted until the user chooses it.
    assert ok(client.get('/api/lora/appearance'))['current']['method'] == 'text'
    recorded = json.loads(ready.read_text().splitlines()[0])
    assert recorded['cwd'] == str(STAND_IN) and recorded['argv'][1].endswith('config.json')
    assert recorded['captions'] == ['m1ra', 'm1ra', 'm1ra', 'm1ra in a green coat', 'm1ra smiling']
    kept = ok(client.post(f"/api/lora/runs/{run['id']}/keep", json={'step': 10}))
    assert kept['name'] == 'Mira look (step 10)' and kept['step'] == 10
    assert 'RESUMING' not in client.get(f"/api/lora/runs/{run['id']}/log").text


def test_a_failed_run_keeps_verified_checkpoints_and_resumes_from_them(client, ready, monkeypatch, app):
    monkeypatch.setenv('FAKE_TRAINER_FAIL_AT', '12')
    run = ok(start(client))
    failed = wait(client, run['id'])
    assert failed['status'] == 'failed' and 'CUDA out of memory' in failed['error']
    assert failed['resumable'] and [item['step'] for item in failed['checkpoints']] == [5, 10]
    assert ok(client.get('/api/lora/adapters'))['adapters'] == []
    # A damaged newest checkpoint is moved aside so the trainer resumes from a good one.
    folder = app.state.database.path.parent / 'lora' / 'runs' / run['folder'] / 'output' / run['folder']
    (folder / f"{run['folder']}_000000010.safetensors").write_bytes(b'\x10\x00')
    with app.state.database.connect(write=True) as connection:
        connection.execute('UPDATE lora_runs SET checkpoints=? WHERE id=?',
                           (json.dumps(training.scan(app.state.database, training.get_row(connection, run['id']))),
                            run['id']))
    monkeypatch.delenv('FAKE_TRAINER_FAIL_AT')
    resumed = ok(client.post(f"/api/lora/runs/{run['id']}/resume"))
    assert resumed['resumed_from_step'] == 5 and resumed['attempt'] == 2
    done = wait(client, run['id'])
    assert done['status'] == 'completed'
    assert '000000005' in client.get(f"/api/lora/runs/{run['id']}/log").text
    assert (folder.parent.parent / 'set-aside' / f"{run['folder']}_000000010.safetensors").exists()


def test_cancel_stops_the_trainer_and_restart_begins_again(client, ready, monkeypatch, app):
    monkeypatch.setenv('FAKE_TRAINER_HANG_AT', '7')
    run = ok(start(client))
    deadline = time.monotonic() + 10
    while ok(client.get(f"/api/lora/runs/{run['id']}"))['progress_step'] != 7 and time.monotonic() < deadline:
        time.sleep(0.05)
    assert app.state.images.gpu_busy()
    monkeypatch.setattr(training, 'STOP_GRACE_SECONDS', 2)
    cancelled = ok(client.post(f"/api/lora/runs/{run['id']}/cancel"))
    assert cancelled['status'] == 'cancelled' and '1 verified checkpoint' in cancelled['error']
    assert cancelled['resumable'] and not app.state.images.gpu_busy()
    monkeypatch.delenv('FAKE_TRAINER_HANG_AT')
    restarted = ok(client.post(f"/api/lora/runs/{run['id']}/restart"))
    assert restarted['checkpoints'] == [] and restarted['progress_step'] is None
    done = wait(client, run['id'])
    assert done['status'] == 'completed' and done['attempt'] == 2
    assert 'RESUMING' not in client.get(f"/api/lora/runs/{run['id']}/log").text.split('Result')[-1]


def test_restart_after_a_crash_marks_running_runs_interrupted(client, ready, app):
    with app.state.database.connect(write=True) as connection:
        companion_id = connection.execute('SELECT id FROM companions').fetchone()[0]
        connection.execute(
            "INSERT INTO lora_runs (id, companion_id, name, status, trainer, trainer_tested, base_model, trigger, options, "
            "trainer_config, dataset, folder, disclosure_accepted_at, created_at, pid) VALUES ('r1', ?, 'x', 'running', "
            "'ai-toolkit', 't', 'b', 'm1ra', '{}', '{}', '{}', 'x-r1', 'now', 'now', 999999)", (companion_id,))
    training.recover(app.state.database)
    run = ok(client.get('/api/lora/runs/r1'))
    assert run['status'] == 'interrupted' and 'Resume from a verified checkpoint' in run['error']
    assert not run['resumable'] and run['restartable']


def test_prohibited_captions_never_train(client, ready):
    references = ok(client.get('/api/lora/references'))['references']
    ok(client.put(f"/api/lora/references/{references[2]['id']}", json={'caption': 'nude schoolgirl'}))
    refused = start(client)
    assert refused.status_code == 422 and refused.json()['code'] == 'prohibited'
