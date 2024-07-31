# News Data API

### Development

Start local api server (port 8000)
```
make api-dev
```

### Docs
Once the server is running you can access the docs at http://127.0.0.1:8000/docs#


### Test local request
Example request:
```sh
curl -X POST http://localhost:8000/api/articles_with_locale \
-H "Authorization: Bearer test" \
-H "Content-Type: application/json" \
-d '{"start_datetime":"2024-07-31 00:00:00", "locale": "en_US", "page":1, "page_size": 100}'
```
