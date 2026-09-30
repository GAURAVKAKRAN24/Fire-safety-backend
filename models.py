from datetime import datetime, timezone

from sqlalchemy import Boolean, ForeignKey, Integer, String, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from database import engine


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    google_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    profile_picture: Mapped[str | None] = mapped_column(String(500), nullable=True)
    auth_provider: Mapped[str] = mapped_column(String(20), default="local", nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="STAFF", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    phone: Mapped[str] = mapped_column(String, nullable=False)
    address: Mapped[str | None] = mapped_column(String)


class Extinguisher(Base):
    __tablename__ = "extinguishers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    extinguisher_no: Mapped[str | None] = mapped_column(String)
    type: Mapped[str] = mapped_column(String, nullable=False)
    capacity: Mapped[str] = mapped_column(String, nullable=False)
    purchase_date: Mapped[str | None] = mapped_column(String)
    last_service_date: Mapped[str | None] = mapped_column(String)
    next_service_date: Mapped[str | None] = mapped_column(String)
    status: Mapped[str | None] = mapped_column(String, default="Active")


class Service(Base):
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    extinguisher_id: Mapped[int] = mapped_column(Integer, ForeignKey("extinguishers.id", ondelete="CASCADE"), nullable=False)
    service_type: Mapped[str] = mapped_column(String, nullable=False)
    service_date: Mapped[str] = mapped_column(String, nullable=False)
    next_service_date: Mapped[str | None] = mapped_column(String, nullable=True)
    amount: Mapped[str | None] = mapped_column(String, nullable=True)
    remarks: Mapped[str | None] = mapped_column(String, nullable=True)


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    extinguisher_id: Mapped[int] = mapped_column(Integer, ForeignKey("extinguishers.id", ondelete="CASCADE"), nullable=False)
    notification_type: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(String, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[str] = mapped_column(String, default=lambda: str(datetime.now(timezone.utc)), nullable=False)


# Ensure all tables exist
Base.metadata.create_all(bind=engine)

# Auto-migrate schema updates for existing tables
try:
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE customers ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id) ON DELETE CASCADE;"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_customers_user_id ON customers(user_id);"))
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users(lower(email));"))
        conn.execute(text("""
            ALTER TABLE extinguishers DROP CONSTRAINT IF EXISTS extinguishers_customer_id_fkey;
            ALTER TABLE extinguishers ADD CONSTRAINT extinguishers_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE;
            ALTER TABLE services DROP CONSTRAINT IF EXISTS services_extinguisher_id_fkey;
            ALTER TABLE services ADD CONSTRAINT services_extinguisher_id_fkey FOREIGN KEY (extinguisher_id) REFERENCES extinguishers(id) ON DELETE CASCADE;
            ALTER TABLE notifications DROP CONSTRAINT IF EXISTS notifications_customer_id_fkey;
            ALTER TABLE notifications ADD CONSTRAINT notifications_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE;
            ALTER TABLE notifications DROP CONSTRAINT IF EXISTS notifications_extinguisher_id_fkey;
            ALTER TABLE notifications ADD CONSTRAINT notifications_extinguisher_id_fkey FOREIGN KEY (extinguisher_id) REFERENCES extinguishers(id) ON DELETE CASCADE;
            CREATE UNIQUE INDEX IF NOT EXISTS uq_extinguisher_unread_service_due ON notifications (extinguisher_id, notification_type) WHERE is_read = false;
        """))
        conn.commit()
except Exception as e:
    print(f"Schema migration note: {e}")

print("Tables verified and created successfully.")