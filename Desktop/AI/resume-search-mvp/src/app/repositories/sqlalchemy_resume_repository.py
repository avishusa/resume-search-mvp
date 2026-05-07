from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.database import SessionLocal, init_db
from app.models.resume import ResumeModel
from app.repositories.resume_repository import ResumeRecord
from app.schemas.candidate import CandidateProfile


class SQLAlchemyResumeRepository:
    def __init__(self, session_factory: sessionmaker[Session] = SessionLocal) -> None:
        init_db()
        self._session_factory = session_factory

    def save(self, record: ResumeRecord) -> ResumeRecord:
        with self._session_factory() as session:
            existing_model = self._get_model_for_record(session, record)
            now = datetime.now(UTC)
            if existing_model is None:
                model = self._to_model(record, created_at=now, updated_at=now)
                session.add(model)
            else:
                self._update_model(existing_model, record, updated_at=now)
            session.commit()
        return record

    def create(self, record: ResumeRecord) -> ResumeRecord:
        return self.save(record)

    def update(self, record: ResumeRecord) -> ResumeRecord:
        return self.save(record)

    def upsert_by_source_path(self, record: ResumeRecord) -> ResumeRecord:
        return self.save(record)

    def get(self, resume_id: str) -> ResumeRecord | None:
        with self._session_factory() as session:
            model = session.scalar(
                select(ResumeModel).where(ResumeModel.resume_id == resume_id)
            )
            return self._to_record(model) if model else None

    def get_by_source_path(self, source_path: str) -> ResumeRecord | None:
        with self._session_factory() as session:
            model = session.scalar(
                select(ResumeModel).where(ResumeModel.source_path == source_path)
            )
            return self._to_record(model) if model else None

    def get_by_source_path_and_file_hash(
        self,
        source_path: str,
        file_hash: str,
    ) -> ResumeRecord | None:
        with self._session_factory() as session:
            model = session.scalar(
                select(ResumeModel).where(
                    ResumeModel.source_path == source_path,
                    ResumeModel.file_hash == file_hash,
                )
            )
            return self._to_record(model) if model else None

    def list_all(self) -> list[ResumeRecord]:
        with self._session_factory() as session:
            models = session.scalars(
                select(ResumeModel).order_by(ResumeModel.file_name)
            ).all()
            return [self._to_record(model) for model in models]

    def list_searchable(self) -> list[ResumeRecord]:
        with self._session_factory() as session:
            models = session.scalars(
                select(ResumeModel)
                .where(
                    ResumeModel.extraction_status == "extracted",
                    ResumeModel.parsing_status.in_(["parsed", "review_required"]),
                )
                .order_by(ResumeModel.file_name)
            ).all()
            return [
                record
                for record in [self._to_record(model) for model in models]
                if record.candidate_profile is not None
            ]

    def clear(self) -> None:
        with self._session_factory() as session:
            session.query(ResumeModel).delete()
            session.commit()

    def _get_model_for_record(
        self,
        session: Session,
        record: ResumeRecord,
    ) -> ResumeModel | None:
        model = session.scalar(
            select(ResumeModel).where(ResumeModel.resume_id == record.resume_id)
        )
        if model is not None:
            return model
        if record.source_path is None:
            return None
        return session.scalar(
            select(ResumeModel).where(ResumeModel.source_path == record.source_path)
        )

    def _to_model(
        self,
        record: ResumeRecord,
        created_at: datetime,
        updated_at: datetime,
    ) -> ResumeModel:
        model = ResumeModel(
            resume_id=record.resume_id,
            created_at=created_at,
            updated_at=updated_at,
        )
        self._update_model(model, record, updated_at=updated_at)
        return model

    def _update_model(
        self,
        model: ResumeModel,
        record: ResumeRecord,
        updated_at: datetime,
    ) -> None:
        profile = record.candidate_profile
        model.resume_id = record.resume_id
        model.file_name = record.file_name
        model.source_path = record.source_path
        model.file_type = record.file_type
        model.file_hash = record.file_hash
        model.last_modified = record.last_modified
        model.extraction_status = record.extraction_status
        model.parsing_status = record.parsing_status
        model.parser_used = record.parser_used
        model.parsing_error = record.parsing_error
        model.ollama_error = record.ollama_error
        model.ollama_model = record.ollama_model
        model.ollama_raw_response_preview = record.ollama_raw_response_preview
        model.extracted_text = record.extracted_text
        model.extracted_text_preview = record.extracted_text_preview
        model.candidate_name = profile.candidate_name if profile else None
        model.email = profile.email if profile else None
        model.phone = profile.phone if profile else None
        model.current_title = profile.current_title if profile else None
        model.skills = profile.skills if profile else []
        model.total_experience_years = profile.total_experience_years if profile else None
        model.companies = profile.companies if profile else []
        model.education = profile.education if profile else []
        model.resume_summary = profile.resume_summary if profile else ""
        model.confidence_score = profile.confidence_score if profile else None
        model.experience_extraction_method = (
            profile.experience_extraction_method if profile else None
        )
        model.experience_date_ranges = profile.experience_date_ranges if profile else []
        model.parsed_at = record.parsed_at
        model.ingested_at = record.ingested_at
        model.updated_at = updated_at

    def _to_record(self, model: ResumeModel) -> ResumeRecord:
        profile = self._to_candidate_profile(model)
        return ResumeRecord(
            resume_id=model.resume_id,
            file_name=model.file_name,
            source_path=model.source_path,
            file_type=model.file_type,
            file_hash=model.file_hash,
            last_modified=model.last_modified,
            extraction_status=model.extraction_status,
            parsing_status=model.parsing_status,
            parser_used=model.parser_used,
            parsing_error=model.parsing_error,
            ollama_error=model.ollama_error,
            ollama_raw_response_preview=model.ollama_raw_response_preview,
            ollama_model=model.ollama_model,
            extracted_text=model.extracted_text,
            parsed_at=model.parsed_at,
            ingested_at=model.ingested_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
            candidate_profile=profile,
        )

    def _to_candidate_profile(self, model: ResumeModel) -> CandidateProfile | None:
        if model.parsing_status not in {"parsed", "review_required"}:
            return None
        if model.parser_used not in {"ollama", "rule_based"}:
            return None

        return CandidateProfile(
            candidate_name=model.candidate_name,
            email=model.email,
            phone=model.phone,
            current_title=model.current_title,
            skills=model.skills or [],
            total_experience_years=model.total_experience_years,
            companies=model.companies or [],
            education=model.education or [],
            resume_summary=model.resume_summary or "",
            experience_extraction_method=model.experience_extraction_method or "unknown",
            experience_date_ranges=model.experience_date_ranges or [],
            confidence_score=model.confidence_score or 0,
            parsing_status=model.parsing_status,
            parser_used=model.parser_used,
        )
