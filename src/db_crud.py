import json
import re
from copy import deepcopy
from datetime import datetime, time

import structlog
from sqlalchemy import and_, func

from config import get_config
from csv_to_json import csv_to_dict_db
from db.tables.aggregation_stats_entity import AggregationStatsEntity
from db.tables.article_cache_record_entity import ArticleCacheRecordEntity
from db.tables.articles_entity import ArticleEntity
from db.tables.base import feed_locale_channel
from db.tables.channel_entity import ChannelEntity
from db.tables.external_article_classification_entity import (
    ExternalArticleClassificationEntity,
)
from db.tables.feed_entity import FeedEntity
from db.tables.feed_locales_entity import FeedLocaleEntity
from db.tables.feed_update_record_entity import FeedUpdateRecordEntity
from db.tables.locales_entity import LocaleEntity
from db.tables.publsiher_entity import PublisherEntity

config = get_config()
logger = structlog.getLogger(__name__)


def insert_or_update_publisher(session, publisher):
    """
    Insert a new publisher into the database or update an existing one
    """
    try:
        existing_publisher = (
            session.query(PublisherEntity).filter_by(url=publisher["site_url"]).first()
        )

        if existing_publisher:
            existing_publisher.favicon_url = publisher["favicon_url"]
            existing_publisher.cover_url = publisher["cover_url"]
            existing_publisher.background_color = publisher["background_color"]
            existing_publisher.enabled = publisher["enabled"]
            existing_publisher.score = publisher["score"]
            session.commit()
            session.refresh(existing_publisher)
            return existing_publisher
        else:
            new_publisher = PublisherEntity(
                url=publisher["site_url"],
                favicon_url=publisher["favicon_url"],
                cover_url=publisher["cover_url"],
                background_color=publisher["background_color"],
                enabled=publisher["enabled"],
                score=publisher["score"],
            )
            session.add(new_publisher)
            session.commit()
            session.refresh(new_publisher)
            return new_publisher

    except Exception as e:
        logger.error(e)
        session.rollback()
        return None


def insert_or_get_locale(session, locale):
    """
    Insert a new locale into the database
    """
    try:
        # Create a new locale entity
        new_locale = LocaleEntity(
            locale=locale,
            name=locale,
        )
        session.add(new_locale)
        session.commit()
        session.refresh(new_locale)

    except Exception as e:
        logger.error(e)
        session.rollback()
        new_locale = session.query(LocaleEntity).filter_by(locale=locale).first()

    return new_locale


def insert_or_get_channel(session, channel):
    """
    Insert a new channel into the database
    """
    try:
        new_channel = ChannelEntity(
            name=channel,
        )
        session.add(new_channel)
        session.commit()
        session.refresh(new_channel)
        return new_channel
    except Exception as e:
        logger.error(e)
        session.rollback()
        return session.query(ChannelEntity).filter_by(name=channel).first()


def insert_or_update_feed(session, feed_data, publisher_id):
    """
    Insert a new feed into the database or update the existing one.
    """
    try:
        existing_feed = (
            session.query(FeedEntity)
            .filter_by(
                url_hash=feed_data["publisher_id"], name=feed_data["publisher_name"]
            )
            .first()
        )

        if existing_feed:
            return existing_feed
        else:
            new_feed = FeedEntity(
                name=feed_data["publisher_name"],
                url=feed_data["feed_url"],
                url_hash=feed_data["publisher_id"],
                publisher_id=publisher_id,
                category=feed_data["category"],
                enabled=feed_data["enabled"],
                og_images=False,
                max_entries=20,
            )
            session.add(new_feed)
            session.commit()
            session.refresh(new_feed)
            return new_feed

    except Exception as e:
        logger.error(e)
        session.rollback()
        return session.query(FeedEntity).filter_by(url=feed_data["feed_url"]).first()


def insert_feed_locale(session, feed_id, locale_id, rank):
    """
    Insert a new feed_locale_channel into the database
    """
    try:
        new_feed_locale = FeedLocaleEntity(
            feed_id=feed_id,
            locale_id=locale_id,
            rank=rank,
        )
        session.add(new_feed_locale)
        session.commit()
        session.refresh(new_feed_locale)
        return new_feed_locale
    except Exception as e:
        logger.error(e)
        session.rollback()


