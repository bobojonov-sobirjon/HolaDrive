"""Payment helpers (sync; call from async via sync_to_async)."""

from django.contrib.auth import get_user_model

from .models import SavedCard

User = get_user_model()


def holder_role_for_user(user: User) -> str:
    """
    Driver group -> driver saved-card bucket; otherwise rider (includes Rider group or no group).
    """
    names = set(user.groups.values_list('name', flat=True))
    if 'Driver' in names:
        return SavedCard.HolderRole.DRIVER
    return SavedCard.HolderRole.RIDER
