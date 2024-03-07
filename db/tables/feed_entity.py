from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, String, func

from db.tables.base import Base


class FeedEntity(Base):
    __tablename__ = "feeds"
    __table_args__ = {"schema": "news"}

    id = Column(BigInteger, primary_key=True, server_default=func.id_gen())
    url = Column(String, nullable=False, unique=True)
    url_hash = Column(String, nullable=False, unique=True)
    publisher_id = Column(BigInteger, ForeignKey("publishers.id"), nullable=False)
    category = Column(String, nullable=False)
    enabled = Column(Boolean, default=True)
    locale_id = Column(BigInteger, ForeignKey("locales.id"), nullable=False)
    created = Column(DateTime(timezone=True), server_default=func.now())
    modified = Column(
        DateTime(timezone=True), server_onupdate=func.now(), server_default=func.now()
    )

    def __repr__(self) -> dict:
        return {
            "id": self.id,
            "url": self.url,
            "url_hash": self.url_hash,
            "publisher_id": self.publisher_id,
            "category": self.category,
            "enabled": self.enabled,
            "locale_id": self.locale_id,
            "created": self.created,
            "modified": self.modified,
        }

    def __str__(self):
        return f"<FeedEntity(id={self.id}, url={self.url}, publisher_id={self.publisher_id}, category={self.category})>"
