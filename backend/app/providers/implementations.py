from typing import List, Dict, Any, Optional
import urllib.parse
from backend.app.providers.base import ProviderAdapter
from backend.app.config import settings

class GoogleDriveAdapter(ProviderAdapter):
    def provider_id(self) -> str:
        return "google-drive"

    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "browser_oauth": True,
            "device_authorization": False,  # Google Drive explicitly restricts RFC 8628 for pure web clients
            "qr_assisted_auth": True,       # QR code encodes official browser OAuth redirect URL for phone scanning
            "refresh_token": True,
            "token_revocation": True,
            "folder_selection": True,
            "resumable_upload": True
        }

    def get_authorization_url(self, state: str) -> str:
        if not settings.GOOGLE_CLIENT_ID:
            return "https://accounts.google.com/o/oauth2/v2/auth?prompt_config_missing=true"
        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": "https://www.googleapis.com/auth/drive.file https://www.googleapis.com/auth/userinfo.email",
            "access_type": "offline",
            "prompt": "consent",
            "state": state
        }
        return f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"

    def exchange_code_for_tokens(self, code: str, code_verifier: Optional[str] = None) -> Dict[str, Any]:
        # Production would make POST https://oauth2.googleapis.com/token
        return {
            "access_token": f"ya29.simulated_gdrive_access_{code[:8]}",
            "refresh_token": f"1//simulated_gdrive_refresh_{code[:8]}",
            "expires_in": 3600,
            "token_type": "Bearer"
        }

    def list_files(self, path: str, token: str) -> List[Dict[str, Any]]:
        return [
            {"id": "g-file-1", "name": "Q3_Audit_Vault.tar.gz", "size": 128849018880, "is_folder": False},
            {"id": "g-folder-1", "name": "Compliance_Records", "size": 0, "is_folder": True}
        ]

    def get_file_metadata(self, file_id_or_path: str, token: str) -> Dict[str, Any]:
        return {
            "id": file_id_or_path,
            "size": 1024 * 1024 * 50,
            "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        }

    def create_resumable_upload_session(self, path: str, file_size: int, token: str) -> str:
        return f"https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable&upload_id=sess_{file_size}"

    def upload_chunk(self, session_url: str, chunk_data: bytes, start_byte: int, total_bytes: int, token: str) -> Dict[str, Any]:
        return {"status": "in_progress", "bytes_received": start_byte + len(chunk_data)}

    def verify_integrity(self, destination_path: str, expected_sha256: str, token: str) -> bool:
        return True


class OneDriveAdapter(ProviderAdapter):
    def provider_id(self) -> str:
        return "onedrive"

    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "browser_oauth": True,
            "device_authorization": True,   # Microsoft Identity Platform supports RFC 8628 device flow
            "qr_assisted_auth": True,       # QR code encodes verification URL (https://microsoft.com/devicelogin)
            "refresh_token": True,
            "token_revocation": True,
            "folder_selection": True,
            "resumable_upload": True
        }

    def get_authorization_url(self, state: str) -> str:
        if not settings.MICROSOFT_CLIENT_ID:
            return "https://login.microsoftonline.com/common/oauth2/v2.0/authorize?prompt_config_missing=true"
        params = {
            "client_id": settings.MICROSOFT_CLIENT_ID,
            "response_type": "code",
            "redirect_uri": settings.MICROSOFT_REDIRECT_URI,
            "scope": "Files.ReadWrite.All offline_access User.Read",
            "state": state
        }
        return f"https://login.microsoftonline.com/common/oauth2/v2.0/authorize?{urllib.parse.urlencode(params)}"

    def exchange_code_for_tokens(self, code: str, code_verifier: Optional[str] = None) -> Dict[str, Any]:
        return {
            "access_token": f"EwB4.simulated_onedrive_access_{code[:8]}",
            "refresh_token": f"M.R3_simulated_onedrive_refresh_{code[:8]}",
            "expires_in": 3600,
            "token_type": "Bearer"
        }

    def list_files(self, path: str, token: str) -> List[Dict[str, Any]]:
        return [
            {"id": "ms-file-1", "name": "Grid_Telemetry_2026.csv", "size": 64424509440, "is_folder": False}
        ]

    def get_file_metadata(self, file_id_or_path: str, token: str) -> Dict[str, Any]:
        return {"id": file_id_or_path, "size": 64424509440, "quickXorHash": "xyz"}

    def create_resumable_upload_session(self, path: str, file_size: int, token: str) -> str:
        return f"https://graph.microsoft.com/v1.0/me/drive/items/root:/{path}:/createUploadSession"

    def upload_chunk(self, session_url: str, chunk_data: bytes, start_byte: int, total_bytes: int, token: str) -> Dict[str, Any]:
        return {"status": "in_progress", "nextExpectedRanges": [f"{start_byte + len(chunk_data)}-{total_bytes-1}"]}

    def verify_integrity(self, destination_path: str, expected_sha256: str, token: str) -> bool:
        return True


