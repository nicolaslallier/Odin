import pytest
from unittest.mock import patch, MagicMock
from src.worker.tasks import confluence
import types

# --- collect_confluence_statistics ---
def _fake_stats(space_key):
    return {
        'space_key': space_key,
        'space_name': f"Name for {space_key}",
        'basic': {'total_pages': 10},
        'detailed': {'foo': 1},
        'comprehensive': {'bar': 2},
    }

def _fake_event(job_id="123", space_key="XYZ", callback_url="http://cb/url"):
    return {"job_id": job_id, "space_key": space_key, "callback_url": callback_url}

@patch("src.worker.tasks.confluence._send_callback")
@patch("time.time", side_effect=lambda: 100.0)
@patch("src.worker.tasks.confluence.ConfluenceClient")
def test_collect_statistics_success_env_creds(mock_client_cls, mock_time, mock_send_cb):
    stats = _fake_stats("XYZ")
    mock_cl = MagicMock()
    mock_cl.get_comprehensive_statistics.return_value = stats
    mock_client_cls.return_value.__enter__.return_value = mock_cl
    # env with creds
    with patch.dict("os.environ", {"CONFLUENCE_BASE_URL": "url", "CONFLUENCE_EMAIL": "e", "CONFLUENCE_API_TOKEN": "t"}):
        out = confluence._collect_confluence_statistics_impl(MagicMock(), _fake_event())
    assert out['status'] == 'success'
    mock_send_cb.assert_called()
    assert mock_client_cls.called

@patch("src.worker.tasks.confluence._send_callback")
@patch("src.worker.tasks.confluence._get_credentials_from_vault")
@patch("src.worker.tasks.confluence.ConfluenceClient")
def test_collect_statistics_vault_creds(mock_client_cls, mock_vault, mock_send_cb):
    stats = _fake_stats("ZZZ")
    mock_cl = MagicMock()
    mock_cl.get_comprehensive_statistics.return_value = stats
    mock_client_cls.return_value.__enter__.return_value = mock_cl
    mock_vault.return_value = {"base_url": "U", "email": "E", "api_token": "T"}
    # env missing creds triggers vault
    with patch.dict("os.environ", {}):
        out = confluence._collect_confluence_statistics_impl(MagicMock(), _fake_event(space_key="ZZZ"))
    assert out['status'] == 'success'
    assert mock_vault.called
    mock_send_cb.assert_called()
    assert mock_client_cls.called

@patch("src.worker.tasks.confluence._send_callback")
@patch("src.worker.tasks.confluence.ConfluenceClient")
def test_collect_statistics_workererror_causes_retry(mock_client_cls, mock_send_cb):
    class DummySelf:
        request = types.SimpleNamespace(retries=0)
        max_retries = 1
        def retry(self, exc): raise Exception(f"retrying: {exc}")
    mock_cl = MagicMock()
    mock_cl.get_comprehensive_statistics.side_effect = confluence.WorkerError("fail!")
    mock_client_cls.return_value.__enter__.return_value = mock_cl
    with patch.dict("os.environ", {"CONFLUENCE_BASE_URL": "u", "CONFLUENCE_EMAIL": "e", "CONFLUENCE_API_TOKEN": "t"}):
        try:
            confluence._collect_confluence_statistics_impl(DummySelf(), _fake_event())
        except Exception as e:
            assert "retrying" in str(e)
    # callback must be called
    assert mock_send_cb.called

@patch("src.worker.tasks.confluence._send_callback", side_effect=Exception("callbackfail"))
@patch("src.worker.tasks.confluence.ConfluenceClient")
def test_collect_statistics_workererror_callback_fails(mock_client_cls, mock_send_cb):
    class DummySelf:
        request = types.SimpleNamespace(retries=9)
        max_retries = 1
        def retry(self, exc): raise Exception("shouldn't retry")
    mock_cl = MagicMock()
    mock_cl.get_comprehensive_statistics.side_effect = confluence.WorkerError("we")
    mock_client_cls.return_value.__enter__.return_value = mock_cl
    with patch.dict("os.environ", {"CONFLUENCE_BASE_URL": "u", "CONFLUENCE_EMAIL": "e", "CONFLUENCE_API_TOKEN": "t"}):
        with pytest.raises(confluence.WorkerError):
            confluence._collect_confluence_statistics_impl(DummySelf(), _fake_event())
    # log error branch covered by side effect

@patch("src.worker.tasks.confluence._send_callback")
@patch("src.worker.tasks.confluence.ConfluenceClient")
def test_collect_statistics_generic_exception(mock_client_cls, mock_send_cb):
    class DummySelf: pass
    mock_cl = MagicMock()
    mock_cl.get_comprehensive_statistics.side_effect = Exception("boom")
    mock_client_cls.return_value.__enter__.return_value = mock_cl
    with patch.dict("os.environ", {"CONFLUENCE_BASE_URL": "u", "CONFLUENCE_EMAIL": "e", "CONFLUENCE_API_TOKEN": "t"}):
        with pytest.raises(Exception):
            confluence._collect_confluence_statistics_impl(DummySelf(), _fake_event())
    assert mock_send_cb.called

