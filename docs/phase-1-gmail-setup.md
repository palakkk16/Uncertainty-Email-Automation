# Phase 1 — Gmail API and desktop OAuth

Do this once in the Google account that will send the test message. The script requests only `https://www.googleapis.com/auth/gmail.send`.

Stop if Google asks you to attach a billing account. This project stays at $0 only when the project has no billing account and only the Gmail API is enabled.

## 1. Create a project with no billing

1. Open [Google Cloud Console](https://console.cloud.google.com/).
2. Open the project picker in the top bar and choose **New project**.
3. Name it `uncertain-email` and choose **Create**.
4. Select that project. If a banner offers to link a billing account, dismiss it. Do not open **Billing** and do not upgrade.

## 2. Enable only the Gmail API

1. Go to **APIs & Services → Library** (or visit the [Gmail API page](https://console.cloud.google.com/apis/library/gmail.googleapis.com)).
2. Open **Gmail API** and choose **Enable**.
3. Do not enable Vertex AI, Maps, Cloud Storage, or any other API.

## 3. Configure the consent screen and stay in Testing

The console labels this area **Google Auth platform**.

1. Go to **Google Auth platform**. If you see **Get started**, choose it.
2. **App information:** set the app name to `UNCERTAIN-EMAIL`. Set **User support email** to your own Gmail address. Continue.
3. **Audience:** choose **External** for a personal Gmail account (choose **Internal** only if this project lives in your own Google Workspace organization). Continue.
4. **Contact information:** enter your own Gmail address. Continue.
5. Agree to the Google API Services User Data Policy if you accept it, then **Create**.
6. Open **Audience**. Leave **Publishing status** on **Testing**. Do not choose **Publish app**.
7. Under **Test users**, choose **Add users**, enter the same Gmail address you will sign in with, and save.
8. Open **Data Access → Add or remove scopes**. Add only this scope:

   `https://www.googleapis.com/auth/gmail.send`

   Do not add `gmail.readonly`, `gmail.modify`, `gmail.compose`, or `https://mail.google.com/`.

## 4. Create a Desktop OAuth client

1. Open **Google Auth platform → Clients** (older consoles show **APIs & Services → Credentials**).
2. Choose **Create client**.
3. Application type: **Desktop app**. Name it `uncertain-email-desktop`.
4. Create the client and download the JSON.
5. On your machine, from the project root:

   ```bash
   mkdir -p credentials
   ```

   Move the downloaded file to `credentials/client_secret.json`.
6. That path is gitignored. Do not commit it, paste it into chat, or copy the `client_secret` value into `.env`.

## 5. Fill in `.env`

```bash
cp .env.example .env
```

Set:

| Variable | What to put |
| --- | --- |
| `CREDENTIALS_PATH` | `credentials/client_secret.json` |
| `TOKEN_PATH` | `credentials/token.json` |
| `GMAIL_SENDER` | The Gmail address you added as a test user. It must be the account that signs in. |
| `TEST_RECIPIENT` | A mailbox you control. The same address as the sender is fine. |
| `TEST_SUBJECT` | Any non-empty subject. |
| `TEST_BODY` | Any non-empty body. |

The first successful login writes `credentials/token.json`. That file is gitignored. The script never prints it.

## 6. Send one test message

```bash
source .venv/bin/activate
python scripts/gmail_send_test.py
```

A browser opens on the machine running the script. Sign in as the test user and allow send access. The terminal should print `Sent. Gmail message id: ...`.

If the cached token later fails, delete `credentials/token.json` and run the script again. Testing-mode refresh tokens last 7 days. Publishing the app is not the fix for this project.

## If a send is rejected

- The signed-in Gmail address is not listed under **Test users**.
- The consent screen was published, or a scope other than `gmail.send` was added.
- `GMAIL_SENDER` is not the account that completed the browser login.
- A different API was enabled, or a billing account was linked. Disable the extra API and remove billing if you added it by mistake.
