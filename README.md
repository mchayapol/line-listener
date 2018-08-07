# LINE BOT Listener
A LINE Bot which saves all messages into a Mongo DB.  
This is a Flask app based on LINE BOT SDK Kitchen sink.

# Start Docker
```shell
docker-compose -f mongo-express-stack.yml up
```

# Run
```shell
export FLASK_APP=app.py
export FLASK_DEBUG=1
flask run --host=0.0.0.0
```

# Register LINE Webhook
1. Go to https://developers.line.me
2. Grab Channel Access Token and Channel Secret
3. Set webhook

# Enable Google Drive Support

```shell
pip install --upgrade google-api-python-client
```

[Get credentials.json](https://developers.google.com/drive/api/v3/quickstart/python)