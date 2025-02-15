import datetime
import json
import shutil

import orjson
import structlog

from aggregator.aggregate import Aggregator
from config import get_config
from db_crud import get_channels, insert_article, update_aggregation_stats
from utils import upload_file

config = get_config()
logger = structlog.getLogger(__name__)

if __name__ == "__main__":
    feed_sources = config.output_path / config.feed_sources_path

    with open(feed_sources) as f:
        publishers = orjson.loads(f.read())
        output_path = config.output_feed_path / f"{config.feed_path}.json-tmp"

    fp = Aggregator(publishers, output_path)
    fp.aggregate()
    shutil.copyfile(
        config.output_feed_path / f"{config.feed_path}.json-tmp",
        config.output_feed_path / f"{config.feed_path}.json",
    )
    with open(config.output_path / config.channel_file, "w") as f:
        channels = get_channels()
        f.write(json.dumps(channels))

    if not config.no_upload:
        upload_file(
            config.output_feed_path / f"{config.feed_path}.json",
            config.pub_s3_bucket,
            f"brave-today/{config.feed_path}{str(config.sources_file).replace('sources', '')}.json",
        )
        # Temporarily upload also with incorrect filename as a stopgap for
        # https://github.com/brave/brave-browser/issues/20114
        # Can be removed once fixed in the brave-core client for all Desktop users.
        upload_file(
            config.output_feed_path / f"{config.feed_path}.json",
            config.pub_s3_bucket,
            f"brave-today/{config.feed_path}{str(config.sources_file).replace('sources', '')}json",
        )
        upload_file(
            config.output_path / config.channel_file,
            config.pub_s3_bucket,
            f"brave-today/{config.channel_file}",
        )

    articles = []
    db_session = config.get_db_session()
    with open(config.output_feed_path / f"{config.feed_path}.json", "r") as f:
        articles = orjson.loads(f.read())
        locale_name = str(config.sources_file).replace("sources.", "")
        aggregation_id = fp.aggregation_id
        logger.info(f"Feed has {len(articles)} items to insert.")
        # for each article, insert into the database, do not use threads
        for article in articles:
            insert_article(
                article,
                locale_name=locale_name,
                aggregation_id=aggregation_id,
                db_session=db_session,
            )

    with open(config.output_path / "report.json", "w") as f:
        f.write(json.dumps(fp.report))

    # Store remaining aggregation stats
    logger.info("storing aggregation stats")
    processing_time_in_seconds = (
        datetime.datetime.now() - fp.start_time
    ).total_seconds()
    update_aggregation_stats(
        id=fp.aggregation_id,
        run_time=processing_time_in_seconds,
        success=True,
        db_session=db_session,
        end_article_count=len(articles),
    )
    logger.info(f"\nCompleted in {processing_time_in_seconds} seconds")
    logger.info(f"DB sessions created {config.db_connections_created}")
