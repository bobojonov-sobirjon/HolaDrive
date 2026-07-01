"""Shared admin user list filters and pagination helpers."""
from __future__ import annotations

from django.db.models import Q, QuerySet

from apps.accounts.models import CustomUser


def apply_admin_user_search(qs: QuerySet, search: str) -> QuerySet:
    search = (search or '').strip()
    if not search:
        return qs
    q = (
        Q(email__icontains=search)
        | Q(username__icontains=search)
        | Q(first_name__icontains=search)
        | Q(last_name__icontains=search)
        | Q(id_identification__icontains=search)
        | Q(phone_number__icontains=search)
    )
    if search.isdigit():
        q |= Q(id=int(search))
    return qs.filter(q)


def parse_admin_pagination(
    page_raw,
    page_size_raw,
    *,
    default_page_size: int = 10,
    max_page_size: int = 200,
) -> tuple[int, int]:
    page = max(1, int(page_raw or 1))
    page_size = int(page_size_raw or default_page_size)
    page_size = max(1, min(page_size, max_page_size))
    return page, page_size


def paginate_queryset(qs: QuerySet, page: int, page_size: int) -> tuple[list, int]:
    total_count = qs.count()
    start = (page - 1) * page_size
    end = start + page_size
    return list(qs[start:end]), total_count


def admin_user_search_snapshot(user: CustomUser, role: str) -> dict:
    return {
        'id': user.id,
        'role': role,
        'email': user.email,
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'full_name': user.get_full_name(),
        'phone_number': user.phone_number,
        'id_identification': user.id_identification,
        'is_active': user.is_active,
        'created_at': user.created_at,
    }
