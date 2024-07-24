from sqlalchemy import BigInteger, Column, DateTime, func, Boolean, UUID, String

from db.tables.base import Base

class AggregationStatsEntity(Base):
    __tablename__ = "aggregation_stats"
    __table_args__ = {"schema": "news"}

    # id column should be created at the beginning of the job as a uuid type
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.id_gen())
    created = Column(DateTime, nullable=False, server_default=func.now())
    success = Column(Boolean, nullable=False, default=False)
    run_time = Column(BigInteger, nullable=False)
    locale_name = Column(String, nullable=False)
    start_time = Column(DateTime, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "created": self.created,
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