def insert_or_update_all_publishers():
    logger.info("insert_or_update_all_publishers")
    """
    Insert or update all publishers in the database
    """
    try:
        locales_finder = re.compile(r"sources\.(.*)\.csv")
        source_files = config.sources_dir.glob("sources.*_*.csv")
        with config.get_db_session() as db_session:
            for source_file in source_files:
                csv_locale = locales_finder.findall(source_file.name)[0]
                try:
                    publisher_csv_data = csv_to_dict_db(csv_locale)
                    locale = insert_or_get_locale(db_session, csv_locale)
                    logger.info("Inserting publisher data")

                    for publisher_data in publisher_csv_data:
                        publisher = insert_or_update_publisher(
                            db_session, publisher_data
                        )

                        feed = insert_or_update_feed(
                            db_session,
                            publisher_data,
                            publisher_id=publisher.id,
                        )

                        feed_locale = insert_feed_locale(
                            db_session, feed.id, locale.id, publisher_data["rank"]
                        )

                        for channel_name in publisher_data["channels"]:
                            channel = insert_or_get_channel(db_session, channel_name)

                            try:
                                feed_locale.channels.append(channel)
                                db_session.commit()
                            except Exception:
                                logger.error(
                                    f"Channels data already inserted for {publisher.url}"
                                )

                    logger.info("Publisher data inserted successfully")

                except Exception as e:
                    logger.error(f"loading json data failed with {e}")
    except Exception as e:
        logger.error(f"Error Connecting to database: {e}")


def get_publisher_with_locale(publisher_url):
    """
    Get a publisher from the database
    """
    try:
        with config.get_db_session() as session:
            data = []
            publisher = (
                session.query(PublisherEntity).filter_by(url=publisher_url).first()
            )
            if publisher:
                publisher_data = {
                    "enabled": publisher.enabled,
                    "site_url": publisher.url,
                    "feed_url": "",
                    "category": "",
                    "favicon_url": publisher.favicon_url,
                    "cover_url": publisher.cover_url,
                    "background_color": publisher.background_color,
                    "score": publisher.score,
                    "publisher_id": "",
                    "locales": [],
                }

                feeds = (
                    session.query(FeedEntity).filter_by(publisher_id=publisher.id).all()
                )
                for feed in feeds:
                    feed_publisher_data = deepcopy(publisher_data)
                    feed_publisher_data["publisher_name"] = feed.name
                    feed_publisher_data["feed_url"] = feed.url
                    feed_publisher_data["category"] = feed.category
                    feed_publisher_data["enabled"] = feed.enabled
                    feed_publisher_data["publisher_id"] = feed.url_hash

                    for feed_locale in feed.locales:
                        locale_data = {
                            "locale": feed_locale.locale.locale,
                            "channels": [
                                channel.name for channel in feed_locale.channels
                            ],
                            "rank": feed_locale.rank,
                        }
                        feed_publisher_data["locales"].append(locale_data)

                    data.append(feed_publisher_data)

            return data
    except Exception as e:
        logger.error(f"Error Connecting to database: {e}")
        return []


def get_publishers_based_on_locale(locale):
    data = []
    try:
        with config.get_db_session() as session:
            feeds = (
                session.query(FeedEntity)
                .filter(
                    FeedEntity.locales.any(FeedLocaleEntity.locale.has(locale=locale))
                )
                .all()
            )

            for feed in feeds:
                channels = []
                for feed_locale in [
                    locale_model
                    for locale_model in feed.locales
                    if locale_model.locale.name == locale
                ]:
                    channels = list(
                        set([channel.name for channel in feed_locale.channels])
                    )

                publisher_data = {
                    "enabled": feed.publisher.enabled,
                    "publisher_name": feed.publisher.name,
                    "site_url": feed.publisher.url,
                    "feed_url": feed.url,
                    "category": feed.category,
                    "favicon_url": feed.publisher.favicon_url,
                    "cover_url": feed.publisher.cover_url,
                    "background_color": feed.publisher.background_color,
                    "score": feed.publisher.score,
                    "publisher_id": feed.url_hash,
                    "channels": list(set(channels)),
                }

                data.append(publisher_data)

            return data
    except Exception as e:
        logger.error(f"Error Connecting to database: {e}")
        return data


