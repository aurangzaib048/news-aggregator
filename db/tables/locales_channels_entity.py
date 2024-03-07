from sqlalchemy import BigInteger, Column, DateTime, String, func

from db.tables.base import Base


class LocaleChannelEntity(Base):
    __tablename__ = "locales_channels"
    __table_args__ = {"schema": "news"}

    id = Column(BigInteger, primary_key=True, server_default=func.id_gen())
    locale = Column(String, nullable=False)
    channel_id = Column(BigInteger, nullable=False)
    created = Column(DateTime(timezone=True), server_default=func.now())
    modified = Column(
        DateTime(timezone=True), server_onupdate=func.now(), server_default=func.now()
    )

    def __repr__(self) -> dict:
        return {
            "id": self.id,
            "locale": self.locale,
            "channel_id": self.channel_id,
            "created": self.created,
            "modified": self.modified,
        }

    def __str__(self):
        return f"locale: {self.locale}, channel_id: {self.channel_id}"
