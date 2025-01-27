import hashlib
from datetime import datetime

import pytest
import pytz
from requests import HTTPError

from feed_processor_multi import (
    download_feed,
    get_popularity_score,
    get_predicted_category,
    get_with_max_size,
    parse_rss,
    process_articles,
    process_image,
    scrub_html,
    unshorten_url,
)


class TestGetWithMaxSize:
    # Successfully retrieves content from a URL
    def test_retrieves_content(self):
        # Arrange
        url = "http://example.com"

        # Act
        result = get_with_max_size(url)

        # Assert
        assert result is not None
        assert isinstance(result, bytes)

    # Raises HTTPError for non-200 status codes
    def test_raises_http_error(self):
        # Arrange
        url = "http://example.com/nonexistent"

        # Act & Assert
        with pytest.raises(HTTPError):
            get_with_max_size(url)


class TestDownloadFeed:
    # Downloading a feed with a valid URL and default max_feed_size.
    def test_valid_url_default_max_feed_size(self):
        feed_url = "https://brave.com/blog/index.xml"
        result = download_feed(feed_url)
        assert result is not None
        assert "feed_cache" in result
        assert "key" in result

    # Downloading a feed with an invalid URL.
    def test_invalid_url(self):
        feed_url = "https://example.com/invalid_feed"
        result = download_feed(feed_url)
        assert result is None


class TestParseRss:
    # Successfully parse a downloaded RSS feed with at least one article.
    def test_parse_rss_success(self):
        downloaded_feed = {
            "key": "https://example.com/rss_feed",
            "feed_cache": "<rss version='2.0'><channel><title>Example Feed</title><item><title>Article 1"
            "</title></item></channel></rss>",
        }

        result = parse_rss(downloaded_feed)

        assert result is not None

    # Fail to parse a downloaded RSS feed with no articles.
    def test_parse_rss_failure(self):
        downloaded_feed = {
            "key": "https://example.com/rss_feed",
            "feed_cache": "<rss version='2.0'><channel><title>Example Feed</title></channel></rss>",
        }

        assert parse_rss(downloaded_feed) is None


class TestProcessImage:
    # item has 'img' key
    def test_item_has_img_key(self):
        item = {
            "img": "https://www.usmagazine.com/wp-content/uploads/2023/10/Ed-Sheeran-s-Reason-for-"
            "Building-His-Final-Resting-Place-in-His-Own-Backyard-Will-Gut-You-297."
            "jpg?crop=0px%2C86px%2C1331px%2C700px&resize=1200%2C630&quality=86&strip=all"
        }
        process_image(item)
        assert item["img"] is not None
        assert item["padded_img"] is not None

    # item has 'img' key but its value is None
    def test_item_img_value_is_none(self):
        item = {"img": None}
        process_image(item)
        assert item["img"] == ""
        assert item["padded_img"] == ""


class TestProcessArticles:
    # Process a valid article with all required fields.

    def test_valid_article_with_required_fields(
        self,
        fake_date=datetime.now().replace(tzinfo=pytz.utc).strftime("%Y-%m-%d"),
    ):
        article = {
            "title": "Example Article",
            "link": "https://www.example.com/article",
            "updated": fake_date,
            "description": "This is an example article",
            "publisher_id": "example_publisher",
            "publisher_name": "Example Publisher",
            "creative_instance_id": "example_creative_instance",
            "category": "example_category",
            "content_type": "text",
        }

        _publisher = {
            "publisher_id": "example_publisher",
            "publisher_name": "Example Publisher",
            "creative_instance_id": "example_creative_instance",
            "category": "example_category",
            "content_type": "text",
        }

        processed_article = process_articles(article, _publisher)

        assert processed_article is not None
        assert processed_article["title"] == "Example Article"
        assert processed_article["link"] == "https://www.example.com/article"
        assert processed_article["img"] == ""
        assert processed_article["category"] == "example_category"
        assert processed_article["description"] == "This is an example article"
        assert processed_article["content_type"] == "text"
        assert processed_article["publisher_id"] == "example_publisher"
        assert processed_article["publisher_name"] == "Example Publisher"
        assert processed_article["creative_instance_id"] == "example_creative_instance"

    # Skip processing an article with no title.
    def test_skip_article_with_no_title(self):
        article = {
            "link": "https://www.example.com/article",
            "updated": "2022-01-01T12:00:00Z",
            "description": "This is an example article",
            "publisher_id": "example_publisher",
            "publisher_name": "Example Publisher",
            "creative_instance_id": "example_creative_instance",
            "category": "example_category",
            "content_type": "text",
        }

        _publisher = {
            "publisher_id": "example_publisher",
            "publisher_name": "Example Publisher",
            "creative_instance_id": "example_creative_instance",
            "category": "example_category",
            "content_type": "text",
        }

        processed_article = process_articles(article, _publisher)

        assert processed_article is None

    # Skip processing an article with a profanity in the title.
    def test_skip_article_with_profanity_in_title(self, mocker):
        mocker.patch("better_profanity.profanity.contains_profanity", return_value=True)

        article = {
            "title": "Example Article with profanity",
            "link": "https://www.example.com/article",
            "updated": "2022-01-01T12:00:00Z",
            "description": "This is an example article",
            "publisher_id": "example_publisher",
            "publisher_name": "Example Publisher",
            "creative_instance_id": "example_creative_instance",
            "category": "example_category",
            "content_type": "text",
        }

        _publisher = {
            "publisher_id": "example_publisher",
            "publisher_name": "Example Publisher",
            "creative_instance_id": "example_creative_instance",
            "category": "example_category",
            "content_type": "text",
        }

        processed_article = process_articles(article, _publisher)

        assert processed_article is None


