"""Unit tests for event-driven tasks.

This module tests event-driven tasks triggered by user actions and system events.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.worker.tasks.events import (
    handle_user_registration,
    process_webhook,
    send_notification,
)


class TestHandleUserRegistration:
    """Test suite for handle_user_registration task."""

    @patch("src.worker.tasks.events.session_scope")
    @patch("src.worker.tasks.events.send_notification")
    def test_handle_registration_success(
        self, mock_send_notification: MagicMock, mock_session_scope: MagicMock
    ) -> None:
        """Test successful user registration handling."""
        # Arrange
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session
        user_data = {
            "user_id": 123,
            "email": "user@example.com",
            "username": "testuser",
        }

        # Act
        result = handle_user_registration(user_data)

        # Assert
        assert result["status"] == "success"
        assert result["user_id"] == 123
        mock_send_notification.delay.assert_called_once()

    @patch("src.worker.tasks.events.session_scope")
    def test_handle_registration_missing_data(
        self, mock_session_scope: MagicMock
    ) -> None:
        """Test registration handling with missing required data."""
        # Arrange
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session
        incomplete_data = {"email": "user@example.com"}  # Missing user_id

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            handle_user_registration(incomplete_data)

        assert "user_id" in str(exc_info.value).lower()

    @patch("src.worker.tasks.events.session_scope")
    @patch("src.worker.tasks.events.send_notification")
    def test_handle_registration_sends_welcome_email(
        self, mock_send_notification: MagicMock, mock_session_scope: MagicMock
    ) -> None:
        """Test that welcome email is sent after registration."""
        # Arrange
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session
        user_data = {
            "user_id": 123,
            "email": "user@example.com",
            "username": "testuser",
        }

        # Act
        result = handle_user_registration(user_data)

        # Assert
        assert result["welcome_email_sent"] is True

    @patch("src.worker.tasks.events.session_scope")
    def test_handle_registration_creates_user_profile(
        self, mock_session_scope: MagicMock
    ) -> None:
        """Test that user profile is created during registration."""
        # Arrange
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session
        user_data = {
            "user_id": 123,
            "email": "user@example.com",
            "username": "testuser",
        }

        # Act
        result = handle_user_registration(user_data)

        # Assert
        assert result["profile_created"] is True


class TestProcessWebhook:
    """Test suite for process_webhook task."""

    @patch("src.worker.tasks.events.validate_webhook_signature")
    @patch("src.worker.tasks.events.session_scope")
    def test_process_webhook_success(
        self, mock_session_scope: MagicMock, mock_validate: MagicMock
    ) -> None:
        """Test successful webhook processing."""
        # Arrange
        mock_validate.return_value = True
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session
        webhook_data = {
            "event": "payment.success",
            "payload": {"amount": 100, "currency": "USD"},
        }

        # Act
        result = process_webhook(webhook_data, signature="valid_signature")

        # Assert
        assert result["status"] == "success"
        assert result["event"] == "payment.success"

    @patch("src.worker.tasks.events.validate_webhook_signature")
    def test_process_webhook_invalid_signature(
        self, mock_validate: MagicMock
    ) -> None:
        """Test webhook processing with invalid signature."""
        # Arrange
        mock_validate.return_value = False
        webhook_data = {"event": "payment.success", "payload": {}}

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            process_webhook(webhook_data, signature="invalid_signature")

        assert "signature" in str(exc_info.value).lower()

    @patch("src.worker.tasks.events.validate_webhook_signature")
    @patch("src.worker.tasks.events.session_scope")
    def test_process_webhook_stores_event(
        self, mock_session_scope: MagicMock, mock_validate: MagicMock
    ) -> None:
        """Test that webhook events are stored in database."""
        # Arrange
        mock_validate.return_value = True
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session
        webhook_data = {"event": "user.updated", "payload": {"user_id": 123}}

        # Act
        result = process_webhook(webhook_data, signature="valid_signature")

        # Assert
        assert result["stored"] is True
        mock_session.add.assert_called_once()

    @patch("src.worker.tasks.events.validate_webhook_signature")
    @patch("src.worker.tasks.events.session_scope")
    def test_process_webhook_handles_different_event_types(
        self, mock_session_scope: MagicMock, mock_validate: MagicMock
    ) -> None:
        """Test processing different types of webhook events."""
        # Arrange
        mock_validate.return_value = True
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session

        event_types = ["payment.success", "user.created", "order.completed"]

        # Act & Assert
        for event_type in event_types:
            webhook_data = {"event": event_type, "payload": {}}
            result = process_webhook(webhook_data, signature="valid_signature")
            assert result["event"] == event_type


class TestSendNotification:
    """Test suite for send_notification task."""

    @patch("src.worker.tasks.events.httpx")
    def test_send_notification_success(self, mock_httpx: MagicMock) -> None:
        """Test successful notification sending."""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_httpx.post.return_value = mock_response

        notification_data = {
            "user_id": 123,
            "type": "email",
            "subject": "Test",
            "message": "Test message",
        }

        # Act
        result = send_notification(notification_data)

        # Assert
        assert result["status"] == "success"
        assert result["user_id"] == 123

    @patch("src.worker.tasks.events.httpx")
    def test_send_notification_retry_on_failure(self, mock_httpx: MagicMock) -> None:
        """Test that failed notifications are retried."""
        # Arrange
        mock_httpx.post.side_effect = Exception("Network error")
        notification_data = {
            "user_id": 123,
            "type": "email",
            "subject": "Test",
            "message": "Test message",
        }

        # Act
        result = send_notification(notification_data)

        # Assert
        assert result["status"] == "failed"
        assert "error" in result

    @patch("src.worker.tasks.events.httpx")
    def test_send_notification_validates_type(self, mock_httpx: MagicMock) -> None:
        """Test that notification type is validated."""
        # Arrange
        notification_data = {
            "user_id": 123,
            "type": "invalid_type",
            "subject": "Test",
            "message": "Test message",
        }

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            send_notification(notification_data)

        assert "type" in str(exc_info.value).lower()

    @patch("src.worker.tasks.events.httpx")
    def test_send_notification_supports_multiple_channels(
        self, mock_httpx: MagicMock
    ) -> None:
        """Test sending notifications through different channels."""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_httpx.post.return_value = mock_response

        notification_types = ["email", "sms", "push"]

        # Act & Assert
        for notification_type in notification_types:
            notification_data = {
                "user_id": 123,
                "type": notification_type,
                "subject": "Test",
                "message": "Test message",
            }
            result = send_notification(notification_data)
            assert result["status"] == "success"

    @patch("src.worker.tasks.events.httpx")
    @patch("src.worker.tasks.events.session_scope")
    def test_send_notification_logs_to_database(
        self, mock_session_scope: MagicMock, mock_httpx: MagicMock
    ) -> None:
        """Test that sent notifications are logged to database."""
        # Arrange
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_httpx.post.return_value = mock_response

        notification_data = {
            "user_id": 123,
            "type": "email",
            "subject": "Test",
            "message": "Test message",
        }

        # Act
        result = send_notification(notification_data)

        # Assert
        assert result["logged"] is True

