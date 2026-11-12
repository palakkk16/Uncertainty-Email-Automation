#!/usr/bin/env python3
"""Replace TOKEN_PATH with a new gmail.send desktop login.

The API never opens a browser. Run this on the same machine, sign in once,
then the next SEND can refresh and send. This script does not send mail.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gmail_send_test import load_config, run_desktop_login, write_token


def main() -> int:
    config = load_config()
    creds = run_desktop_login(config.credentials_path)
    write_token(creds, config.token_path)
    print(f"Wrote {config.token_path}. The next SEND will use this token.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