class TestUnshortenUrl:
    # Unshortens a valid URL.
    def test_unshorten_valid_url(self, mocker):
        # Mock the unshortener object
        mock_unshortener = mocker.Mock()
        mocker.patch("unshortenit.UnshortenIt", return_value=mock_unshortener)

        # Mock the unshorten method
        mock_unshortener.unshorten.return_value = "https://example.com"

        # Create the input article
        out_article = {
            "link": "https://bit.ly/3i2QJgA",
            "title": "Example Article",
            "author": "John Doe",
        }

        # Call the function under test
        result = unshorten_url(out_article)

        # Assert the unshortened URL is correct
        assert result["url"] == "https://example.com"

        # Assert the link key is removed
        assert "link" not in result

        # Assert the URL hash is correct
        assert (
            result["url_hash"]
            == hashlib.sha256("https://example.com".encode("utf-8")).hexdigest()
        )

        # Assert the URL is encoded
        assert result["url"] == "https://example.com"

    # Skips unshortening if the URL is None.
    def test_skip_unshortening_if_url_none(self, mocker):
        # Create the input article with None URL
        out_article = {"link": None, "title": "Example Article", "author": "John Doe"}

        # Call the function under test
        result = unshorten_url(out_article)

        # Assert the result is None
        assert result is None


class TestGetPopularityScore:
    # Successfully retrieves popularity score for an article.
    def test_retrieves_popularity_score(self, mocker):
        # Mock the get_with_max_size function to return a sample response
        mocker.patch(
            "feed_processor_multi.get_with_max_size",
            return_value=b'{"popularity": {"popularity": {"score1": 1, "score2": 2}}}',
        )

        # Create a sample article
        out_article = {
            "url": "https://example.com/article",
            "title": "Example Article",
            "author": "John Doe",
            "publish_time": "2022-01-01T12:00:00Z",
        }

        # Call the get_popularity_score function
        result = get_popularity_score(out_article)

        # Assert that the popularity score is None
        assert result["pop_score"] == 3

    # URL is invalid or empty.
    def test_invalid_or_empty_url(self, mocker):
        # Mock the get_with_max_size function to raise an exception
        mocker.patch(
            "feed_processor_multi.get_with_max_size",
            side_effect=ValueError("Content-Length too large"),
        )

        # Create a sample article with an invalid URL
        out_article = {
            "url": "",
            "title": "Example Article",
            "author": "John Doe",
            "publish_time": "2022-01-01T12:00:00Z",
        }

        # Call the get_popularity_score function
        result = get_popularity_score(out_article)

        # Assert that the popularity score is None
        assert result["pop_score"] == 1.0


class TestGetPredictedCategory:
    # Retrieves predicted category for a valid article.
    def test_retrieves_predicted_category(self, mocker):
        # Mock the requests.post method to return a mock response
        mock_response = mocker.Mock()
        mock_response.json.return_value = {
            "results": [
                {
                    "reliability": "high",
                    "categories": [
                        {"name": "Technology", "confidence": 0.9},
                        {"name": "Science", "confidence": 0.8},
                    ],
                }
            ]
        }
        mocker.patch("requests.post", return_value=mock_response)

        # Define the input article
        article = {
            "title": "Example Article",
            "content": "This is an example article.",
            "url": "https://example.com/article",
            "publish_time": "2022-01-01T00:00:00Z",
        }

        # Invoke the function under test
        result = get_predicted_category(article)

        # Assert the expected output
        assert result == {
            "title": "Example Article",
            "content": "This is an example article.",
            "url": "https://example.com/article",
            "publish_time": "2022-01-01T00:00:00Z",
            "predicted_category": {
                "reliability": "high",
                "category": "Technology",
                "confidence": 0.9,
            },
        }

    # Handles an empty article and returns None as predicted category.
    def test_handles_empty_article(self, mocker):
        # Mock the requests.post method to return a mock response
        mock_response = mocker.Mock()
        mock_response.json.return_value = {"results": []}
        mocker.patch("requests.post", return_value=mock_response)

        # Define the input article
        article = {}

        # Invoke the function under test
        result = get_predicted_category(article)

        # Assert the expected output
        assert result == {"predicted_category": None}


class TestScrubHtml:
    # Scrubs HTML content in a dictionary with valid HTML tags and attributes.
    def test_valid_html_tags_and_attributes(self):
        feed = {
            "title": "<h1>This is a title</h1>",
            "description": "<p>This is a description</p>",
            "content": "<div>This is some content</div>",
        }

        scrubbed_feed = scrub_html(feed)

        assert scrubbed_feed["title"] == "This is a title"
        assert scrubbed_feed["description"] == "This is a description"
        assert scrubbed_feed["content"] == "This is some content"

    # Scrubs HTML content in a dictionary with invalid HTML tags and attributes.
    def test_invalid_html_tags_and_attributes(self):
        feed = {
            "title": "<h1>This is a title</h1>",
            "description": "<p>This is a description</p>",
            "content": "<script>alert('Hello World!')</script>",
        }

        scrubbed_feed = scrub_html(feed)

        assert scrubbed_feed["title"] == "This is a title"
        assert scrubbed_feed["description"] == "This is a description"
        assert scrubbed_feed["content"] == "alert('Hello World!')"