def insert_cache_record(article_id, locale, aggregation_id, db_session=None):
    try:
        with db_session or config.get_db_session() as session:
            locale = session.query(LocaleEntity).filter_by(locale=locale).first()
            db_article_cache_record = (
                session.query(ArticleCacheRecordEntity)
                .filter_by(article_id=article_id, locale_id=locale.id)
                .first()
            )
            if not db_article_cache_record:
                article_cache_record = ArticleCacheRecordEntity(
                    article_id=article_id,
                    locale_id=locale.id,
                    aggregation_id=aggregation_id,
                )
                session.add(article_cache_record)
                session.commit()

    except Exception as e:
        logger.error(f"Error Connecting to database: {e}")


def insert_article(article, locale_name, aggregation_id, db_session=None):
    try:
        with db_session or config.get_db_session() as db_session:
            try:
                feed = (
                    db_session.query(FeedEntity)
                    .filter(
                        FeedEntity.url_hash == article.get("publisher_id"),
                        FeedEntity.locales.any(
                            FeedLocaleEntity.locale.has(locale=locale_name)
                        ),
                    )
                    .first()
                )
                article_hash = article.get("url_hash")
                db_article = (
                    db_session.query(ArticleEntity)
                    .filter_by(url_hash=article_hash)
                    .first()
                )
                # if the article exists then insert as cache record
                if db_article:
                    insert_cache_record(
                        db_article.id, locale_name, aggregation_id, db_session
                    )
                    logger.info(f"Updated article {article.get('title')} to database")
                # else if the article does not exist then insert it into both article and cache record tables
                else:
                    new_article = ArticleEntity(
                        title=article.get("title"),
                        publish_time=article.get("publish_time"),
                        img=article.get("img"),
                        category=article.get("category"),
                        description=article.get("description"),
                        content_type=article.get("content_type"),
                        creative_instance_id=article.get("creative_instance_id"),
                        url=article.get("url"),
                        url_hash=article_hash,
                        pop_score=article.get("pop_score"),
                        padded_img=article.get("padded_img"),
                        score=article.get("score"),
                        feed_id=feed.id,
                        aggregation_id=aggregation_id,
                    )
                    db_session.add(new_article)
                    db_session.commit()
                    db_session.refresh(new_article)

                    insert_cache_record(
                        new_article.id, locale_name, aggregation_id, db_session
                    )

                    logger.info(f"Saved new article {article.get('title')} to database")
            except Exception as e:
                logger.error(f"Error saving articles to database: {e}")
    except Exception as e:
        logger.error(f"Error Connecting to database: {e}")


def get_article(url_hash, locale_name, db_session=None):
    try:
        with db_session or config.get_db_session() as session:
            article = session.query(ArticleEntity).filter_by(url_hash=url_hash).first()
            if article and locale_name in [
                locale_model.locale.name for locale_model in article.feed.locales
            ]:
                channels = []
                for feed_locale in [
                    locale_model
                    for locale_model in article.feed.locales
                    if locale_model.locale.name == locale_name
                ]:
                    channels = list(
                        set([channel.name for channel in feed_locale.channels])
                    )

                if article.img:
                    article_data = {
                        "title": article.title,
                        "publish_time": article.publish_time.strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                        "img": article.img,
                        "category": article.category,
                        "description": article.description,
                        "content_type": article.content_type,
                        "publisher_id": article.feed.url_hash,
                        "publisher_name": article.feed.name,
                        "channels": channels,
                        "creative_instance_id": article.creative_instance_id,
                        "url": article.url,
                        "url_hash": article.url_hash,
                        "pop_score": article.pop_score,
                        "padded_img": article.padded_img,
                        "score": article.score,
                    }

                    locale = (
                        session.query(LocaleEntity)
                        .filter_by(locale=locale_name)
                        .first()
                    )

                    article_cache_record = (
                        session.query(ArticleCacheRecordEntity)
                        .filter_by(article_id=article.id)
                        .filter(ArticleCacheRecordEntity.locale_id.in_([locale.id]))
                        .first()
                    )
                    if article_cache_record:
                        article_cache_record.cache_hit += 1
                        session.commit()
                        session.refresh(article_cache_record)

                    return article_data
                else:
                    return None
            else:
                return None
    except Exception as e:
        logger.error(f"Error Connecting to database: {e}")
        return None


