import firebase_admin
from django.conf import settings
from firebase_admin import credentials, messaging

from .models import Notification, NotificationDelivery, PushDevice


class PushNotificationsNotConfigured(RuntimeError):
    pass


class PushDeliveryPartiallyFailed(RuntimeError):
    pass


def _firebase_app():
    if not settings.FIREBASE_ENABLED:
        raise PushNotificationsNotConfigured("Firebase push notifications are disabled.")

    try:
        return firebase_admin.get_app()
    except ValueError:
        try:
            if settings.FIREBASE_CREDENTIALS_FILE:
                credential = credentials.Certificate(settings.FIREBASE_CREDENTIALS_FILE)
            else:
                credential = credentials.ApplicationDefault()

            options = {}
            if settings.FIREBASE_PROJECT_ID:
                options["projectId"] = settings.FIREBASE_PROJECT_ID
            return firebase_admin.initialize_app(credential, options=options or None)
        except Exception as exc:
            raise PushNotificationsNotConfigured(
                "Firebase Admin SDK could not be initialized."
            ) from exc


def _chunks(values, size=500):
    for index in range(0, len(values), size):
        yield values[index:index + size]


def _get_pending_devices(notification: Notification) -> list[PushDevice]:
    devices = list(
        PushDevice.objects.filter(
            user_id=notification.user_id,
            is_active=True,
        ).order_by("id")
    )
    if not devices:
        return []

    deliveries = {
        delivery.device_id: delivery
        for delivery in NotificationDelivery.objects.filter(
            notification=notification,
            device__in=devices,
        )
    }

    pending_devices = []
    for device in devices:
        delivery = deliveries.get(device.id)
        if delivery is None:
            NotificationDelivery.objects.create(
                notification=notification,
                device=device,
            )
            pending_devices.append(device)
        elif delivery.status != NotificationDelivery.Status.SENT:
            pending_devices.append(device)

    return pending_devices


def send_notification_push(notification_id: int) -> int:
    app = _firebase_app()
    notification = Notification.objects.get(pk=notification_id)
    devices = _get_pending_devices(notification)
    if not devices:
        return 0

    delivery_by_device_id = {
        delivery.device_id: delivery
        for delivery in NotificationDelivery.objects.filter(
            notification=notification,
            device_id__in=[device.id for device in devices],
        )
    }

    sent_count = 0
    failed_count = 0
    data = {
        "notification_id": str(notification.pk),
        "notification_type": str(notification.notification_type),
        "target_type": str(notification.target_type or ""),
        "target_id": str(notification.target_id or ""),
    }
    data.update({str(key): str(value) for key, value in (notification.data or {}).items()})

    for device_chunk in _chunks(devices):
        fids = [device.installation_id for device in device_chunk]
        message = messaging.MulticastMessage(
            fids=fids,
            notification=messaging.Notification(
                title=notification.title,
                body=notification.body,
            ),
            data=data,
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    channel_id=settings.FCM_ANDROID_CHANNEL_ID,
                ),
            ),
            apns=messaging.APNSConfig(
                headers={"apns-priority": "10"},
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(sound="default"),
                ),
            ),
        )
        response = messaging.send_each_for_multicast(message, app=app)

        for device, send_response in zip(device_chunk, response.responses):
            delivery = delivery_by_device_id[device.id]
            if send_response.success:
                delivery.mark_sent(send_response.message_id)
                sent_count += 1
                continue

            error = send_response.exception
            delivery.mark_failed(str(error) if error else "FCM delivery failed.")
            failed_count += 1

            error_code = getattr(error, "code", "")
            if error_code in {
                "messaging/registration-token-not-registered",
                "messaging/invalid-argument",
            }:
                device.deactivate(error_code)

    if failed_count:
        raise PushDeliveryPartiallyFailed(
            f"{failed_count} push notification deliveries failed after {sent_count} succeeded."
        )

    return sent_count
