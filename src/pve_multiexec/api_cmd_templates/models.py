from sqlmodel import Field, SQLModel


class CmdTemplateBase(SQLModel):
    name: str = Field(min_length=1, index=True)
    template: str = Field(index=True)


class CmdTemplate(CmdTemplateBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
