from sqlalchemy import Column, Integer, String, BigInteger, DateTime, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import os


Base = declarative_base()


class GuildMember(Base):
    __tablename__ = "guild_members"

    id = Column(Integer, primary_key=True)
    discord_id = Column(String(50), nullable=True)
    character_name = Column(String(50), nullable=False)
    character_id = Column(String(100), unique=True, nullable=False)
    server_id = Column(Integer, nullable=False)
    server_name = Column(String(20))
    class_name = Column(String(20))
    race_name = Column(String(20))
    registered_at = Column(DateTime, default=datetime.utcnow)

    history = relationship("CombatPowerHistory", back_populates="member", cascade="all, delete-orphan")


class CombatPowerHistory(Base):
    __tablename__ = "combat_power_history"

    id = Column(Integer, primary_key=True)
    member_id = Column(Integer, ForeignKey("guild_members.id"))
    combat_power = Column(BigInteger, nullable=False)
    item_level = Column(Integer)
    level = Column(Integer)
    recorded_at = Column(DateTime, default=datetime.utcnow)

    member = relationship("GuildMember", back_populates="history")


os.makedirs("data", exist_ok=True)

engine = create_engine("sqlite:///./data/aion2.db", echo=False)
SessionLocal = sessionmaker(bind=engine)


def init_db():
    Base.metadata.create_all(engine)
