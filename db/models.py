from sqlalchemy import (BigInteger, String, Text, DECIMAL, ForeignKey, TIMESTAMP, func)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase): pass


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String(32), nullable=True)
    first_name: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[TIMESTAMP] = mapped_column(TIMESTAMP, server_default=func.now())


class Request(Base):
    __tablename__ = 'requests'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.telegram_id'))
    user: Mapped["User"] = relationship()
    request_type: Mapped[str] = mapped_column(String(10), nullable=False)
    currency_from: Mapped[str] = mapped_column(String(50), nullable=False)
    money_type_from: Mapped[str] = mapped_column(String(50), nullable=False)
    location_from: Mapped[str] = mapped_column(String(50), nullable=False)
    amount: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)
    currency_to: Mapped[str] = mapped_column(String(50), nullable=False)
    money_type_to: Mapped[str] = mapped_column(String(50), nullable=False)
    location_to: Mapped[str] = mapped_column(String(50), nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(10), default='ACTIVE', nullable=False)
    group_message_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[TIMESTAMP] = mapped_column(TIMESTAMP, server_default=func.now())
    closed_at: Mapped[TIMESTAMP] = mapped_column(TIMESTAMP, nullable=True)
