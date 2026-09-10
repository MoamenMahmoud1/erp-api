from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver

from accounts.models import Role
from authsession.cache import delete_all_auth_session_caches, delete_auth_session_caches
from authsession.models import AuthSession


def _invalidate_users(user_ids):
    user_ids = tuple({int(user_id) for user_id in user_ids if user_id is not None})
    if not user_ids:
        return
    session_ids = AuthSession.objects.filter(
        user_id__in=user_ids,
        revoked_at__isnull=True,
    ).values_list("pk", flat=True)
    delete_auth_session_caches(session_ids)


def _invalidate_group_users(group_id):
    if not group_id:
        return
    user_ids = Group.objects.filter(pk=group_id).values_list("user__pk", flat=True)
    _invalidate_users(user_ids)


User = get_user_model()


@receiver(m2m_changed, sender=User.groups.through)
def invalidate_user_group_permissions(sender, instance, action, reverse, pk_set, **kwargs):
    if action not in {"post_add", "post_remove", "post_clear"}:
        return
    if reverse:
        _invalidate_group_users(instance.pk)
        return
    _invalidate_users((instance.pk,))


@receiver(m2m_changed, sender=User.user_permissions.through)
def invalidate_user_direct_permissions(sender, instance, action, **kwargs):
    if action in {"post_add", "post_remove", "post_clear"}:
        _invalidate_users((instance.pk,))


@receiver(m2m_changed, sender=Group.permissions.through)
def invalidate_group_permissions(sender, instance, action, **kwargs):
    if action in {"post_add", "post_remove", "post_clear"}:
        _invalidate_group_users(instance.pk)


@receiver(post_save, sender=User)
def invalidate_user_session_cache(sender, instance, **kwargs):
    """Drop cached auth state when activation or privileged flags change."""
    _invalidate_users((instance.pk,))


@receiver(post_save, sender=Group)
def invalidate_new_group_session_caches(sender, instance, created, **kwargs):
    """Drop authorization snapshots when a new RBAC group is introduced."""
    if created:
        delete_all_auth_session_caches()


@receiver(post_save, sender=Role)
def invalidate_role_level_cache(sender, instance, **kwargs):
    _invalidate_group_users(instance.group_id)


@receiver(post_delete, sender=Role)
def invalidate_deleted_role_cache(sender, instance, **kwargs):
    _invalidate_group_users(instance.group_id)
