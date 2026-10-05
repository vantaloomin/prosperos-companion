import logging
import logging.config

from companion import logs


def test_credentials_are_masked():
    line = ('Authorization: Bearer abc.def-ghi api_key=XYZ123456 "token": "t0k3n" '
            'sk-proj-ABCDEFGH12345678 hf_ABCDEFGHIJKL normal words stay')
    masked = logs.redact(line)
    for secret in ('abc.def-ghi', 'XYZ123456', 't0k3n', 'sk-proj-ABCDEFGH12345678', 'hf_ABCDEFGHIJKL'):
        assert secret not in masked
    assert 'normal words stay' in masked


def test_log_file_masks_messages_and_tracebacks(tmp_path):
    logging.config.dictConfig(logs.config(tmp_path))
    logger = logging.getLogger('uvicorn.error')
    logger.info('Connecting with %s', 'Bearer sk-live-SECRETSECRET')
    try:
        raise RuntimeError('provider refused api_key=SECRETVALUE')
    except RuntimeError:
        logger.exception('Request failed')
    for handler in logger.handlers:
        handler.flush()
    text = (tmp_path / 'logs' / 'companion.log').read_text(encoding='utf-8')
    assert 'Request failed' in text and 'RuntimeError' in text
    assert 'SECRET' not in text
    for name in ('uvicorn', 'uvicorn.error', 'companion'):
        configured = logging.getLogger(name)
        for handler in list(configured.handlers):
            handler.close()
            configured.removeHandler(handler)
        configured.propagate = True
