SET MONGO_HOST=localhost
SET MONGO_PORT=27017
SET MONGO_USER=root
SET MONGO_PASSWORD=example

SET LINE_CHANNEL_ACCESS_TOKEN=xxxxxxxxxxxxxxxx
SET LINE_CHANNEL_SECRET=xxxxxxxxxxxxxxxx
SET LINE_CHANNEL_ADMIN=xxxxxxxxxxxxxxxx

cd src
SET FLASK_APP=app.py
SET FLASK_ENV=development
flask run --host=0.0.0.0