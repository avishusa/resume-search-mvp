from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ResumeModel(Base):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    resume_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    provider_name: Mapped[str] = mapped_column(String(64), index=True, nullable=True)
    source_id: Mapped[str] = mapped_column(String(1024), index=True, nullable=True)
    file_name: Mapped[str] = mapped_column(String(255))
    source_path: Mapped[str] = mapped_column(String(1024), unique=True, index=True, nullable=True)
    file_type: Mapped[str] = mapped_column(String(255))
    file_hash: Mapped[str] = mapped_column(String(128), index=True)
    last_modified: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    extraction_status: Mapped[str] = mapped_column(String(64))
    parsing_status: Mapped[str] = mapped_column(String(64), nullable=True)
    parser_used: Mapped[str] = mapped_column(String(64), nullable=True)
    parsing_error: Mapped[str] = mapped_column(Text, nullable=True)
    ollama_error: Mapped[str] = mapped_column(Text, nullable=True)
    ollama_model: Mapped[str] = mapped_column(String(255), nullable=True)
    ollama_raw_response_preview: Mapped[str] = mapped_column(Text, nullable=True)
    extracted_text: Mapped[str] = mapped_column(Text)
    extracted_text_preview: Mapped[str] = mapped_column(Text)
    candidate_name: Mapped[str] = mapped_column(String(255), nullable=True)
    email: Mapped[str] = mapped_column(String(255), index=True, nullable=True)
    phone: Mapped[str] = mapped_column(String(100), nullable=True)
    current_title: Mapped[str] = mapped_column(String(255), index=True, nullable=True)
    skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    total_experience_years: Mapped[float] = mapped_column(Float, nullable=True)
    companies: Mapped[list[str]] = mapped_column(JSON, default=list)
    education: Mapped[list[str]] = mapped_column(JSON, default=list)
    resume_summary: Mapped[str] = mapped_column(Text, default="")
    confidence_score: Mapped[float] = mapped_column(Float, nullable=True)
    experience_extraction_method: Mapped[str] = mapped_column(String(64), nullable=True)
    experience_date_ranges: Mapped[list[str]] = mapped_column(JSON, default=list)
    parsed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
