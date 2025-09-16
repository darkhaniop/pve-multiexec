from sqlmodel import Field, SQLModel


class ExecConfigBase(SQLModel):
    name: str = Field(min_length=1, index=True)
    include_tags: str
    exclude_tags: str
    include_vmids: str
    cmd_template_id: int | None = Field(
        default=None, foreign_key="cmdtemplate.id", index=True
    )


class ExecConfig(ExecConfigBase, table=True):
    id: int | None = Field(default=None, primary_key=True)


def db_init():
    """Call this before creating the SQLite database

    This ensures that SQLModel metadata is populated.
    """
    pass
