from pydantic import BaseModel, Field


class BienvenidaPayload(BaseModel):
    maestro_ids: list[int] = Field(min_length=1)


class FallidoItem(BaseModel):
    id: int
    nombre: str
    error: str


class BienvenidaResultado(BaseModel):
    enviados: int
    fallidos: list[FallidoItem]
