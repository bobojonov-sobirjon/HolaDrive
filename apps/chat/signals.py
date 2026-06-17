from __future__ import annotations

from django.contrib.auth.models import Group
from django.db.models.signals import post_migrate
from django.dispatch import receiver


@receiver(post_migrate)
def ensure_admin_group(sender, **kwargs):
    """
    Keep an 'Admin' group present and assign it to all superusers.

    Note: 'Admin' here is an app-level concept (support operators). We still
    use Django's `is_superuser` / `is_staff` for permission gating.
    """
    try:
        admin_group, _ = Group.objects.get_or_create(name='Admin')
    except Exception:
        return

    # Assign group to all superusers (best effort).
    try:
        from apps.accounts.models import CustomUser

        qs = CustomUser.objects.filter(is_superuser=True).only('id')
        for u in qs:
            try:
                u.groups.add(admin_group)
            except Exception:
                pass
    except Exception:
        # Apps may not be ready in some migration contexts.
        return

