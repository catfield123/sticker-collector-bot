from sqlalchemy import Column, Integer, String, BigInteger, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class StickerPack(Base):
    __tablename__ = 'sticker_packs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    short_name = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    sticker_type = Column(String(50), nullable=False)  # regular, mask, custom_emoji
    link = Column(String(512), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship
    submissions = relationship("UserStickerSubmission", back_populates="sticker_pack")

    def __repr__(self):
        return f"<StickerPack(id={self.id}, short_name='{self.short_name}', name='{self.name}')>"


class UserStickerSubmission(Base):
    __tablename__ = 'user_sticker_submissions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    sticker_pack_id = Column(Integer, ForeignKey('sticker_packs.id'), nullable=False)
    submitted_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship
    sticker_pack = relationship("StickerPack", back_populates="submissions")

    # Unique constraint to prevent duplicate submissions from same user for same pack
    __table_args__ = (
        UniqueConstraint('user_id', 'sticker_pack_id', name='uix_user_sticker_pack'),
    )

    def __repr__(self):
        return f"<UserStickerSubmission(id={self.id}, user_id={self.user_id}, sticker_pack_id={self.sticker_pack_id})>"
