"""Offline defaults for the chat suite.

POST /chat refuses to extract when GEMINI_API_KEY is empty. The chat tests
replace the SDK client and do not use the network. A placeholder satisfies
that guard. It is not a credential and it is not sent anywhere.
"""

from __future__ import annotations

import os

if not os.environ.get("GEMINI_API_KEY", "").strip():
    os.environ["GEMINI_API_KEY"] = "test-not-a-real-key"
