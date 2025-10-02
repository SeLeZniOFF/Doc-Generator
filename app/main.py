from fastapi import FastAPI, Depends, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import select
from pathlib import Path
from typing import List
import io
import zipfile

from .settings import settings
from .database import get_db, engine, Base
from . import models, schemas
from .docx_utils import extract_placeholders, replace_placeholders

app = FastAPI(title="DocGen")

# CORS
origins = [s.strip() for s in settings.ALLOWED_ORIGINS.split(",") if s.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Инициализация БД и директорий
Base.metadata.create_all(bind=engine)
STORAGE_DIR = Path(settings.STORAGE_DIR)
TEMPLATES_DIR = STORAGE_DIR / "templates"
OUTPUTS_DIR = STORAGE_DIR / "outputs"
for d in (TEMPLATES_DIR, OUTPUTS_DIR):
    d.mkdir(parents=True, exist_ok=True)

# ---- Домашняя страница (минимальный UI) ----
from fastapi.staticfiles import StaticFiles
app.mount("/", StaticFiles(directory=str(Path(__file__).resolve().parent.parent / "static"), html=True), name="static")

# -------------- Entities --------------
@app.post("/api/entities", response_model=schemas.EntityOut)
def create_entity(payload: schemas.EntityCreate, db: Session = Depends(get_db)):
    code = payload.code.strip()
    if not (code.startswith("{") and code.endswith("}")):
        raise HTTPException(status_code=400, detail="Код сущности должен быть в фигурных скобках, например {FIO}")
    exists = db.scalar(select(models.Entity).where(models.Entity.code == code))
    if exists:
        raise HTTPException(status_code=409, detail="Сущность с таким кодом уже существует")
    ent = models.Entity(name=payload.name.strip(), code=code)
    db.add(ent)
    db.commit()
    db.refresh(ent)
    return ent

@app.get("/api/entities", response_model=List[schemas.EntityOut])
def list_entities(db: Session = Depends(get_db)):
    return db.scalars(select(models.Entity).order_by(models.Entity.id)).all()

@app.put("/api/entities/{entity_id}", response_model=schemas.EntityOut)
def update_entity(entity_id: int, payload: schemas.EntityUpdate, db: Session = Depends(get_db)):
    ent = db.get(models.Entity, entity_id)
    if not ent:
        raise HTTPException(404, "Сущность не найдена")
    if payload.name is not None:
        ent.name = payload.name
    if payload.code is not None:
        code = payload.code.strip()
        if not (code.startswith("{") and code.endswith("}")):
            raise HTTPException(status_code=400, detail="Код сущности должен быть в фигурных скобках")
        dup = db.scalar(select(models.Entity).where(models.Entity.code == code, models.Entity.id != ent.id))
        if dup:
            raise HTTPException(409, "Код уже используется")
        ent.code = code
    db.commit()
    db.refresh(ent)
    return ent

@app.delete("/api/entities/{entity_id}")
def delete_entity(entity_id: int, db: Session = Depends(get_db)):
    ent = db.get(models.Entity, entity_id)
    if not ent:
        raise HTTPException(404, "Сущность не найдена")
    db.delete(ent)
    db.commit()
    return {"ok": True}

# -------------- Clients --------------
@app.post("/api/clients", response_model=schemas.ClientOut)
def create_client(payload: schemas.ClientCreate, db: Session = Depends(get_db)):
    exists = db.scalar(select(models.Client).where(models.Client.name == payload.name))
    if exists:
        raise HTTPException(409, detail="Клиент с таким именем уже существует")
    c = models.Client(name=payload.name)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c

@app.get("/api/clients", response_model=List[schemas.ClientOut])
def list_clients(db: Session = Depends(get_db)):
    return db.scalars(select(models.Client).order_by(models.Client.id)).all()

@app.put("/api/clients/{client_id}", response_model=schemas.ClientOut)
def update_client(client_id: int, payload: schemas.ClientUpdate, db: Session = Depends(get_db)):
    c = db.get(models.Client, client_id)
    if not c:
        raise HTTPException(404, "Клиент не найден")
    if payload.name is not None:
        dup = db.scalar(select(models.Client).where(models.Client.name == payload.name, models.Client.id != c.id))
        if dup:
            raise HTTPException(409, "Имя уже используется")
        c.name = payload.name
    db.commit()
    db.refresh(c)
    return c

@app.delete("/api/clients/{client_id}")
def delete_client(client_id: int, db: Session = Depends(get_db)):
    c = db.get(models.Client, client_id)
    if not c:
        raise HTTPException(404, "Клиент не найден")
    db.delete(c)
    db.commit()
    return {"ok": True}

# -------------- Values --------------
@app.post("/api/values", response_model=schemas.ValueOut)
def create_value(payload: schemas.ValueCreate, db: Session = Depends(get_db)):
    # Проверки наличия
    ent = db.get(models.Entity, payload.entity_id)
    cli = db.get(models.Client, payload.client_id)
    if not ent or not cli:
        raise HTTPException(400, "Некорректные entity_id или client_id")
    # Уникальность (entity, client)
    dup = db.scalar(select(models.Value).where(models.Value.entity_id==payload.entity_id, models.Value.client_id==payload.client_id))
    if dup:
        raise HTTPException(409, "Значение для этой пары entity/client уже существует. Обновите его, если нужно.")
    v = models.Value(entity_id=payload.entity_id, client_id=payload.client_id, value_text=payload.value_text)
    db.add(v)
    db.commit()
    db.refresh(v)
    return v

@app.get("/api/values", response_model=List[schemas.ValueOut])
def list_values(db: Session = Depends(get_db)):
    return db.scalars(select(models.Value).order_by(models.Value.id)).all()

@app.put("/api/values/{value_id}", response_model=schemas.ValueOut)
def update_value(value_id: int, payload: schemas.ValueUpdate, db: Session = Depends(get_db)):
    v = db.get(models.Value, value_id)
    if not v:
        raise HTTPException(404, "Значение не найдено")
    if payload.value_text is not None:
        v.value_text = payload.value_text
    db.commit()
    db.refresh(v)
    return v

@app.delete("/api/values/{value_id}")
def delete_value(value_id: int, db: Session = Depends(get_db)):
    v = db.get(models.Value, value_id)
    if not v:
        raise HTTPException(404, "Значение не найдено")
    db.delete(v)
    db.commit()
    return {"ok": True}

# -------------- Templates --------------
@app.post("/api/templates", response_model=schemas.TemplateOut)
async def upload_template(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.lower().endswith(".docx"):
        raise HTTPException(400, "Ожидается .docx файл")
    safe_name = Path(file.filename).name
    dest = TEMPLATES_DIR / safe_name

    # Разрешаем одноименные файлы: добавим суффикс, если уже есть
    i = 1
    while dest.exists():
        dest = TEMPLATES_DIR / f"{Path(safe_name).stem}_{i}.docx"
        i += 1

    content = await file.read()
    dest.write_bytes(content)

    tmpl = models.Template(filename=dest.name, file_path=str(dest))
    db.add(tmpl)
    db.commit()
    db.refresh(tmpl)
    return tmpl

@app.get("/api/templates", response_model=List[schemas.TemplateOut])
def list_templates(db: Session = Depends(get_db)):
    return db.scalars(select(models.Template).order_by(models.Template.id)).all()

@app.get("/api/templates/{template_id}/placeholders")
def get_template_placeholders(template_id: int, db: Session = Depends(get_db)):
    tmpl = db.get(models.Template, template_id)
    if not tmpl:
        raise HTTPException(404, "Шаблон не найден")
    placeholders = sorted(list(extract_placeholders(tmpl.file_path)))
    return {"placeholders": placeholders}

# -------------- Generation --------------
@app.post("/api/generate")
def generate_documents(payload: schemas.GenerateIn, db: Session = Depends(get_db)):
    tmpl = db.get(models.Template, payload.template_id)
    if not tmpl:
        raise HTTPException(404, "Шаблон не найден")

    # Соберем карту кодов сущностей -> id
    entities = db.scalars(select(models.Entity)).all()
    code_to_entity = {e.code: e.id for e in entities}

    def mapping_for_client(client_id: int):
        # Значения клиента
        vals = db.scalars(select(models.Value).where(models.Value.client_id==client_id)).all()
        ent_id_to_val = {v.entity_id: v.value_text for v in vals}
        # Построим mapping {"{FIO}": "..."}
        mapping = {}
        for code, ent_id in code_to_entity.items():
            if ent_id in ent_id_to_val:
                mapping[code] = ent_id_to_val[ent_id]
        return mapping

    outputs: list[tuple[int, Path]] = []  # (client_id, path)

    if len(payload.client_ids) == 1:
        cid = payload.client_ids[0]
        mapping = mapping_for_client(cid)
        try:
            doc = replace_placeholders(tmpl.file_path, mapping, on_missing=payload.on_missing)
        except KeyError as e:
            raise HTTPException(400, str(e))
        out_name = f"generated_{Path(tmpl.filename).stem}_client{cid}.docx"
        out_path = OUTPUTS_DIR / out_name
        doc.save(out_path)
        # history
        hist = models.GenerationHistory(template_id=tmpl.id, client_id=cid, user_id=None, output_path=str(out_path))
        db.add(hist)
        db.commit()
        return FileResponse(path=str(out_path), filename=out_name, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

    # ZIP для нескольких клиентов
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for cid in payload.client_ids:
            mapping = mapping_for_client(cid)
            try:
                doc = replace_placeholders(tmpl.file_path, mapping, on_missing=payload.on_missing)
            except KeyError as e:
                raise HTTPException(400, f"client_id {cid}: {e}")
            out_name = f"generated_{Path(tmpl.filename).stem}_client{cid}.docx"
            temp_bytes = io.BytesIO()
            doc.save(temp_bytes)
            zf.writestr(out_name, temp_bytes.getvalue())
            outputs.append((cid, Path(out_name)))

    # сохраним общий zip на диск (по желанию)
    zip_name = f"batch_{Path(tmpl.filename).stem}_{'_'.join(map(str, payload.client_ids))}.zip"
    zip_path = OUTPUTS_DIR / zip_name
    with open(zip_path, "wb") as f:
        f.write(zip_buf.getvalue())

    # history
    for cid, _ in outputs:
        hist = models.GenerationHistory(template_id=tmpl.id, client_id=cid, user_id=None, output_path=str(zip_path))
        db.add(hist)
    db.commit()

    zip_buf.seek(0)
    return StreamingResponse(zip_buf, media_type="application/zip", headers={"Content-Disposition": f"attachment; filename={zip_name}"})

@app.get("/api/history", response_model=List[schemas.GenerationOut])
def get_history(db: Session = Depends(get_db)):
    rows = db.scalars(select(models.GenerationHistory).order_by(models.GenerationHistory.id.desc())).all()
    return rows
