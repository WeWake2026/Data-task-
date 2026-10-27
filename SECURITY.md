# Security Policy - Secure Cloud Transfer Manager

## 1. Authentication & Session Protection
- **Argon2id Hashing**: Passwords stored as Argon2id hashes with memory cost protection.
- **HttpOnly Cookies**: Session cookies marked `HttpOnly`, `SameSite=Lax`, and `Secure` (in HTTPS).
- **No Client Credential Exposure**: Provider OAuth client secrets, refresh tokens, and internal cryptographic keys are never sent in API responses or stored in browser `localStorage`.
- **Generic Auth Errors**: Authentication failures return identical messages to prevent username harvesting.

## 2. Cloud Authorization & Scopes
- **OAuth 2.0 with PKCE**: Cloud integrations use Authorization Code flow with PKCE (`code_challenge` / `code_verifier`).
- **Token Encryption at Rest**: All cloud provider OAuth refresh tokens are encrypted using AES-128/Fernet key rotation before storage in PostgreSQL/SQLite.
- **Least Privilege**: Only `drive.file` and non-invasive folder permissions requested.

## 3. Data Integrity & Verification
- **Cryptographic Verification**: File transfers are only marked verified after SHA-256 integrity match confirmation.
- **Non-Destructive Operations**: Source files are never deleted or truncated during or after transfer.
- **Conflict Handling**: Idempotency keys prevent duplicate job submissions.

## 4. Windows Agent Security
- **Per-Agent Enrollment Tokens**: Agents authenticate over TLS with hashed credentials.
- **Restricted Directories**: Agents only access authorized user folders; path traversal attempts (`../`) are blocked.
- **Revocation**: Compromised or decommissioned agents can be instantly revoked by administrators.
