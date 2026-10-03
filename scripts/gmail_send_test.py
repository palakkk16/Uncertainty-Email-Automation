#!/usr/bin/env python3
"""Send one Gmail message after a desktop OAuth login (Phase 1 only).

Later phases choose ASK vs SEND. This script does not. It sends once when
configuration is complete, and it exits before any Gmail call when it is not.
"""

from __future__ import annotations

import base64
import os
import sys
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path

from dotenv import load_dotenv
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Least privilege: send is allowed; reading or changing mail is not.
GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"

REQUIRED_ENV = (
    "CREDENTIALS_PATH",
    "TOKEN_PATH",
    "GMAIL_SENDER",
    "TEST_RECIPIENT",
    "TEST_SUBJECT",
    "TEST_BODY",
)

# Same strings as .env.example. Real addresses do not belong in source.
PLACEHOLDER_VALUES = {
    "GMAIL_SENDER": "your-sender@gmail.com",
    "TEST_RECIPIENT": "your-recipient@gmail.com",
}


@dataclass(frozen=True)
class SendConfig:
    credentials_path: Path
    token_path: Path
    sender: str
    recipient: str
    subject: str
    body: str


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_environment() -> dict[str, str]:
    """Load .env without overriding variables already set in the process."""
    load_dotenv(project_root() / ".env")
    missing = [key for key in REQUIRED_ENV if not os.environ.get(key, "").strip()]
    if not missing:
        return {key: os.environ[key].strip() for key in REQUIRED_ENV}
    joined = ", ".join(missing)
    raise SystemExit(
        f"Missing required environment variables: {joined}.\n"
        "Copy .env.example to .env in the project root and set every value.\n"
        "Setup steps: docs/phase-1-gmail-setup.md\n"
        "Refusing to send."
    )


def reject_placeholders(values: dict[str, str]) -> None:
    stale = [key for key, sample in PLACEHOLDER_VALUES.items() if values[key] == sample]
    if not stale:
        return
    joined = ", ".join(stale)
    raise SystemExit(
        f"Still using placeholder values for: {joined}.\n"
        "Edit .env before running. Refusing to send."
    )


def require_email(key: str, value: str) -> None:
    local, separator, domain = value.partition("@")
    if separator and local and domain and "." in domain and not any(ch.isspace() for ch in value):
        return
    raise SystemExit(f"{key} must be one email address. Fix .env. Refusing to send.")


def resolve_path(raw: str) -> Path:
    path = Path(raw).expanduser()
    if path.is_absolute():
        return path
    return project_root() / path


def assert_gitignored_secret(path: Path) -> None:
    """Block secret paths that .gitignore would not cover inside this repo."""
    try:
        relative = path.resolve().relative_to(project_root().resolve())
    except ValueError:
        return
    name = relative.name
    if relative.parts[0] == "credentials":
        return
    if name in {"token.json", ".env"} or name.startswith("client_secret"):
        return
    raise SystemExit(
        f"{relative} is inside the project and is not covered by .gitignore.\n"
        "Use credentials/client_secret.json and credentials/token.json.\n"
        "Refusing to send."
    )


def require_client_secret(path: Path) -> None:
    if path.is_file() and path.stat().st_size > 0:
        return
    raise SystemExit(
        f"OAuth client secret not found at {path}.\n"
        "Create a Google Cloud project with no billing account, enable only the Gmail API, "
        "leave the OAuth consent screen in Testing, add your Gmail as a test user, "
        "create a Desktop app client, and download its JSON to this path.\n"
        "Click-path: docs/phase-1-gmail-setup.md\n"
        "Refusing to open a browser or send mail."
    )


def load_config() -> SendConfig:
    values = load_environment()
    reject_placeholders(values)
    require_email("GMAIL_SENDER", values["GMAIL_SENDER"])
    require_email("TEST_RECIPIENT", values["TEST_RECIPIENT"])
    credentials_path = resolve_path(values["CREDENTIALS_PATH"])
    token_path = resolve_path(values["TOKEN_PATH"])
    assert_gitignored_secret(credentials_path)
    assert_gitignored_secret(token_path)
    require_client_secret(credentials_path)
    return SendConfig(
        credentials_path=credentials_path,
        token_path=token_path,
        sender=values["GMAIL_SENDER"],
        recipient=values["TEST_RECIPIENT"],
        subject=values["TEST_SUBJECT"],
        body=values["TEST_BODY"],
    )


