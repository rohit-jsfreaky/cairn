"""Passwords never go into memory.

Cairn remembers *that* a step types a password, never *which* password. The trail stored in
Sibyl holds a marker like `secret: "password"`; the value itself is looked up at replay time
from the machine it runs on.

Two places are checked, in order:

1. An environment variable, which is what `package/CLAUDE.md` asks for:
       CAIRN_SECRET_BILLING_ACME_COM_PASSWORD
2. `~/.cairn/secrets.json`, which is easier for a person to manage:
       { "billing.acme.com": { "password": "..." } }

Neither lives in the repo, and neither is ever written to memory. If a secret is missing,
replay stops and says exactly which one to set — it never guesses and never falls back to
something stored earlier.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
from pathlib import Path

SECRETS_FILE = Path.home() / ".cairn" / "secrets.json"
ENV_PREFIX = "CAIRN_SECRET"


class MissingSecret(RuntimeError):
    """A step needs a password that this machine does not have.

    Deliberately loud. Quietly skipping the field would leave the browser sitting on a
    login page and the failure would surface three steps later as something confusing.
    """


def env_var_name(domain: str, field: str) -> str:
    """The environment variable a given secret would come from."""
    slug = re.sub(r"[^A-Za-z0-9]+", "_", f"{domain}_{field}").strip("_").upper()
    return f"{ENV_PREFIX}_{slug}"


def resolve(domain: str, field: str, *, secrets_file: Path | None = None) -> str:
    """Find one secret, or explain precisely how to provide it."""
    from_env = os.environ.get(env_var_name(domain, field))
    if from_env:
        return from_env

    path = secrets_file or SECRETS_FILE
    from_file = _read_file(path).get(domain, {}).get(field)
    if from_file:
        return str(from_file)

    raise MissingSecret(
        f'Cairn needs the "{field}" for {domain}, and never stores it. Provide it either as '
        f"the environment variable {env_var_name(domain, field)}, or in {path} as "
        f'{{"{domain}": {{"{field}": "..."}}}}.'
    )


def store(domain: str, field: str, value: str, *, secrets_file: Path | None = None) -> Path:
    """Write one secret to the local secrets file, for convenience.

    Only ever called because a person asked for it. The file is created private to the
    user where the platform allows it.
    """
    path = secrets_file or SECRETS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)

    everything = _read_file(path)
    everything.setdefault(domain, {})[field] = value
    path.write_text(json.dumps(everything, indent=2), encoding="utf-8")

    # Windows ignores POSIX modes; the file still sits in the user's own profile.
    with contextlib.suppress(OSError):
        path.chmod(0o600)
    return path


def known_fields(domain: str, *, secrets_file: Path | None = None) -> list[str]:
    """Which secrets this machine already has for a site. Names only, never values."""
    return sorted(_read_file(secrets_file or SECRETS_FILE).get(domain, {}))


def _read_file(path: Path) -> dict[str, dict[str, str]]:
    if not path.is_file():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return loaded if isinstance(loaded, dict) else {}
