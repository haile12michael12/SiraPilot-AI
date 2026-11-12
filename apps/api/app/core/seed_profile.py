"""Seed initial profile and form-fill answers for Hailemichael Assefa."""

from __future__ import annotations

import json
import sqlite3
from typing import TYPE_CHECKING

from app.core.timeutil import utc_now
from app.modules.form_fill.answers import create_answer
from app.modules.form_fill.repository import FormFillRepository
from app.modules.form_fill.schemas import (
    AnswerChoiceInput,
    AnswerCreate,
    AnswerSingleChoiceValue,
    BooleanValue,
    DecimalValue,
    TextValue,
)
from app.modules.preferences.schemas import (
    DEFAULT_PREFERENCES_REVISION,
    DescriptionHighlight,
    Preferences,
)

if TYPE_CHECKING:
    from app.config import Settings
    from app.core.paths import ResolvedPaths


def _ensure_schema(conn: sqlite3.Connection) -> None:
    try:
        from app.infra.database import init_schema

        init_schema(conn)
    except ModuleNotFoundError:
        from pathlib import Path

        schema_path = Path(__file__).resolve().parent / "schema.sql"
        if schema_path.exists():
            conn.executescript(schema_path.read_text("utf-8"))
        conn.execute(
            "CREATE TABLE IF NOT EXISTS user_preferences ("
            "revision TEXT PRIMARY KEY, "
            "settings_json TEXT NOT NULL, "
            "updated_at TEXT NOT NULL)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS form_answers ("
            "id TEXT PRIMARY KEY, "
            "answer_key TEXT UNIQUE NOT NULL, "
            "label TEXT NOT NULL, "
            "description TEXT, "
            "value_kind TEXT NOT NULL, "
            "value_json TEXT NOT NULL, "
            "fill_policy TEXT NOT NULL DEFAULT 'auto', "
            "status TEXT NOT NULL DEFAULT 'active', "
            "revision INTEGER NOT NULL DEFAULT 1, "
            "created_at TEXT NOT NULL, "
            "updated_at TEXT NOT NULL)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS form_answer_choices ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "answer_id TEXT NOT NULL REFERENCES form_answers (id) ON DELETE CASCADE, "
            "choice_key TEXT NOT NULL, "
            "label TEXT NOT NULL, "
            "status TEXT NOT NULL DEFAULT 'active', "
            "rank INTEGER NOT NULL, "
            "UNIQUE (answer_id, choice_key))"
        )

HAILEMICHAEL_PROFILE = {
    "first_name": "Hailemichael",
    "last_name": "Assefa",
    "email": "hailemichaelassefa18@gmail.com",
    "phone": "+251911000000",
    "headline": "Full-Stack Software Developer | Python & FastAPI | Laravel | React & TypeScript",
    "city": "Addis Ababa",
    "country": "Ethiopia",
    "github_url": "https://github.com/haile12michael12",
    "portfolio_url": "https://hailemichael-portfolio.vercel.app/",
    "linkedin_url": "https://www.linkedin.com/in/hailemichael-assefa-413614223/",
    "years_experience": "4",
    "summary": (
        "Full-stack software developer focused on building scalable web platforms, "
        "secure APIs, and AI-powered products. Proficient in Python, FastAPI, Laravel, "
        "React, TypeScript, Next.js, PostgreSQL, MySQL, and modern web architectures."
    ),
    "skills": (
        "Python, FastAPI, Laravel, PHP, React, TypeScript, Next.js, "
        "PostgreSQL, MySQL, SQLite, Docker, Git, REST APIs, Tailwind CSS"
    ),
}


