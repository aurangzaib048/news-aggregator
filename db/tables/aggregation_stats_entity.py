from sqlalchemy import UUID, BigInteger, Boolean, Column, DateTime, String

from db.tables.base import Base


class AggregationStatsEntity(Base):
    __tablename__ = "aggregation_stats"
    __table_args__ = {"schema": "news"}

    # id column should be created at the beginning of the job as a uuid type
    id = Column(UUID(as_uuid=True), primary_key=True)
    success = Column(Boolean, default=False)
    run_time = Column(BigInteger)
    locale_name = Column(String)
    start_time = Column(DateTime)
    feed_count = Column(BigInteger)
    start_article_count = Column(BigInteger)
    end_article_count = Column(BigInteger)
    cache_hit_count = Column(BigInteger)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "run_time": self.run_time,
            "locale_name": self.locale_name,
            "start_time": self.start_time,
        }

    def to_insert(self) -> dict:
        return {
            "locale_id": self.locale_id,
            "run_time": self.run_time,
            "locale_name": self.locale_name,
            "start_time": self.start_time,
        }

    def __str__(self):
        return f"aggregation_stats_entity(id={self.id!r})"
