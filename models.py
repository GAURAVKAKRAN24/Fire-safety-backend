from datetime import datetime, timezone

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from database import engine


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    phone: Mapped[str] = mapped_column(String, nullable=False)
    address: Mapped[str | None] = mapped_column(String)


# Create the extinguishers table in the database

class Extinguisher(Base):
    __tablename__ = "extinguishers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey("customers.id"), nullable=False)
    extinguisher_no: Mapped[str | None] = mapped_column(String)
    type: Mapped[str] = mapped_column(String, nullable=False)
    capacity: Mapped[str] = mapped_column(String, nullable=False)
    purchase_date: Mapped[str | None] = mapped_column(String)
    last_service_date: Mapped[str | None] = mapped_column(String)
    next_service_date: Mapped[str | None] = mapped_column(String)
    status: Mapped[str | None] = mapped_column(String, default="Active")


class Service(Base):
    __tablename__ = "services" # Services table name

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    extinguisher_id: Mapped[int] = mapped_column(Integer, ForeignKey("extinguishers.id"), nullable=False)
    service_type: Mapped[str] = mapped_column(String, nullable=False)
    service_date: Mapped[str] = mapped_column(String, nullable=False)
    next_service_date: Mapped[str | None] = mapped_column(String, nullable=False)
    amount: Mapped[int | None] = mapped_column(Integer, nullable=False)
    remarks: Mapped[str | None] = mapped_column(String)


class Notification(Base):
    __tablename__ = "notifications" # Notifications table name

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey("customers.id"), nullable=False)
    extinguisher_id: Mapped[int] = mapped_column(Integer, ForeignKey("extinguishers.id"), nullable=False)
    notification_type: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(String, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[str] = mapped_column(String, default=lambda: datetime.now(timezone.utc), nullable=False)

Base.metadata.create_all(bind=engine) # Create All table in the database

print("Tables created successfully.")