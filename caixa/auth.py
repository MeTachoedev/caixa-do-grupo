"""Acesso compartilhado, sem atribuir identidade à pessoa selecionada."""

import hashlib
import hmac
import time

MAX_AGE = 8 * 60 * 60
IDLE = 30 * 60


def configured(secret):
    return isinstance(secret, str) and 12 <= len(secret) <= 128 and bool(secret.strip())


def fingerprint(secret):
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def authenticate(candidate, secret, store, now=None):
    if not configured(secret) or not isinstance(candidate, str) or not 1 <= len(candidate) <= 128:
        return None, "Informe a senha do grupo."
    now = time.time() if now is None else now
    if not store.admit_login(now):
        return None, "Muitas tentativas. Aguarde um minuto e tente novamente."
    if not hmac.compare_digest(candidate.encode("utf-8"), secret.encode("utf-8")):
        return None, "Senha incorreta."
    return {"created": now, "last": now, "version": fingerprint(secret)}, None


def authorized(session, secret, now=None):
    if not configured(secret) or not isinstance(session, dict):
        return False
    now = time.time() if now is None else now
    try:
        return (
            hmac.compare_digest(session["version"], fingerprint(secret))
            and 0 <= now - session["created"] < MAX_AGE
            and 0 <= now - session["last"] < IDLE
        )
    except (KeyError, TypeError):
        return False
