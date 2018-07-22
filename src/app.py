from flask import (
    Flask, request, abort
)

import tempfile
import os
import sys

import datetime
import time

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError, LineBotApiError
)

from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    ImageMessage, VideoMessage, AudioMessage, StickerMessage,
    JoinEvent, SourceGroup, StickerSendMessage
)

from pymongo import (
    MongoClient
)

import json

app = Flask(__name__)

latest_image_path = ""

channel_secret = os.getenv('LINE_CHANNEL_SECRET', None)
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)
channel_admin = os.getenv('LINE_CHANNEL_ADMIN', None)
if channel_secret is None:
    print('Specify LINE_CHANNEL_SECRET as environment variable.')
    sys.exit(1)
if channel_access_token is None:
    print('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
    sys.exit(1)
if channel_admin is None:
    print('Specify LINE_CHANNEL_ADMIN as environment variable.')
    sys.exit(1)


host = os.getenv('MONGO_HOST', None)
port = os.getenv('MONGO_PORT', None)
username = os.getenv('MONGO_USER', None)
password = os.getenv('MONGO_PASSWORD', None)

if host is None:
    print('Specify MONGO_HOST as environment variable.')
    sys.exit(1)
if port is None:
    print('Specify MONGO_PORT as environment variable.')
    sys.exit(1)
if username is None:
    print('Specify MONGO_USER as environment variable.')
    sys.exit(1)
if password is None:
    print('Specify MONGO_PASSWORD as environment variable.')
    sys.exit(1)


line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)

static_tmp_path = os.path.join(os.path.dirname(__file__), 'static', 'tmp')

# function for create tmp dir for download content


def make_static_tmp_dir():
    try:
        os.makedirs(static_tmp_path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(static_tmp_path):
            pass
        else:
            raise


def save_message(event):
    client = MongoClient('mongodb://%s:%s@%s:%s' % (username, password, host, port))
    db = client.chatlog
    channels = db.channels

    message = event.message
    groupId = event.source.group_id
    print('Saving to group: ', groupId)
    group = channels[groupId]

    # LINE Event __str__ serialises itself to JSON string
    # We need to load it into a JSON (Dict) object for Mongo
    j = json.loads(str(event))
    print("event:", event)
    print("message:", message)
    id = group.insert_one(j).inserted_id
    return


@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        # print("Body:" + body)
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'


@handler.add(MessageEvent, message=StickerMessage)
def handle_sticker_message(event):
    # Handle webhook verification
    print("Sticker Message")
    if event.reply_token == 'ffffffffffffffffffffffffffffffff':
        return

    line_bot_api.reply_message(
        event.reply_token,
        StickerSendMessage(
            package_id=event.message.package_id,
            sticker_id=event.message.sticker_id
        )
    )


@handler.add(JoinEvent)
def handle_join(event):
    # group_id = event.source.group_id
    # line_bot_api.get_group_member_profile(group_id,member_id)
    # member_ids_res = line_bot_api.get_group_member_ids(group_id)
    # print(member_ids_res.member_ids)
    # print(member_ids_res.next)
    try:
        profile = line_bot_api.get_group_member_profile(
            event.source.group_id,
            channel_admin
        )
        line_bot_api.reply_message(
            event.reply_token,
            [
                TextSendMessage(text='สวัสดีค่า'),
                StickerSendMessage(
                    package_id=1,
                    sticker_id=2
                )
            ]
        )
    except LineBotApiError as e:
        print(e.status_code)
        print(e.error.message)
        print(e.error.details)
        line_bot_api.reply_message(
            event.reply_token,
            [
                TextSendMessage(text='หัวหน้าไม่อยู่ในห้องนี้\nไปละค่ะ\nบัย'),
            ]
        )
        line_bot_api.leave_group(event.source.group_id)


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    global latest_image_path

    if event.reply_token == "00000000000000000000000000000000":
        return "OK"

    save_message(event)

    uid = event.source.user_id

    if event.message.text == 'ออกไปได้แล้ว':
        if isinstance(event.source, SourceGroup):
            if event.source.user_id == channel_admin:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextMessage(text='บะบายค่า')
                )
                line_bot_api.leave_group(event.source.group_id)
            else:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextMessage(text='ไม่!')
                )

    else:
        return  # Keep quiet
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=event.message.text+'จ้า'))


@handler.add(MessageEvent, message=(ImageMessage, VideoMessage, AudioMessage))
def handle_content_message(event):
    global latest_image_path

    if isinstance(event.message, ImageMessage):
        ext = 'jpg'
    elif isinstance(event.message, VideoMessage):
        ext = 'mp4'
    elif isinstance(event.message, AudioMessage):
        ext = 'm4a'
    else:
        return

    message_content = line_bot_api.get_message_content(event.message.id)
    with tempfile.NamedTemporaryFile(dir=static_tmp_path, prefix=ext + '-', delete=False) as tf:
        for chunk in message_content.iter_content():
            tf.write(chunk)
        tempfile_path = tf.name

    dest_path = tempfile_path + '.' + ext
    dest_name = os.path.basename(dest_path)
    os.rename(tempfile_path, dest_path)

    uid = event.source.user_id
    if uid in reportingUsers:
        catalog = reportingUsers[uid]
        # TODO
        saveToFirebase(catalog, event)
        imageURL = saveImageToFirebase(catalog, dest_path)
        print('Saved image to firebase:', imageURL)
        return

    # Save image path
    latest_image_path = dest_path
    line_bot_api.reply_message(
        event.reply_token, [
            TextSendMessage(text='เก็บรูปให้แล้วค่ะ')
        ])


if __name__ == "__main__":
    app.run()