def scopes_are_send_only(creds: Credentials) -> bool:
    # A cached token from a broader login must not be reused.
    return set(creds.scopes or []) == {GMAIL_SEND_SCOPE}


def read_cached_credentials(token_path: Path) -> Credentials | None:
    if not token_path.is_file():
        return None
    try:
        return Credentials.from_authorized_user_file(str(token_path), [GMAIL_SEND_SCOPE])
    except (ValueError, OSError):
        # A corrupt cache can contain a refresh token. Do not print it.
        return None


def write_token(creds: Credentials, token_path: Path) -> None:
    token_path.parent.mkdir(parents=True, exist_ok=True)
    # Owner-only: the file holds a refresh token.
    fd = os.open(token_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, creds.to_json().encode("utf-8"))
    finally:
        os.close(fd)
    os.chmod(token_path, 0o600)
    # Restrict the secrets directory, never the project root.
    if token_path.parent.resolve() != project_root().resolve():
        os.chmod(token_path.parent, 0o700)


def refresh_cached(creds: Credentials, token_path: Path) -> Credentials | None:
    if not (creds.expired and creds.refresh_token and scopes_are_send_only(creds)):
        return None
    try:
        creds.refresh(Request())
    except RefreshError:
        # RefreshError can include token material. Drop the cache and sign in again.
        return None
    write_token(creds, token_path)
    return creds


def start_installed_flow(credentials_path: Path) -> InstalledAppFlow:
    try:
        return InstalledAppFlow.from_client_secrets_file(
            str(credentials_path), [GMAIL_SEND_SCOPE]
        )
    except (ValueError, OSError):
        raise SystemExit(
            "Could not read the OAuth client secret. Re-download the Desktop client JSON.\n"
            "File contents were not printed. Refusing to send."
        ) from None


def run_desktop_login(credentials_path: Path) -> Credentials:
    flow = start_installed_flow(credentials_path)
    # prompt=consent so Google issues a refresh token, not only a one-hour access token.
    creds = flow.run_local_server(port=0, prompt="consent")
    if scopes_are_send_only(creds):
        return creds
    raise SystemExit(
        "Google granted a scope set other than gmail.send alone.\n"
        "Remove this app under Google Account permissions, then run again.\n"
        "Refusing to store a token or send mail."
    )


def authorize(credentials_path: Path, token_path: Path) -> Credentials:
    cached = read_cached_credentials(token_path)
    if cached and cached.valid and scopes_are_send_only(cached):
        return cached
    if cached:
        refreshed = refresh_cached(cached, token_path)
        if refreshed:
            return refreshed
    require_client_secret(credentials_path)
    creds = run_desktop_login(credentials_path)
    write_token(creds, token_path)
    return creds


def build_raw_message(sender: str, recipient: str, subject: str, body: str) -> dict[str, str]:
    # EmailMessage emits the raw RFC 2822/5322 bytes Gmail's `raw` field expects.
    message = EmailMessage()
    message["To"] = recipient
    message["From"] = sender
    message["Subject"] = subject
    message.set_content(body)
    encoded = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
    return {"raw": encoded}


def send_test_message(service: object, raw_body: dict[str, str]) -> str:
    try:
        sent = service.users().messages().send(userId="me", body=raw_body).execute()
    except HttpError as exc:
        status = getattr(getattr(exc, "resp", None), "status", "unknown")
        raise SystemExit(
            f"Gmail API rejected the send (HTTP {status}).\n"
            "Confirm only the Gmail API is enabled, the consent screen is in Testing, "
            "and the signed-in account is a test user. No message id was returned."
        ) from None
    message_id = sent.get("id") if isinstance(sent, dict) else None
    if not message_id:
        raise SystemExit("Gmail API returned no message id. Treat the send as unverified.")
    return str(message_id)


def main() -> int:
    config = load_config()
    creds = authorize(config.credentials_path, config.token_path)
    service = build("gmail", "v1", credentials=creds)
    raw_body = build_raw_message(config.sender, config.recipient, config.subject, config.body)
    message_id = send_test_message(service, raw_body)
    print(f"Sent. Gmail message id: {message_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