class DropboxAdapter(ProviderAdapter):
    def provider_id(self) -> str:
        return "dropbox"

    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "browser_oauth": True,
            "device_authorization": False,  # Dropbox standard OAuth uses browser PKCE
            "qr_assisted_auth": True,       # QR code encodes official Dropbox OAuth URL
            "refresh_token": True,
            "token_revocation": True,
            "folder_selection": True,
            "resumable_upload": True
        }

    def get_authorization_url(self, state: str) -> str:
        if not settings.DROPBOX_CLIENT_ID:
            return "https://www.dropbox.com/oauth2/authorize?prompt_config_missing=true"
        params = {
            "client_id": settings.DROPBOX_CLIENT_ID,
            "response_type": "code",
            "redirect_uri": settings.DROPBOX_REDIRECT_URI,
            "token_access_type": "offline",
            "state": state
        }
        return f"https://www.dropbox.com/oauth2/authorize?{urllib.parse.urlencode(params)}"

    def exchange_code_for_tokens(self, code: str, code_verifier: Optional[str] = None) -> Dict[str, Any]:
        return {
            "access_token": f"sl.simulated_dropbox_access_{code[:8]}",
            "refresh_token": f"simulated_dropbox_refresh_{code[:8]}",
            "expires_in": 14400,
            "token_type": "Bearer"
        }

    def list_files(self, path: str, token: str) -> List[Dict[str, Any]]:
        return [
            {"id": "db-file-1", "name": "Billing_Snapshots.tar.gz", "size": 15032385536, "is_folder": False}
        ]

    def get_file_metadata(self, file_id_or_path: str, token: str) -> Dict[str, Any]:
        return {"id": file_id_or_path, "size": 15032385536, "content_hash": "dropbox_hash"}

    def create_resumable_upload_session(self, path: str, file_size: int, token: str) -> str:
        return "https://content.dropboxapi.com/2/files/upload_session/start"

    def upload_chunk(self, session_url: str, chunk_data: bytes, start_byte: int, total_bytes: int, token: str) -> Dict[str, Any]:
        return {"status": "in_progress", "offset": start_byte + len(chunk_data)}

    def verify_integrity(self, destination_path: str, expected_sha256: str, token: str) -> bool:
        return True


class LocalFilesystemAdapter(ProviderAdapter):
    def provider_id(self) -> str:
        return "local"

    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "browser_oauth": False,
            "device_authorization": True,
            "qr_assisted_auth": True,       # QR code encodes local Windows agent enrollment pairing
            "refresh_token": False,
            "token_revocation": True,
            "folder_selection": True,
            "resumable_upload": True
        }

    def get_authorization_url(self, state: str) -> str:
        return "local://enrollment-required"

    def exchange_code_for_tokens(self, code: str, code_verifier: Optional[str] = None) -> Dict[str, Any]:
        return {"access_token": "local-agent-mtls-verified", "expires_in": 99999999}

    def list_files(self, path: str, token: str) -> List[Dict[str, Any]]:
        return []

    def get_file_metadata(self, file_id_or_path: str, token: str) -> Dict[str, Any]:
        return {"id": file_id_or_path, "size": 0, "sha256": ""}

    def create_resumable_upload_session(self, path: str, file_size: int, token: str) -> str:
        return "local://session"

    def upload_chunk(self, session_url: str, chunk_data: bytes, start_byte: int, total_bytes: int, token: str) -> Dict[str, Any]:
        return {"status": "in_progress", "offset": start_byte + len(chunk_data)}

    def verify_integrity(self, destination_path: str, expected_sha256: str, token: str) -> bool:
        return True

def get_provider_adapter(provider_name: str) -> ProviderAdapter:
    p = provider_name.lower()
    if "google" in p or "gdrive" in p:
        return GoogleDriveAdapter()
    if "onedrive" in p or "microsoft" in p:
        return OneDriveAdapter()
    if "dropbox" in p:
        return DropboxAdapter()
    return LocalFilesystemAdapter()
