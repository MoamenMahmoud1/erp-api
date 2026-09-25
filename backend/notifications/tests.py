from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from auditlog.models import AuditEvent

from .models import Notification, NotificationDelivery, PushDevice
from .push import send_notification_push
from .tasks import create_notification_for_approval_event
from .views import (
    FirebaseWebConfigView,
    NotificationListView,
    NotificationMarkReadView,
    PushDeviceRegistrationView,
)


User = get_user_model()


class NotificationTaskTests(TestCase):
    def setUp(self):
        self.requester = User.objects.create_user(
            username="rep-notify",
            email="rep-notify@example.com",
            password="test-password",
        )
        self.manager = User.objects.create_user(
            username="manager-notify",
            email="manager-notify@example.com",
            password="test-password",
        )

    def _event(self, action, metadata):
        return AuditEvent.objects.create(
            action=action,
            entity_type="invoice",
            entity_id=42,
            actor_id=self.requester.pk,
            request_id="notification-test",
            metadata=metadata,
        )

    def test_approval_request_notifies_assigned_manager(self):
        event = self._event(
            "approval.requested",
            {"operation": "update", "approver_id": self.manager.pk},
        )

        self.assertEqual(create_notification_for_approval_event(event.pk), 1)
        notification = Notification.objects.get()
        self.assertEqual(notification.user_id, self.manager.pk)
        self.assertFalse(notification.is_read)

    def test_approval_notification_is_idempotent(self):
        event = self._event(
            "approval.requested",
            {"operation": "delete", "approver_id": self.manager.pk},
        )

        create_notification_for_approval_event(event.pk)
        create_notification_for_approval_event(event.pk)

        self.assertEqual(Notification.objects.count(), 1)

    def test_approval_decision_notifies_requester(self):
        event = self._event(
            "approval.approved",
            {"operation": "update", "requester_id": self.requester.pk},
        )

        self.assertEqual(create_notification_for_approval_event(event.pk), 1)
        self.assertEqual(Notification.objects.get().user_id, self.requester.pk)


class NotificationApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="notify-api",
            email="notify-api@example.com",
            password="test-password",
        )
        self.other_user = User.objects.create_user(
            username="other-notify",
            email="other-notify@example.com",
            password="test-password",
        )
        self.notification = Notification.objects.create(
            user=self.user,
            notification_type=Notification.NotificationType.APPROVAL_REQUESTED,
            title="Test",
            body="Test body",
            dedupe_key="api-test-notification",
        )

    def test_list_returns_only_current_users_notifications(self):
        Notification.objects.create(
            user=self.other_user,
            notification_type=Notification.NotificationType.APPROVAL_REQUESTED,
            title="Other",
            body="Other body",
            dedupe_key="other-test-notification",
        )
        request = APIRequestFactory().get("/api/v1/notifications/")
        force_authenticate(request, user=self.user)

        response = NotificationListView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], self.notification.pk)

    def test_mark_read_requires_notification_ownership(self):
        request = APIRequestFactory().post("/api/v1/notifications/999/read/")
        force_authenticate(request, user=self.other_user)

        response = NotificationMarkReadView.as_view()(request, pk=self.notification.pk)

        self.assertEqual(response.status_code, 404)
        self.notification.refresh_from_db()
        self.assertIsNone(self.notification.read_at)

    def test_mark_read_updates_read_at(self):
        request = APIRequestFactory().post(f"/api/v1/notifications/{self.notification.pk}/read/")
        force_authenticate(request, user=self.user)

        response = NotificationMarkReadView.as_view()(request, pk=self.notification.pk)

        self.assertEqual(response.status_code, 200)
        self.notification.refresh_from_db()
        self.assertIsNotNone(self.notification.read_at)

    def test_device_registration_belongs_to_authenticated_user(self):
        request = APIRequestFactory().post(
            "/api/v1/notifications/devices/",
            {
                "installation_id": "fid-device-1",
                "platform": "android",
                "firebase_app_id": "app-id-1",
            },
            format="json",
        )
        force_authenticate(request, user=self.user)

        response = PushDeviceRegistrationView.as_view()(request)

        self.assertEqual(response.status_code, 201)
        device = PushDevice.objects.get(installation_id="fid-device-1")
        self.assertEqual(device.user_id, self.user.pk)
        self.assertTrue(device.is_active)

    def test_device_registration_accepts_web_platform(self):
        request = APIRequestFactory().post(
            "/api/v1/notifications/devices/",
            {
                "installation_id": "fid-web-1",
                "platform": "web",
                "firebase_app_id": "web-app-id",
            },
            format="json",
        )
        force_authenticate(request, user=self.user)

        response = PushDeviceRegistrationView.as_view()(request)

        self.assertEqual(response.status_code, 201)
        device = PushDevice.objects.get(installation_id="fid-web-1")
        self.assertEqual(device.platform, PushDevice.Platform.WEB)

    def test_web_config_returns_disabled_when_web_credentials_are_missing(self):
        request = APIRequestFactory().get("/api/v1/notifications/web-config/")
        with self.settings(
            FIREBASE_ENABLED=True,
            FIREBASE_PROJECT_ID="project",
            FIREBASE_WEB_API_KEY="",
            FIREBASE_WEB_MESSAGING_SENDER_ID="sender",
            FIREBASE_WEB_APP_ID="app",
            FIREBASE_WEB_VAPID_KEY="vapid",
        ):
            response = FirebaseWebConfigView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["enabled"])

    def test_web_config_exposes_only_public_client_configuration(self):
        request = APIRequestFactory().get("/api/v1/notifications/web-config/")
        with self.settings(
            FIREBASE_ENABLED=True,
            FIREBASE_PROJECT_ID="project",
            FIREBASE_WEB_API_KEY="api-key",
            FIREBASE_WEB_AUTH_DOMAIN="project.firebaseapp.com",
            FIREBASE_WEB_STORAGE_BUCKET="project.firebasestorage.app",
            FIREBASE_WEB_MESSAGING_SENDER_ID="sender",
            FIREBASE_WEB_APP_ID="app-id",
            FIREBASE_WEB_MEASUREMENT_ID="G-test",
            FIREBASE_WEB_VAPID_KEY="public-vapid",
        ):
            response = FirebaseWebConfigView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["enabled"])
        self.assertEqual(response.data["firebase"]["projectId"], "project")
        self.assertEqual(response.data["firebase"]["appId"], "app-id")
        self.assertEqual(response.data["vapid_key"], "public-vapid")
        self.assertNotIn("credentials", response.data)

    def test_device_registration_reassigns_device_when_user_logs_into_same_installation(self):
        device = PushDevice.objects.create(
            user=self.user,
            installation_id="fid-device-shared",
            platform="android",
        )

        request = APIRequestFactory().post(
            "/api/v1/notifications/devices/",
            {
                "installation_id": device.installation_id,
                "platform": "android",
            },
            format="json",
        )
        force_authenticate(request, user=self.other_user)

        response = PushDeviceRegistrationView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        device.refresh_from_db()
        self.assertEqual(device.user_id, self.other_user.pk)
        self.assertTrue(device.is_active)


class PushDeliveryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="push-user",
            email="push-user@example.com",
            password="test-password",
        )
        self.notification = Notification.objects.create(
            user=self.user,
            notification_type=Notification.NotificationType.APPROVAL_APPROVED,
            title="Approved",
            body="Approved body",
            dedupe_key="push-test-notification",
        )

    @patch("notifications.push._firebase_app", return_value=object())
    @patch("notifications.push.messaging.send_each_for_multicast")
    def test_retry_sends_only_to_devices_that_have_not_succeeded(self, send_mock, _firebase_mock):
        sent_device = PushDevice.objects.create(
            user=self.user,
            installation_id="fid-already-sent",
            platform="android",
        )
        pending_device = PushDevice.objects.create(
            user=self.user,
            installation_id="fid-pending",
            platform="android",
        )
        NotificationDelivery.objects.create(
            notification=self.notification,
            device=sent_device,
            status=NotificationDelivery.Status.SENT,
            attempt_count=1,
        )

        send_mock.return_value = SimpleNamespace(
            responses=[SimpleNamespace(success=True, message_id="message-1", exception=None)]
        )

        with self.settings(FIREBASE_ENABLED=True):
            self.assertEqual(send_notification_push(self.notification.pk), 1)

        call_message = send_mock.call_args.args[0]
        self.assertEqual(call_message.fids, [pending_device.installation_id])
        pending_delivery = NotificationDelivery.objects.get(
            notification=self.notification,
            device=pending_device,
        )
        sent_delivery = NotificationDelivery.objects.get(
            notification=self.notification,
            device=sent_device,
        )
        self.assertEqual(pending_delivery.status, NotificationDelivery.Status.SENT)
        self.assertEqual(sent_delivery.attempt_count, 1)

    @patch("notifications.push._firebase_app", return_value=object())
    @patch("notifications.push.messaging.send_each_for_multicast")
    def test_webpush_click_link_is_attached_for_https(self, send_mock, _firebase_mock):
        web_device = PushDevice.objects.create(
            user=self.user,
            installation_id="fid-web-delivery",
            platform=PushDevice.Platform.WEB,
        )
        send_mock.return_value = SimpleNamespace(
            responses=[SimpleNamespace(success=True, message_id="web-message-1", exception=None)]
        )

        with self.settings(
            FIREBASE_ENABLED=True,
            FIREBASE_WEB_NOTIFICATION_LINK="https://erp.example.com/",
        ):
            self.assertEqual(send_notification_push(self.notification.pk), 1)

        message = send_mock.call_args.args[0]
        self.assertEqual(message.fids, [web_device.installation_id])
        self.assertEqual(
            message.webpush.fcm_options.link,
            "https://erp.example.com/",
        )