# --- _get_credentials_from_vault ---
@patch("hvac.Client")
def test_get_credentials_from_vault_success(mock_hvac):
    # fake Vault response
    client = MagicMock()
    client.secrets.kv.v2.read_secret_version.return_value = {"data": {"data": {"base_url": "U", "email": "E", "api_token": "T"}}}
    mock_hvac.return_value = client
    with patch.dict("os.environ", {"VAULT_ADDR": "A", "VAULT_TOKEN": "T"}):
        out = confluence._get_credentials_from_vault()
    assert out["base_url"] == "U"

@patch("hvac.Client", side_effect=Exception("failout"))
def test_get_credentials_from_vault_error(mock_hvac):
    with pytest.raises(confluence.WorkerError):
        confluence._get_credentials_from_vault()

# --- _send_callback ---
@patch("httpx.Client")
def test_send_callback_success(mock_httpx):
    # Setup dummy POST
    inst = mock_httpx.return_value.__enter__.return_value
    response = MagicMock()
    response.raise_for_status.return_value = None
    inst.post.return_value = response
    confluence._send_callback("http://api/", {"a": 1})
    inst.post.assert_called()

@patch('httpx.Client')
def test_send_callback_http_status_error(mock_httpx):
    inst = mock_httpx.return_value.__enter__.return_value
    resp = MagicMock()
    class DummyHTTPStatus(Exception):
        response = MagicMock(status_code=403, text='Forbidden')
    resp.raise_for_status.side_effect = DummyHTTPStatus()
    inst.post.return_value = resp
    with pytest.raises(confluence.WorkerError):
        confluence._send_callback("x", {})

@patch('httpx.Client', side_effect=Exception('failpost'))
def test_send_callback_other_exception(mock_httpx):
    with pytest.raises(confluence.WorkerError):
        confluence._send_callback("z", {})

# --- process_statistics_queue ---
@patch('json.loads', side_effect=lambda b: {"job_id": "jid"})
@patch('pika.BlockingConnection')
def test_process_queue_success(mock_conn_cls, mock_json_loads,):
    from src.worker.tasks import confluence
    fakechan = MagicMock()
    fakechan.basic_get.side_effect = [
        (MagicMock(), None, b'{"job_id": "jid"}'),
        (MagicMock(), None, b'{"job_id": "jid2"}'),
        (None, None, None)
    ]
    fakeconn = MagicMock()
    fakeconn.channel.return_value = fakechan
    mock_conn_cls.return_value = fakeconn
    key = "collect_confluence_statistics"
    globals_ = confluence.process_statistics_queue.__wrapped__.__globals__
    original = globals_.get(key, None)
    mock_task = MagicMock()
    mock_task.delay = MagicMock()
    globals_[key] = mock_task
    try:
        with patch.dict("os.environ", {"CELERY_BROKER_URL": "amqp://user:pass@host/"}):
            result = confluence.process_statistics_queue()
        assert result["status"] == "success"
        assert result["processed"] == 2
        fakechan.basic_ack.assert_called()
    finally:
        if original is not None:
            globals_[key] = original
        else:
            del globals_[key]

@patch('json.loads', side_effect=Exception("bad_json"))
@patch('pika.BlockingConnection')
def test_process_queue_message_error(mock_conn_cls, mock_json_loads):
    from src.worker.tasks import confluence
    fakechan = MagicMock()
    msg = MagicMock()
    fakechan.basic_get.side_effect = [(msg, None, b'bad')]*(1) + [(None, None, None)]
    fakeconn = MagicMock()
    fakeconn.channel.return_value = fakechan
    mock_conn_cls.return_value = fakeconn
    key = "collect_confluence_statistics"
    globals_ = confluence.process_statistics_queue.__wrapped__.__globals__
    original = globals_.get(key, None)
    mock_task = MagicMock()
    mock_task.delay = MagicMock()
    globals_[key] = mock_task
    try:
        result = confluence.process_statistics_queue()
        fakechan.basic_nack.assert_called()
        assert result["status"] == "success"
    finally:
        if original is not None:
            globals_[key] = original
        else:
            del globals_[key]

@patch('pika.BlockingConnection', side_effect=Exception('failconnect'))
def test_process_queue_outer_error(mock_conn_cls):
    with patch.dict("os.environ", {}):
        res = confluence.process_statistics_queue()
    assert res["status"] == "error"
    assert res["processed"] == 0
