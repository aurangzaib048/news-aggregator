export PYTHONPATH=$(PWD):$(PWD)/src

all:

clean:
	rm -rf sources-orig.csv feed.json sources.json sources.json report.json feed/
	rm -rf __pycache__ */__pycache__ .pytest_cache

pytest:
	echo Running pytest...
	pytest -s tests/

validjson:
	export PYTHONPATH=$PWD:$PWD/src
	mv sources/sources.csv sources/sources-orig.csv ; head -5 sources/sources-orig.csv > sources/sources.csv
	echo Checking that csv_to_json.py creates valid JSON files...
	NO_UPLOAD=1 NO_DOWNLOAD=1 python src/csv_to_json.py
	mv sources/sources-orig.csv sources/sources.csv
	python ./tests/json_verify.py < output/sources.json
	python ./tests/json_verify.py < output/feed_source.json
	echo Checking that sources.json is of the expected size...
	echo Checking that feed.json is of the expected size...
	echo System $(shell uname)
ifeq ($(shell uname), Linux)
	test `stat -c%s output/sources.json` -gt 10
else ifeq ($(shell uname), Darwin)
	test `stat -f%z output/sources.json` -gt 10
endif
	echo Checking that main.py creates a valid JSON file...
	NO_UPLOAD=1 NO_DOWNLOAD=1 SOURCES_FILE=sources.en_US python src/main.py
	python ./tests/json_verify.py < output/feed/feed.json
	echo Checking that the report makes sense...
	python lib/report-check.py
	echo Checking that feed/feed.json is of the expected size...
ifeq ($(shell uname), Linux)
	test `stat -c%s output/feed/feed.json` -gt 1000
else ifeq ($(shell uname), Darwin)
	test `stat -f%z output/feed/feed.json` -gt 1000
endif

migrate-up:
	alembic upgrade head

migrate-down:
	alembic downgrade base


test: pytest validjson

api-prod:
	export PYTHONPATH=$PWD:$PWD/src
	fastapi run api/__init__.py --proxy-headers --port=80

api-dev:
	export PYTHONPATH=$PWD:$PWD/src
	fastapi dev api/__init__.py