def update_or_insert_article(article_data, locale, aggregation_id, db_session=None):
    logger.info(f"update_or_insert_article")
    try:
        with db_session or config.get_db_session() as session:
            article_hash = article_data.get("url_hash")
            article = (
                session.query(ArticleEntity).filter_by(url_hash=article_hash).first()
            )
            # if article exists, update it in the database with the new data
            if article:
                article.title = article_data.get("title")
                article.publish_time = article_data.get("publish_time")
                article.description = article_data.get("description")
                article.pop_score = article_data.get("pop_score")
                article.score = article_data.get("score", 0)

                if article_data.get("img") and article.img != article_data.get("img"):
                    article.img = article_data.get("img")
                    article.padded_img = article_data.get("padded_img")

                session.commit()
                session.refresh(article)

            else:
                insert_article(article_data, locale, aggregation_id, db_session)

    except Exception as e:
        logger.error(f"Error Connecting to database: {e}")
        return None


def get_remaining_articles(feed_url_hashes):
    try:
        articles = []
        with config.get_db_session() as session:
            remaining_articles = (
                session.query(ArticleEntity)
                .join(FeedEntity)
                .filter(~FeedEntity.url_hash.in_(feed_url_hashes))
                .all()
            )
            for article in remaining_articles:
                channels = []
                feed_locales = (
                    session.query(FeedLocaleEntity)
                    .filter_by(feed_id=article.feed.id)
                    .all()
                )
                for feed_locale in feed_locales:
                    channels.extend(
                        session.query(ChannelEntity)
                        .join(feed_locale_channel)
                        .filter_by(feed_locale_id=feed_locale.id)
                        .all()
                    )
                article_data = {
                    "title": article.title,
                    "publish_time": article.publish_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "img": article.img,
                    "category": article.category,
                    "description": article.description,
                    "content_type": article.content_type,
                    "publisher_id": article.feed.url_hash,
                    "publisher_name": article.feed.publisher.name,
                    "channels": [channel.name for channel in set(channels)],
                    "creative_instance_id": article.creative_instance_id,
                    "url": article.url,
                    "url_hash": article.url_hash,
                    "pop_score": article.pop_score,
                    "padded_img": article.padded_img,
                    "score": article.score,
                }
                articles.append(article_data)
            return articles
    except Exception as e:
        logger.error(f"Error Connecting to database: {e}")
        return []


def insert_feed_lastbuild(url_hash, last_build_time):
    try:
        with config.get_db_session() as session:
            feed = (
                session.query(FeedEntity)
                .filter(FeedEntity.url_hash == url_hash)
                .first()
            )
            if feed:
                last_record = (
                    session.query(FeedUpdateRecordEntity)
                    .filter(feed_id=feed.id)
                    .order_by(last_build_time.desc())
                    .first()
                )
                if last_record:
                    if last_build_time > last_record.last_build_time:
                        last_build_timedelta = datetime.utcnow() - last_build_time
                        last_record.last_build_time = last_build_time
                        last_record.last_build_timedelta = (
                            last_build_timedelta.total_seconds()
                        )
                        session.commit()
                        print("Feed update record updated successfully.")
                        return True
                    else:
                        print(
                            "New last_build_time is not greater than the previously inserted one."
                        )
                        return False
                else:
                    last_build_timedelta = datetime.utcnow() - last_build_time
                    new_record = FeedUpdateRecordEntity(
                        feed_id=feed.id,
                        last_build_time=last_build_time,
                        last_build_timedelta=last_build_timedelta.total_seconds(),
                    )
                    session.add(new_record)
                    session.commit()
                    print("Feed update record inserted successfully.")
                    return True
            else:
                print("Feed with URL hash {} not found.".format(url_hash))
                return False

    except Exception as e:
        logger.error(f"Error saving feed last build to database: {e}")


