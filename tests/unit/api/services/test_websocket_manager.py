import pytest
from unittest.mock import AsyncMock, patch
from src.api.services.websocket import WebSocketManager, WebSocketDisconnect


@pytest.mark.asyncio
class TestWebSocketManager:
    @pytest.fixture
    def ws_manager(self) -> WebSocketManager:
        return WebSocketManager()

    @pytest.fixture
    def mock_websocket(self):
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.close = AsyncMock()
        ws.send_json = AsyncMock()
        return ws

    @pytest.mark.asyncio
    async def test_connect_new_client(self, ws_manager: WebSocketManager, mock_websocket):
        """Test that connect adds a websocket and returns a client id."""
        client_id = await ws_manager.connect(mock_websocket)
        assert client_id in ws_manager.connections
        mock_websocket.accept.assert_awaited_once()
        assert ws_manager.get_connection_count() == 1

    @pytest.mark.asyncio
    async def test_connect_with_client_id(self, ws_manager: WebSocketManager, mock_websocket):
        """Test connect with explicit client id."""
        cid = "test-client-42"
        result = await ws_manager.connect(mock_websocket, client_id=cid)
        assert result == cid
        assert ws_manager.connections[cid] == mock_websocket

    @pytest.mark.asyncio
    async def test_connect_exception(self, ws_manager: WebSocketManager):
        ws = AsyncMock()
        ws.accept.side_effect = Exception("fail")
        with pytest.raises(Exception):
            await ws_manager.connect(ws)
        assert ws_manager.get_connection_count() == 0

    @pytest.mark.asyncio
    async def test_disconnect_and_cleanup(self, ws_manager: WebSocketManager, mock_websocket):
        # Setup
        client_id = await ws_manager.connect(mock_websocket)
        await ws_manager.subscribe_to_space(client_id, "SPACE")
        await ws_manager.disconnect(client_id)
        assert client_id not in ws_manager.connections
        assert ws_manager.get_connection_count() == 0
        assert ws_manager.get_subscription_count("SPACE") == 0

    @pytest.mark.asyncio
    async def test_disconnect_closes_socket_and_removes_from_all_spaces(
        self, ws_manager: WebSocketManager, mock_websocket
    ):
        cid = await ws_manager.connect(mock_websocket)
        await ws_manager.subscribe_to_space(cid, "A")
        await ws_manager.subscribe_to_space(cid, "B")
        await ws_manager.disconnect(cid)
        mock_websocket.close.assert_awaited()
        assert ws_manager.space_subscriptions == {}
        # coverage for not present client
        await ws_manager.disconnect("not-present")

    @pytest.mark.asyncio
    async def test_disconnect_socket_close_error_handled(self, ws_manager: WebSocketManager):
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.close = AsyncMock(side_effect=Exception("close-error"))
        cid = await ws_manager.connect(ws)
        await ws_manager.disconnect(cid)  # Should handle exception
        assert ws_manager.get_connection_count() == 0

    def test_get_connection_count_and_subscription_count(self, ws_manager: WebSocketManager):
        ws_manager.connections = {"a": None, "b": None}
        ws_manager.space_subscriptions = {"SPACE": {"a", "b"}, "X": set()}
        assert ws_manager.get_connection_count() == 2
        assert ws_manager.get_subscription_count("SPACE") == 2
        assert ws_manager.get_subscription_count("Y") == 0

    @pytest.mark.asyncio
    async def test_subscribe_unsubscribe_to_space(self, ws_manager: WebSocketManager):
        ws_manager.space_subscriptions = {}
        await ws_manager.subscribe_to_space("cid1", "SP1")
        await ws_manager.subscribe_to_space("cid2", "SP1")
        assert ws_manager.get_subscription_count("SP1") == 2
        await ws_manager.unsubscribe_from_space("cid1", "SP1")
        assert ws_manager.get_subscription_count("SP1") == 1
        await ws_manager.unsubscribe_from_space("cid2", "SP1")
        assert ws_manager.get_subscription_count("SP1") == 0
        # Unsubscribe when not present OK
        await ws_manager.unsubscribe_from_space("nope", "SP1")

    @pytest.mark.asyncio
    async def test_broadcast_statistics_and_fails(
        self, ws_manager: WebSocketManager, mock_websocket
    ):
        cid = await ws_manager.connect(mock_websocket)
        await ws_manager.subscribe_to_space(cid, "SP")
        # Normal send
        count = await ws_manager.broadcast_statistics("SP", "jid", {"x": 1})
        assert count == 1
        # Simulate send_json failure
        ws_manager.connections[cid].send_json.side_effect = Exception("fail")
        count2 = await ws_manager.broadcast_statistics("SP", "jid", {"x": 2})
        assert count2 == 0

    @pytest.mark.asyncio
    async def test_broadcast_statistics_disconnect(
        self, ws_manager: WebSocketManager, mock_websocket
    ):
        cid = await ws_manager.connect(mock_websocket)
        await ws_manager.subscribe_to_space(cid, "SP")
        ws_manager.connections[cid].send_json.side_effect = WebSocketDisconnect()
        count = await ws_manager.broadcast_statistics("SP", "jid", {"x": 2})
        assert count == 0

    @pytest.mark.asyncio
    async def test_broadcast_to_all(self, ws_manager: WebSocketManager, mock_websocket):
        c1 = await ws_manager.connect(mock_websocket)
        c2 = await ws_manager.connect(AsyncMock())
        count = await ws_manager.broadcast_to_all({"msg": "hi"})
        assert count == 2

    @pytest.mark.asyncio
    async def test_broadcast_to_all_disconnect_and_error(
        self, ws_manager: WebSocketManager, mock_websocket
    ):
        c = await ws_manager.connect(mock_websocket)
        ws_manager.connections[c].send_json.side_effect = WebSocketDisconnect()
        result = await ws_manager.broadcast_to_all({"msg": "X"})
        assert result == 0
        # error
        c2 = await ws_manager.connect(AsyncMock())
        ws_manager.connections[c2].send_json.side_effect = Exception("fail")
        result2 = await ws_manager.broadcast_to_all({"msg": "fail"})
        assert result2 == 0

    @pytest.mark.asyncio
    async def test_send_to_client_success_failure(
        self, ws_manager: WebSocketManager, mock_websocket
    ):
        cid = await ws_manager.connect(mock_websocket)
        ok = await ws_manager.send_to_client(cid, {"foo": 1})
        assert ok is True
        # Not present
        ok2 = await ws_manager.send_to_client("unknown", {"foo": 2})
        assert ok2 is False
        mock_websocket.send_json.side_effect = WebSocketDisconnect()
        ok3 = await ws_manager.send_to_client(cid, {"foo": 33})
        assert ok3 is False
        ws_manager.connections[cid] = AsyncMock()
        ws_manager.connections[cid].send_json.side_effect = Exception("fail")
        ok4 = await ws_manager.send_to_client(cid, {"foo": 44})
        assert ok4 is False

    @pytest.mark.asyncio
    async def test_handle_client_message_subscribe_unsubscribe_ping_unknown_error(
        self, ws_manager: WebSocketManager
    ):
        cid = "cid1"
        ws_manager.connections[cid] = AsyncMock()
        # subscribe
        with (
            patch.object(ws_manager, "subscribe_to_space", new=AsyncMock()) as sub_mock,
            patch.object(ws_manager, "send_to_client", new=AsyncMock()) as send_mock,
        ):
            await ws_manager.handle_client_message(cid, {"type": "subscribe", "space_key": "SP2"})
            sub_mock.assert_awaited_with(cid, "SP2")
            send_mock.assert_awaited()
        # unsubscribe
        with (
            patch.object(ws_manager, "unsubscribe_from_space", new=AsyncMock()) as unsub_mock,
            patch.object(ws_manager, "send_to_client", new=AsyncMock()) as send_mock,
        ):
            await ws_manager.handle_client_message(cid, {"type": "unsubscribe", "space_key": "SP3"})
            unsub_mock.assert_awaited_with(cid, "SP3")
            send_mock.assert_awaited()
        # ping
        with patch.object(ws_manager, "send_to_client", new=AsyncMock()) as send_mock:
            await ws_manager.handle_client_message(cid, {"type": "ping"})
            send_mock.assert_awaited_with(cid, {"type": "pong"})
        # unknown
        with patch.object(ws_manager, "send_to_client", new=AsyncMock()) as send_mock:
            await ws_manager.handle_client_message(cid, {"type": "nonsense"})
            send_mock.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_handle_client_message_error_branch(self, ws_manager: WebSocketManager):
        cid = "cid1"
        ws_manager.connections[cid] = AsyncMock()
        # Simulate an error in send_to_client, ensure handler doesn't raise
        with patch.object(
            ws_manager, "send_to_client", new=AsyncMock(side_effect=Exception("fail"))
        ):
            # Should not raise, error is logged and handled inside handler
            await ws_manager.handle_client_message(cid, None)

    @pytest.mark.asyncio
    async def test_cleanup(self, ws_manager: WebSocketManager, mock_websocket):
        cid1 = await ws_manager.connect(mock_websocket)
        cid2 = await ws_manager.connect(AsyncMock())
        await ws_manager.cleanup()
        assert ws_manager.get_connection_count() == 0
