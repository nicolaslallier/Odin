import pytest
from unittest.mock import patch, MagicMock
import httpx
from src.worker.services.confluence_client import ConfluenceClient, WorkerError


# --- Context Manager coverage ---
def test_context_manager_and_client_cleanup():
    cl = ConfluenceClient("https://x", "e", "t")
    with patch("httpx.Client") as mock_client_cls:
        client_inst = MagicMock()
        mock_client_cls.return_value = client_inst
        with cl as inst:
            assert inst._client is client_inst
            mock_client_cls.assert_called_once()
        assert cl._client is None
        client_inst.close.assert_called_once()


def test_get_client_fail_outside_context():
    cl = ConfluenceClient("x", "e", "t")
    with pytest.raises(WorkerError):
        cl._get_client()


# --- get_comprehensive_statistics ---
def test_get_comprehensive_statistics_success(monkeypatch):
    cl = ConfluenceClient("x", "e", "t")
    monkeypatch.setattr(cl, "_get_space_info", lambda space: {"key": "s", "name": "SN"})
    monkeypatch.setattr(
        cl, "_get_all_pages", lambda space: [{"body": {"storage": {"value": "foo"}}, "version": {}}]
    )
    monkeypatch.setattr(cl, "_calculate_basic_statistics", lambda pages: {"total_pages": 1})
    monkeypatch.setattr(cl, "_calculate_detailed_statistics", lambda pages: {"foo": 2})
    monkeypatch.setattr(cl, "_calculate_comprehensive_statistics", lambda pages: {"bar": 3})
    with patch.object(cl, "_client", MagicMock()):
        out = cl.get_comprehensive_statistics("S")
        assert out["space_key"] == "s"
        assert out["space_name"] == "SN"
        assert out["basic"]["total_pages"] == 1
        assert out["detailed"]["foo"] == 2
        assert out["comprehensive"]["bar"] == 3


def test_get_comprehensive_statistics_error(monkeypatch):
    cl = ConfluenceClient("x", "e", "t")
    monkeypatch.setattr(cl, "_get_space_info", lambda k: 1 / 0)
    with patch.object(cl, "_client", MagicMock()), pytest.raises(WorkerError):
        cl.get_comprehensive_statistics("bad")


# --- _get_space_info ---
def make_mock_response(data=None, status_code=200, raise_http=None):
    resp = MagicMock()
    resp.json.return_value = data or {"key": "k", "name": "n"}
    resp.status_code = status_code
    if raise_http:
        resp.raise_for_status.side_effect = raise_http
    else:
        resp.raise_for_status.return_value = None
    return resp


@patch("httpx.Client")
def test_get_space_info_success(mock_client_cls):
    cl = ConfluenceClient("base", "e", "t")
    client = MagicMock()
    client.get.return_value = make_mock_response({"k": 1})
    cl._client = client
    out = cl._get_space_info("S")
    assert client.get.called
    assert isinstance(out, dict)


def test_get_space_info_404():
    cl = ConfluenceClient("b", "e", "t")
    client = MagicMock()

    # Simulate httpx.HTTPStatusError with .response.status_code=404
    class DummyResp:
        status_code = 404

    err = httpx.HTTPStatusError("fail", request=None, response=DummyResp())
    client.get.return_value.raise_for_status.side_effect = err
    cl._client = client
    with pytest.raises(WorkerError) as exc:
        cl._get_space_info("BAD")
    assert "not found" in str(exc.value).lower()


def test_get_space_info_other_http_error():
    cl = ConfluenceClient("b", "e", "t")
    client = MagicMock()

    class DummyResp:
        status_code = 500

    err = httpx.HTTPStatusError("fail", request=None, response=DummyResp())
    client.get.return_value.raise_for_status.side_effect = err
    cl._client = client
    with pytest.raises(WorkerError):
        cl._get_space_info("fail")


def test_get_space_info_generic_error():
    cl = ConfluenceClient("b", "e", "t")
    client = MagicMock()
    client.get.side_effect = Exception("boom")
    cl._client = client
    with pytest.raises(WorkerError):
        cl._get_space_info("x")


# --- _get_all_pages ---
def test_get_all_pages_success(monkeypatch):
    cl = ConfluenceClient("b", "e", "t")
    page = {"id": 1, "body": {"storage": {"value": "foo"}}, "version": {}}
    responses = [
        {"results": [page], "_links": {"next": "/more"}},
        {"results": [page], "_links": {}},
    ]
    client = MagicMock()
    client.get.side_effect = [make_mock_response(r) for r in responses]
    cl._client = client
    out = cl._get_all_pages("S")
    assert isinstance(out, list)
    assert len(out) == 2


def test_get_all_pages_error():
    cl = ConfluenceClient("b", "e", "t")
    client = MagicMock()
    client.get.side_effect = Exception("failpage")
    cl._client = client
    with pytest.raises(WorkerError):
        cl._get_all_pages("X")


# --- _calculate_basic_statistics ---
def test_calculate_basic_statistics_all_branches():
    cl = ConfluenceClient("b", "e", "t")
    # Various edge pages
    pages = [
        # No body, no contributors, no updated
        {},
        # All fields
        {
            "body": {"storage": {"value": "abc"}},
            "version": {"by": {"displayName": "Alice"}, "when": "2024-01-01T01:00:00", "number": 1},
        },
        # Newer update
        {
            "body": {"storage": {"value": "def"}},
            "version": {"by": {"displayName": "Bob"}, "when": "2024-01-02T01:00:00", "number": 1},
        },
    ]
    out = cl._calculate_basic_statistics(pages)
    assert out["total_pages"] == 3
    assert out["contributor_count"] == 2
    assert out["last_updated"] == "2024-01-02T01:00:00"
    assert out["total_size_bytes"] > 0


def test_calculate_detailed_statistics_all_branches():
    cl = ConfluenceClient("b", "e", "t")
    pages = [
        # No attachments, one version
        {"type": "x", "version": {"number": 1}, "children": {}},
        # Attachment type and versions
        {
            "type": "page",
            "version": {"number": 3},
            "children": {
                "attachment": {
                    "results": [
                        {"extensions": {"mediaType": "img/jpg", "fileSize": 50}},
                        {"extensions": {"mediaType": "img/png", "fileSize": 100}},
                    ]
                }
            },
        },
    ]
    out = cl._calculate_detailed_statistics(pages)
    assert "attachment_stats" in out
    stats = out["attachment_stats"]
    assert stats["count"] == 2
    assert stats["total_size_bytes"] == 150
    assert stats["types"]["img/jpg"] == 1
    assert stats["types"]["img/png"] == 1
    assert out["version_count"] == 4
    assert out["page_breakdown_by_type"]["x"] == 1


def test_calculate_comprehensive_statistics_all_branches():
    cl = ConfluenceClient("b", "e", "t")
    # User activity, links, comments
    pages = [
        # Simple create
        {
            "history": {"createdBy": {"displayName": "Zee"}},
            "version": {"number": 2},
            "body": {"storage": {"value": 'ac:link href="http://abc.com"'}},
        },
        # Absent creator, edge-cases
        {},
    ]
    stats = cl._calculate_comprehensive_statistics(pages)
    assert stats["user_activity"]["Zee"]["pages_created"] == 1
    assert stats["user_activity"]["Zee"]["total_edits"] == 2
    assert "internal" in stats["link_analysis"]
    assert "external" in stats["link_analysis"]
