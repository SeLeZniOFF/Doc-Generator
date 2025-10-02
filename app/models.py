from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, func, UniqueConstraint
from sqlalchemy.orm import relationship, Mapped, mapped_column
from .database import Base


class User(Base):
__tablename__ = "users"
id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())


generations = relationship("GenerationHistory", back_populates="user")


class Client(Base):
__tablename__ = "clients"
id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())


values = relationship("Value", back_populates="client", cascade="all, delete-orphan")
generations = relationship("GenerationHistory", back_populates="client")


class Entity(Base):
__tablename__ = "entities"
id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
# Идентификатор с фигурными скобками: {FIO}, {ADDRESS}
code: Mapped[str] = mapped_column(String(255), unique=True, index=True)
name: Mapped[str] = mapped_column(String(255))
created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())


values = relationship("Value", back_populates="entity", cascade="all, delete-orphan")


class Value(Base):
__tablename__ = "values"
id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"))
value_text: Mapped[str] = mapped_column(Text)


entity = relationship("Entity", back_populates="values")
client = relationship("Client", back_populates="values")


__table_args__ = (
UniqueConstraint("entity_id", "client_id", name="uq_entity_client"),
)


class Template(Base):
__tablename__ = "templates"
id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
filename: Mapped[str] = mapped_column(String(255))
file_path: Mapped[str] = mapped_column(String(1024))
uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())


generations = relationship("GenerationHistory", back_populates="template")


class GenerationHistory(Base):
__tablename__ = "generation_history"
id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
template_id: Mapped[int] = mapped_column(ForeignKey("templates.id", ondelete="SET NULL"))
client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="SET NULL"))
user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
output_path: Mapped[str] = mapped_column(String(1024))
created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())


template = relationship("Template", back_populates="generations")
client = relationship("Client", back_populates="generations")
user = relationship("User", back_populates="generations")
