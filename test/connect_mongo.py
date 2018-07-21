import os
from pymongo import (
    MongoClient
)

host = os.getenv('MONGO_HOST', None)
port = os.getenv('MONGO_PORT', None)
username = os.getenv('MONGO_USER', None)
password = os.getenv('MONGO_PASSWORD', None)

client = MongoClient('mongodb://%s:%s@%s:%s' % (username, password, host, port))
db = client.chatlog
channels = db.channels
group1 = channels.group1
msg = {
    'user_id': '047908123921',
    'message': 'text',
    'text': 'Hello World'
}
id = group1.insert_one(msg).inserted_id
print(id)