def get_locale_average_cache_hits(locale_name):
    try:
        one_day_ago = datetime.combine(datetime.utcnow(), time.min)
        with config.get_db_session() as session:
            locale = session.query(LocaleEntity).filter_by(locale=locale_name).first()
            feeds = (
                session.query(FeedEntity)
                .filter(
                    FeedEntity.locales.any(
                        FeedLocaleEntity.locale.has(locale=locale_name)
                    )
                )
                .all()
            )

            feed_articles = (
                session.query(ArticleEntity)
                .filter(
                    ArticleEntity.created >= one_day_ago.strftime("%Y-%m-%d %H:%M:%S"),
                    ArticleEntity.feed_id.in_([feed.id for feed in feeds]),
                )
                .all()
            )

            cache_hits = (
                session.query(func.count(ArticleCacheRecordEntity.cache_hit))
                .filter(
                    ArticleCacheRecordEntity.article_id.in_(
                        [article.id for article in feed_articles]
                    ),
                    ArticleCacheRecordEntity.locale_id.in_([locale.id]),
                )
                .first()
            )

            cache_hits = cache_hits[0] if cache_hits[0] else 0
            total_articles = len(feed_articles)

            logger.info(f"Total articles: {total_articles}")
            logger.info(f"Cache hits: {cache_hits}")

            cache_hit_percentage = (cache_hits / total_articles) * 100

            logger.info(f"Average cache hits: {cache_hit_percentage}")

            return cache_hit_percentage

    except Exception as e:
        logger.error(f"Error Connecting to database: {e}")


def get_global_average_cache_hits():
    try:
        one_day_ago = datetime.combine(datetime.utcnow(), time.min)
        with config.get_db_session() as session:
            articles = (
                session.query(ArticleEntity)
                .filter(
                    ArticleEntity.created >= one_day_ago.strftime("%Y-%m-%d %H:%M:%S")
                )
                .all()
            )

            cache_hits = (
                session.query(func.count(ArticleCacheRecordEntity.cache_hit))
                .filter(
                    ArticleCacheRecordEntity.article_id.in_(
                        [article.id for article in articles]
                    )
                )
                .first()
            )

            cache_hits = cache_hits[0] if cache_hits[0] else 0
            total_articles = len(articles)

            logger.info(f"Total articles: {total_articles}")
            logger.info(f"Cache hits: {cache_hits}")

            cache_hit_percentage = (cache_hits / total_articles) * 100

            logger.info(f"Average cache hits: {cache_hit_percentage}")

            return cache_hit_percentage

    except Exception as e:
        logger.error(f"Error Connecting to database: {e}")


def insert_external_channels(url_hash, external_channels, raw_data, db_session=None):
    try:
        with db_session or config.get_db_session() as session:
            article_hash = url_hash
            article = (
                session.query(ArticleEntity).filter_by(url_hash=article_hash).first()
            )
            if article:
                new_external_channel = ExternalArticleClassificationEntity(
                    article_id=article.id,
                    channels=external_channels,
                    raw_data=json.dumps([{i.name: i.confidence} for i in raw_data]),
                )
                session.add(new_external_channel)
                session.commit()
                session.refresh(new_external_channel)
    except Exception as e:
        logger.error(f"Error Connecting to database: {e}")


def get_article_with_external_channels(url_hash, locale):
    try:
        with config.get_db_session() as session:
            article_hash = url_hash
            article_from_db = (
                session.query(ArticleEntity).filter_by(url_hash=article_hash).first()
            )
            article = get_article(url_hash, locale, session)
            if article:
                external_channels = (
                    session.query(ExternalArticleClassificationEntity)
                    .filter_by(article_id=article_from_db.id)
                    .first()
                )
                article.update({"external_channels": external_channels.channels})
                article.update({"raw_data": external_channels.raw_data})
                return article
            else:
                return None
    except Exception as e:
        logger.error(f"Error Connecting to database: {e}")


def external_channel_stats(locale):
    try:
        with config.get_db_session() as session:
            data = []
            locale = session.query(LocaleEntity).filter_by(locale=locale).first()
            articles = (
                session.query(
                    ArticleEntity,
                    func.array_agg(ChannelEntity.name).label("channels"),
                )
                .join(
                    ExternalArticleClassificationEntity,
                    ArticleEntity.id == ExternalArticleClassificationEntity.article_id,
                )
                .join(
                    FeedLocaleEntity,
                    ArticleEntity.feed_id == FeedLocaleEntity.feed_id,
                )
                .join(
                    feed_locale_channel,
                    FeedLocaleEntity.id == feed_locale_channel.c.feed_locale_id,
                )
                .join(
                    ChannelEntity, feed_locale_channel.c.channel_id == ChannelEntity.id
                )
                .filter(
                    and_(
                        func.array_length(
                            ExternalArticleClassificationEntity.channels, 1
                        )
                        > 0,
                        # Check that array length is greater than 0
                        ExternalArticleClassificationEntity.channels.isnot(
                            None
                        ),  # Ensure channels is not NULL
                        FeedLocaleEntity.locale_id == locale.id,
                    )
                )
                .order_by(ArticleEntity.created.desc())
                .group_by(ArticleEntity.id)
                # .first()
                .limit(100000)
                .all()
            )

            for result in articles:
                article, channels = result

                article_data = {
                    "publisher": article.feed.publisher.name,
                    "title": article.title,
                    "description": article.description,
                    "channels": channels,
                    "external_channels": article.external_channels[0].channels,
                    "raw_data": article.external_channels[0].raw_data,
                }

                data.append(article_data)

            return data

    except Exception as e:
        logger.error(f"Error Connecting to database: {e}")


