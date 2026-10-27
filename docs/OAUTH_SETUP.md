# OAuth Provider Setup Guide

To link production cloud accounts, register OAuth 2.0 applications with each provider:

---

## 1. Google Drive (Google Cloud Console)
1. Navigate to [Google Cloud Console](https://console.cloud.google.com/).
2. Create or select a project (e.g. `MSEDCL-Secure-Transfers`).
3. Under **APIs & Services > Credentials**, create an **OAuth 2.0 Client ID** (Web application).
4. Add Authorized Redirect URI:
   `http://127.0.0.1:8000/api/v1/accounts/google/callback`
5. Enable **Google Drive API**.
6. Set the following in `.env`:
   - `GOOGLE_CLIENT_ID`
   - `GOOGLE_CLIENT_SECRET`

---

## 2. Microsoft OneDrive (Azure Portal / Microsoft Entra)
1. Go to [Azure Portal App Registrations](https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade).
2. Click **New registration** (Accounts in any organizational directory).
3. Under **Authentication**, add a Web platform redirect URI:
   `http://127.0.0.1:8000/api/v1/accounts/onedrive/callback`
4. Under **API Permissions**, grant:
   - `Files.ReadWrite.All`
   - `offline_access`
   - `User.Read`
5. Create a client secret under **Certificates & secrets**.
6. Set `MICROSOFT_CLIENT_ID` and `MICROSOFT_CLIENT_SECRET` in `.env`.

---

## 3. Dropbox (Dropbox App Console)
1. Visit the [Dropbox App Console](https://www.dropbox.com/developers/apps).
2. Create an App with **Scoped access** and **Full Dropbox** access.
3. In the App settings, add the redirect URI:
   `http://127.0.0.1:8000/api/v1/accounts/dropbox/callback`
4. Under Permissions, enable `files.metadata.read`, `files.content.read`, `files.content.write`.
5. Set `DROPBOX_CLIENT_ID` and `DROPBOX_CLIENT_SECRET` in `.env`.
