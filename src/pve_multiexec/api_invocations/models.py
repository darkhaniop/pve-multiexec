from datetime import datetime

from sqlmodel import TIMESTAMP, Column, Field, SQLModel, text


class InvocationBase(SQLModel):
    comment: str = Field(default=None, index=True)
    exec_config_id: int
    cmd_template_id: int = Field(index=True)
    exec_config_raw: str
    cmd_template_raw: str
    matched_guests: str
    finished_at: datetime | None


class Invocation(InvocationBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
            index=True,
        ),
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
            server_onupdate=text("CURRENT_TIMESTAMP"),
        ),
    )


def db_init():
    """Call this before creating the SQLite database

    This ensures that SQLModel metadata is populated.
    """
    pass
