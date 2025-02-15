# News Aggregator
This project is the backend side of Brave News, and it fetches the articles from the Brave-defined publishers and
shows their feeds/News in the Browser.

For more details: https://brave.com/brave-news-updates/

## Setup

### Dependencies
Python Version (Required):

    Python 3.9

Required setup:
```sh
    virtualenv -p /usr/bin/python3.9 .venv
    . .venv/bin/activate
    pip install -r requirements.dev.txt
```

### Running locally

To generate sources and list of feeds:
```sh
    export PYTHONPATH=$PWD:$PWD/src
    NO_UPLOAD=1 NO_DOWNLOAD=1 python src/csv_to_json.py
```
To generate browser feed and images:
```sh
    export PYTHONPATH=$PWD:$PWD/src
    NO_UPLOAD=1 python src/feed_processor_multi.py feed
```
To update the favicon urls:
```sh
    export PYTHONPATH=$PWD:$PWD/src
    NO_UPLOAD=1 NO_DOWNLOAD=1 python src/favicons_covers/update_favicon_urls.py
```
Populate DB with publisher data (channels, feeds, locales, publishers)
```sh
    # calls insert_or_update_all_publishers()
    export PYTHONPATH=$PWD:$PWD/src
    python -u src/db_crud.py
```

#### Run local migrations
In order to run migrations locally update the following:

Set database_url to localhost:
https://github.com/brave/news-aggregator/blob/master/config.py#L136
```sh
Optional[str] = "postgres://localhost:5432"
```

Set db url to localhost: https://github.com/brave/news-aggregator/blob/master/alembic.ini#L9
```sh
sqlalchemy.url = postgresql://localhost:5432
```
Then you can run:
```sh
make migrate-up
# or
make migrate-down
```

**Running the tests will run the aggregator**
```sh
make test
```

### Organization

This service organizes as follows:
```
news_aggregator/
├── bin/                # This dir contains the helping shell scripts for Dockerfile.
├── db/                 # This dir contains the database schema.
├── lib/                # This dir contains the utility modules.
├── models/             # This dir contains the dataclasses.
├── sources/            # This dir contains the sources files.
├── src/                # This dir contains all the python script to run the new aggregator.
├── tests/              # This dir contains the tests.
```

Detailed DB README: [db/README.md](db/README.md)

### Contribution

We configured the pre-commit hooks to ensure the quality of the code. To set-up the pre-commit hooks run the following
commands:
```sh
    pre-commit install
    pre-commit run --all-files
```

# wasm_thumbnail

The `wasm_thumbnail.wasm` binary comes from <https://github.com/brave-intl/wasm-thumbnail>.