def get_channels():
    try:
        with config.get_db_session() as session:
            channels = session.query(ChannelEntity.name).distinct().all()

            return sorted([channel.name for channel in channels])
    except Exception as e:
        logger.error(f"Error Connecting to database: {e}")
        return []


def insert_aggregation_stats(id, start_time, locale_name):
    try:
        with config.get_db_session() as session:
            aggregation_stats = AggregationStatsEntity(
                id=id,
                start_time=start_time,
                locale_name=locale_name,
            )
            session.add(aggregation_stats)
            session.commit()
            session.refresh(aggregation_stats)
            return aggregation_stats.id
    except Exception as e:
        logger.error(f"Error Connecting to database: {e}")
        return None


def update_aggregation_stats(
    id,
    run_time=0,
    success=False,
    feed_count=0,
    start_article_count=0,
    end_article_count=0,
    cache_hit_count=0,
    db_session=None,
):
    try:
        with db_session or config.get_db_session() as session:
            record = session.query(AggregationStatsEntity).filter_by(id=id).first()
            if record:
                record.run_time = record.run_time or run_time
                record.success = record.success or success
                record.feed_count = record.feed_count or feed_count
                record.start_article_count = (
                    record.start_article_count or start_article_count
                )
                record.end_article_count = record.end_article_count or end_article_count
                record.cache_hit_count = record.cache_hit_count or cache_hit_count
                session.commit()
                session.refresh(record)
                return record.id
            else:
                logger.error(f"Record with id {id} not found")
                return None
    except Exception as e:
        logger.error(f"Error Connecting to database: {e}")
        return None


def get_locales():
    try:
        with config.get_db_session() as session:
            locales = session.query(LocaleEntity.locale).distinct().all()

            return sorted([locale.locale for locale in locales])
    except Exception as e:
        logger.error(f"Error Connecting to database: {e}")
        return []


def get_articles_with_locale(
    locale, start_datetime, page: int = 1, page_size: int = 100
):
    try:
        with config.get_db_session() as session:
            locale_entity = session.query(LocaleEntity).filter_by(locale=locale).first()
            if not locale_entity:
                raise ValueError(f"Locale {locale} not found in the database.")

            offset = (page - 1) * page_size

            articles = (
                session.query(ArticleEntity)
                .join(FeedEntity)
                .join(FeedLocaleEntity)
                .filter(
                    FeedLocaleEntity.locale_id == locale_entity.id,
                    ArticleEntity.created >= start_datetime,
                )
                .distinct()
                .order_by(ArticleEntity.created.desc())
                .offset(offset)
                .limit(page_size)
                .all()
            )

            data = []
            for article in articles:
                article_data = {
                    "title": article.title,
                    "publish_time": article.publish_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "img": article.img,
                    "category": article.category,
                    "description": article.description,
                    "content_type": article.content_type,
                    "publisher_id": article.feed.url_hash,
                    "publisher_name": article.feed.publisher.name,
                    "creative_instance_id": article.creative_instance_id,
                    "url": article.url,
                    "url_hash": article.url_hash,
                    "pop_score": article.pop_score,
                    "padded_img": article.padded_img,
                    "score": article.score,
                }

                data.append(article_data)

            return data
    except Exception as e:
        logger.error(f"Error Connecting to database: {e}")
        return []


if __name__ == "__main__":
    insert_or_update_all_publishers()
    # get_locale_average_cache_hits("en_GB_2")
    # get_global_average_cache_hits()
