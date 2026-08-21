def client_ip(request) -> str:
    """Best-effort client IP (first X-Forwarded-For hop, else REMOTE_ADDR)."""
    forwarded = (request.META.get('HTTP_X_FORWARDED_FOR') or '').split(',')
    for part in forwarded:
        ip = part.strip()
        if ip:
            return ip[:45]
    return (request.META.get('REMOTE_ADDR') or '0.0.0.0')[:45]