def seed_hailemichael_profile(conn: sqlite3.Connection) -> dict[str, int]:
    """Seed default profile answers and preferences for Hailemichael Assefa."""
    _ensure_schema(conn)

    # 1. Seed or update user preferences with tailored keywords
    cursor = conn.cursor()
    prefs_row = cursor.execute("SELECT revision, settings_json FROM user_preferences LIMIT 1").fetchone()
    if not prefs_row:
        custom_highlights = [
            DescriptionHighlight(id="experience-years", terms=["years", "year", "exp", "jaar"]),
            DescriptionHighlight(id="language", terms=["english", "amharic", "dutch", "nederlandse"]),
            DescriptionHighlight(id="pay", terms=["usd", "$", "euro", "€", "birr", "etb"]),
            DescriptionHighlight(
                id="custom-words",
                terms=[
                    "senior",
                    "lead",
                    "fullstack",
                    "full-stack",
                    "backend",
                    "frontend",
                    "python",
                    "fastapi",
                    "laravel",
                    "react",
                    "typescript",
                    "ai",
                    "remote",
                ],
            ),
        ]
        default_prefs = Preferences(description_highlights=custom_highlights)
        cursor.execute(
            "INSERT INTO user_preferences (revision, settings_json, updated_at) VALUES (?, ?, ?)",
            (DEFAULT_PREFERENCES_REVISION, default_prefs.model_dump_json(), utc_now()),
        )
        conn.commit()

    # 2. Seed form-fill answers
    repo = FormFillRepository(conn)
    created_count = 0

    answers_to_seed: list[AnswerCreate] = [
        AnswerCreate(
            answer_key="first_name",
            label="First name",
            description="Legal first name",
            value_kind="text",
            value=TextValue(kind="text", value=HAILEMICHAEL_PROFILE["first_name"]),
            fill_policy="auto",
        ),
        AnswerCreate(
            answer_key="last_name",
            label="Last name",
            description="Legal last name",
            value_kind="text",
            value=TextValue(kind="text", value=HAILEMICHAEL_PROFILE["last_name"]),
            fill_policy="auto",
        ),
        AnswerCreate(
            answer_key="email",
            label="Email address",
            description="Primary contact email",
            value_kind="text",
            value=TextValue(kind="text", value=HAILEMICHAEL_PROFILE["email"]),
            fill_policy="auto",
        ),
        AnswerCreate(
            answer_key="phone",
            label="Phone number",
            description="Primary mobile phone",
            value_kind="text",
            value=TextValue(kind="text", value=HAILEMICHAEL_PROFILE["phone"]),
            fill_policy="auto",
        ),
        AnswerCreate(
            answer_key="headline",
            label="Professional headline",
            description="Headline for job applications",
            value_kind="text",
            value=TextValue(kind="text", value=HAILEMICHAEL_PROFILE["headline"]),
            fill_policy="auto",
        ),
        AnswerCreate(
            answer_key="city",
            label="City",
            description="Current residence city",
            value_kind="text",
            value=TextValue(kind="text", value=HAILEMICHAEL_PROFILE["city"]),
            fill_policy="auto",
        ),
        AnswerCreate(
            answer_key="country",
            label="Country",
            description="Current residence country",
            value_kind="text",
            value=TextValue(kind="text", value=HAILEMICHAEL_PROFILE["country"]),
            fill_policy="auto",
        ),
        AnswerCreate(
            answer_key="github_url",
            label="GitHub profile",
            description="GitHub portfolio and repository showcase",
            value_kind="text",
            value=TextValue(kind="text", value=HAILEMICHAEL_PROFILE["github_url"]),
            fill_policy="auto",
        ),
        AnswerCreate(
            answer_key="linkedin_url",
            label="LinkedIn profile",
            description="LinkedIn professional profile URL",
            value_kind="text",
            value=TextValue(kind="text", value=HAILEMICHAEL_PROFILE["linkedin_url"]),
            fill_policy="auto",
        ),
        AnswerCreate(
            answer_key="portfolio_url",
            label="Portfolio website",
            description="Personal portfolio website URL",
            value_kind="text",
            value=TextValue(kind="text", value=HAILEMICHAEL_PROFILE["portfolio_url"]),
            fill_policy="auto",
        ),
        AnswerCreate(
            answer_key="years_experience",
            label="Total years of experience",
            description="Total years of professional software development experience",
            value_kind="decimal",
            value=DecimalValue(kind="decimal", value=HAILEMICHAEL_PROFILE["years_experience"]),
            fill_policy="auto",
        ),
        AnswerCreate(
            answer_key="summary",
            label="Professional summary",
            description="Brief career and technical overview",
            value_kind="text",
            value=TextValue(kind="text", value=HAILEMICHAEL_PROFILE["summary"]),
            fill_policy="auto",
        ),
        AnswerCreate(
            answer_key="skills",
            label="Core skills",
            description="Key programming languages, frameworks, and tools",
            value_kind="text",
            value=TextValue(kind="text", value=HAILEMICHAEL_PROFILE["skills"]),
            fill_policy="auto",
        ),
        AnswerCreate(
            answer_key="work_authorized",
            label="Authorized to work",
            description="Legally authorized to work remotely / locally",
            value_kind="single_choice",
            value=AnswerSingleChoiceValue(kind="single_choice", choice_key="yes"),
            choices=[
                AnswerChoiceInput(choice_key="yes", display_label="Yes", status="active"),
                AnswerChoiceInput(choice_key="no", display_label="No", status="active"),
            ],
            fill_policy="auto",
        ),
        AnswerCreate(
            answer_key="require_sponsorship",
            label="Require visa sponsorship",
            description="Will you now or in the future require visa sponsorship",
            value_kind="single_choice",
            value=AnswerSingleChoiceValue(kind="single_choice", choice_key="no"),
            choices=[
                AnswerChoiceInput(choice_key="yes", display_label="Yes", status="active"),
                AnswerChoiceInput(choice_key="no", display_label="No", status="active"),
            ],
            fill_policy="auto",
        ),
    ]

    for answer_create in answers_to_seed:
        if repo.get_answer_by_key(answer_create.answer_key) is None:
            create_answer(repo, answer_create)
            created_count += 1

    return {"answers_created": created_count, "total_answers": len(answers_to_seed)}
