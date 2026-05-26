import json
from pathlib import Path

import httpx

from app.config import Settings
from app.schemas.debug import (
    GoogleDriveStorageProviderDebugStatus,
    LocalStorageProviderDebugStatus,
    OllamaDebugResponse,
    ParseResumeTextDebugResponse,
    StorageProviderDebugResponse,
)
from app.services.candidate_profile_service import CandidateProfileService
from app.storage.factory import create_google_drive_resume_storage_provider
from app.storage.local_folder import LocalFolderResumeStorageProvider


class DebugService:
    def __init__(
        self,
        settings: Settings,
        candidate_profile_service: CandidateProfileService,
    ) -> None:
        self._settings = settings
        self._candidate_profile_service = candidate_profile_service

    def check_ollama(self) -> OllamaDebugResponse:
        ollama_reachable = False
        test_generation_success = False
        error = None

        try:
            with httpx.Client(timeout=self._settings.ollama_timeout_seconds) as client:
                response = client.post(
                    f"{self._settings.ollama_base_url.rstrip('/')}/api/generate",
                    json={
                        "model": self._settings.ollama_model,
                        "prompt": 'Return only JSON: {"status":"ok"}',
                        "stream": False,
                        "format": "json",
                    },
                )
                response.raise_for_status()

            ollama_reachable = True
            response_body = response.json()
            raw_generation = response_body.get("response")
            if not isinstance(raw_generation, str):
                raise ValueError("Ollama response did not include a response string.")

            parsed_generation = json.loads(raw_generation)
            test_generation_success = parsed_generation.get("status") == "ok"
            if not test_generation_success:
                error = "Ollama JSON response did not contain status=ok."
        except Exception as exception:
            error = str(exception)

        return OllamaDebugResponse(
            resume_parser_provider=self._settings.resume_parser_provider,
            ollama_base_url=self._settings.ollama_base_url,
            ollama_model=self._settings.ollama_model,
            ollama_timeout_seconds=self._settings.ollama_timeout_seconds,
            ollama_max_resume_chars=self._settings.ollama_max_resume_chars,
            ollama_use_resume_digest=self._settings.ollama_use_resume_digest,
            resume_parse_concurrency=self._settings.resume_parse_concurrency,
            ollama_reachable=ollama_reachable,
            test_generation_success=test_generation_success,
            error=error,
        )

    def parse_resume_text(self, resume_text: str) -> ParseResumeTextDebugResponse:
        parse_result = self._candidate_profile_service.parse_with_metadata(resume_text)
        profile = parse_result.profile
        return ParseResumeTextDebugResponse(
            parser_used=profile.parser_used,
            profile=profile.model_dump(),
            parsing_error=parse_result.parsing_error,
            ollama_error=parse_result.ollama_error,
            ollama_raw_response_preview=parse_result.ollama_raw_response_preview,
            ollama_model=parse_result.ollama_model,
        )

    def check_storage_providers(self) -> StorageProviderDebugResponse:
        provider_statuses = []
        for provider_name in self._settings.resume_storage_provider_list:
            if provider_name == "local":
                provider_statuses.append(self._check_local_storage_provider())
            elif provider_name == "google_drive":
                provider_statuses.append(self._check_google_drive_storage_provider())
            else:
                provider_statuses.append(
                    LocalStorageProviderDebugStatus(
                        provider_name=provider_name,
                        directory_path="",
                        exists=False,
                        recursive=False,
                        supported_file_count=0,
                        error=f"Unsupported resume storage provider: {provider_name}",
                    )
                )

        return StorageProviderDebugResponse(
            configured_providers=self._settings.resume_storage_provider_list,
            providers=provider_statuses,
        )

    def _check_local_storage_provider(self) -> LocalStorageProviderDebugStatus:
        try:
            provider = LocalFolderResumeStorageProvider(
                self._settings.local_drive_resume_dir,
                recursive=self._settings.local_drive_recursive,
            )
            directory_path = str(Path(self._settings.local_drive_resume_dir))
            directory_exists = Path(self._settings.local_drive_resume_dir).exists()
            supported_file_count = len(provider.list_resume_files())
            return LocalStorageProviderDebugStatus(
                provider_name="local",
                directory_path=directory_path,
                exists=directory_exists,
                recursive=self._settings.local_drive_recursive,
                supported_file_count=supported_file_count,
            )
        except Exception as exception:
            return LocalStorageProviderDebugStatus(
                provider_name="local",
                directory_path=self._settings.local_drive_resume_dir,
                exists=False,
                recursive=self._settings.local_drive_recursive,
                supported_file_count=0,
                error=str(exception),
            )

    def _check_google_drive_storage_provider(
        self,
    ) -> GoogleDriveStorageProviderDebugStatus:
        service_account_file = self._settings.google_service_account_file.strip()
        folder_id = self._settings.google_drive_folder_id.strip()
        service_account_file_exists = (
            bool(service_account_file) and Path(service_account_file).exists()
        )

        status = GoogleDriveStorageProviderDebugStatus(
            provider_name="google_drive",
            folder_id_present=bool(folder_id),
            service_account_file_configured=bool(service_account_file),
            service_account_file_exists=service_account_file_exists,
            recursive_enabled=self._settings.google_drive_recursive,
            max_depth=self._settings.google_drive_max_depth,
            max_files=self._settings.google_drive_max_files,
            can_authenticate=False,
            can_list_files=False,
            supported_file_count=None,
            folders_seen=None,
            errors=[],
        )

        if not folder_id or not service_account_file:
            status.error = (
                "GOOGLE_DRIVE_FOLDER_ID and GOOGLE_SERVICE_ACCOUNT_FILE are "
                "required for Google Drive storage."
            )
            return status

        try:
            provider = create_google_drive_resume_storage_provider(self._settings)
            files = provider.list_resume_files()
            status.can_authenticate = True
            status.can_list_files = True
            status.supported_file_count = len(files)
            status.folders_seen = provider.last_folders_seen
            status.errors = provider.last_errors
            if provider.last_errors:
                status.error = "; ".join(provider.last_errors)
        except Exception as exception:
            status.error = str(exception)

        return status
