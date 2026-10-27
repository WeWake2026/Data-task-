from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class ProviderAdapter(ABC):
    """
    Standard Cloud & Local Storage Provider Interface.
    Each provider declares supported operations explicitly.
    """

    @abstractmethod
    def provider_id(self) -> str:
        """Unique provider identifier (e.g. google-drive, onedrive, dropbox, local)"""
        pass

    @abstractmethod
    def get_capabilities(self) -> Dict[str, Any]:
        """Returns provider capability flags (browser_oauth, device_auth, qr_auth, resumable_upload)"""
        pass

    @abstractmethod
    def get_authorization_url(self, state: str) -> str:
        """Returns OAuth 2.0 authorization URL or instructions"""
        pass

    @abstractmethod
    def exchange_code_for_tokens(self, code: str, code_verifier: Optional[str] = None) -> Dict[str, Any]:
        """Exchanges authorization code for access and refresh tokens"""
        pass

    @abstractmethod
    def list_files(self, path: str, token: str) -> List[Dict[str, Any]]:
        """Lists files and folders with metadata"""
        pass

    @abstractmethod
    def get_file_metadata(self, file_id_or_path: str, token: str) -> Dict[str, Any]:
        """Retrieves file size, hash (SHA-256 or MD5), and modified timestamps"""
        pass

    @abstractmethod
    def create_resumable_upload_session(self, path: str, file_size: int, token: str) -> str:
        """Initiates a resumable upload session for large files"""
        pass

    @abstractmethod
    def upload_chunk(self, session_url: str, chunk_data: bytes, start_byte: int, total_bytes: int, token: str) -> Dict[str, Any]:
        """Streams a bounded chunk of file data"""
        pass

    @abstractmethod
    def verify_integrity(self, destination_path: str, expected_sha256: str, token: str) -> bool:
        """Cryptographically verifies checksum at destination"""
        pass
