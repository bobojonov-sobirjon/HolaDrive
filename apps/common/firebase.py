"""Shared Firebase Admin SDK initialization (FCM + Auth ID token verification)."""
import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)

try:
    import firebase_admin
    from firebase_admin import auth as firebase_auth
    from firebase_admin import credentials
except ImportError:  # pragma: no cover
    firebase_admin = None
    firebase_auth = None
    credentials = None

_firebase_app: Optional['firebase_admin.App'] = None


def _service_account_info_from_env() -> Optional[dict]:
    required_keys = [
        'FIREBASE_TYPE',
        'FIREBASE_PROJECT_ID',
        'FIREBASE_PRIVATE_KEY_ID',
        'FIREBASE_PRIVATE_KEY',
        'FIREBASE_CLIENT_EMAIL',
        'FIREBASE_CLIENT_ID',
        'FIREBASE_AUTH_URI',
        'FIREBASE_TOKEN_URI',
        'FIREBASE_AUTH_PROVIDER_X509_CERT_URL',
        'FIREBASE_CLIENT_X509_CERT_URL',
    ]
    env = {k: os.getenv(k) for k in required_keys}
    if not all(env.values()):
        return None
    private_key = env['FIREBASE_PRIVATE_KEY'] or ''
    private_key = private_key.replace('\\n', '\n')
    return {
        'type': env['FIREBASE_TYPE'],
        'project_id': env['FIREBASE_PROJECT_ID'],
        'private_key_id': env['FIREBASE_PRIVATE_KEY_ID'],
        'private_key': private_key,
        'client_email': env['FIREBASE_CLIENT_EMAIL'],
        'client_id': env['FIREBASE_CLIENT_ID'],
        'auth_uri': env['FIREBASE_AUTH_URI'],
        'token_uri': env['FIREBASE_TOKEN_URI'],
        'auth_provider_x509_cert_url': env['FIREBASE_AUTH_PROVIDER_X509_CERT_URL'],
        'client_x509_cert_url': env['FIREBASE_CLIENT_X509_CERT_URL'],
    }


def get_firebase_app():
    """Return the default Firebase app, initializing from FIREBASE_* env vars if needed."""
    global _firebase_app

    if firebase_admin is None or credentials is None:
        return None

    if _firebase_app is not None:
        return _firebase_app

    try:
        _firebase_app = firebase_admin.get_app()
        return _firebase_app
    except ValueError:
        pass

    info = _service_account_info_from_env()
    if not info:
        logger.warning('Firebase env vars incomplete — cannot initialize Firebase Admin SDK')
        return None

    try:
        cred = credentials.Certificate(info)
        _firebase_app = firebase_admin.initialize_app(cred)
        logger.info('Firebase Admin SDK initialized (project_id=%s)', info.get('project_id'))
        return _firebase_app
    except Exception:
        logger.exception('Firebase Admin SDK initialization failed')
        return None


def verify_firebase_id_token(id_token: str, *, check_revoked: bool = True) -> dict[str, Any]:
    """
    Verify a Firebase Auth ID token from the mobile client (Google / Apple / Facebook via Firebase).

    Raises:
        RuntimeError: SDK not configured
        ValueError: invalid/expired token (message safe for API clients)
    """
    if not id_token or not str(id_token).strip():
        raise ValueError('id_token is required')

    if firebase_auth is None or get_firebase_app() is None:
        raise RuntimeError('Firebase is not configured on the server')

    try:
        return firebase_auth.verify_id_token(str(id_token).strip(), check_revoked=check_revoked)
    except firebase_auth.ExpiredIdTokenError:
        raise ValueError('Firebase ID token has expired. Sign in again in the app.') from None
    except firebase_auth.RevokedIdTokenError:
        raise ValueError('Firebase ID token was revoked. Sign in again in the app.') from None
    except firebase_auth.InvalidIdTokenError:
        raise ValueError('Invalid Firebase ID token.') from None
    except Exception as exc:
        logger.warning('Firebase verify_id_token failed: %s', exc)
        raise ValueError('Could not verify Firebase ID token.') from None
