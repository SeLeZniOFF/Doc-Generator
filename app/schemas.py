from pydantic import BaseModel, Field
from typing import Optional, List

# -------- Entities --------
class EntityCreate(BaseModel):
    name: str = Field(..., examples=["ФИО"])
    code: str = Field(..., examples=["{FIO}"])  # храним вместе с фигурными скобками

class EntityUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None

class EntityOut(BaseModel):
    id: int
    name: str
    code: str
    class Config:
        from_attributes = True

# -------- Clients --------
class ClientCreate(BaseModel):
    name: str

class ClientUpdate(BaseModel):
    name: Optional[str] = None

class ClientOut(BaseModel):
    id: int
    name: str
    class Config:
        from_attributes = True

# -------- Values --------
class ValueCreate(BaseModel):
    entity_id: int
    client_id: int
    value_text: str

class ValueUpdate(BaseModel):
    value_text: Optional[str] = None

class ValueOut(BaseModel):
    id: int
    entity_id: int
    client_id: int
    value_text: str
    class Config:
        from_attributes = True

# -------- Templates --------
class TemplateOut(BaseModel):
    id: int
    filename: str
    file_path: str
    class Config:
        from_attributes = True

# -------- Generation --------
class GenerateIn(BaseModel):
    template_id: int
    client_ids: List[int]
    on_missing: str = Field("keep", pattern="^(keep|error)$", description="При отсутствии значения: keep — оставить placeholder, error — вернуть ошибку")

class GenerationOut(BaseModel):
    id: int
    template_id: int
    client_id: int
    output_path: str
    class Config:
        from_attributes = True
