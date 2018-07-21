from flask import Flask, request, abort

import tempfile
import os
import sys

import datetime, time
from intent import Intent
# import intent.Intent

from intent.Intent import (
    StartReportIntent, EndReportIntent, 
    ListReportIntent, ViewReportIntent,
    DefaultIntent
)

from features.firebase import (
    Report
)

from features.CarAnalytics import LicencePlate

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError,LineBotApiError
)

#from mytest.intent.Registration import(
#     Registration
#)


from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    ImageMessage, VideoMessage, AudioMessage, StickerMessage, 
    JoinEvent,SourceGroup,StickerSendMessage
)

import json

import oil_price

app = Flask(__name__)

latest_image_path = ""

# State controller
reportingUsers = {}
reportList = []

channel_secret = os.getenv('LINE_CHANNEL_SECRET', None)
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)
if channel_secret is None:
    print('Specify LINE_CHANNEL_SECRET as environment variable.')
    sys.exit(1)
if channel_access_token is None:
    print('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
    sys.exit(1)

line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)

conversation = {}

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


@app.route("/", methods=['GET'])
def default_action():
    l = oil_price.get_prices()
    s = ""
    for p in l:
        s += "%s %f บาท\n"%(p[0],p[1])
    return s
    
def saveToFirebase(event):
    ref = db.reference('/report')
    ref.push(json.loads(event.as_json_string()))

def saveFirebase(event,uid):
    ref = db.reference('/registration-'+uid)
    ref.push(json.loads(event.as_json_string()))

def saveToFirebase(catalog,event):
    ref = db.reference(catalog)
    ref.push(json.loads(event.as_json_string()))

def saveImageToFirebase(catalog,source_filename):
    bucket = storage.bucket()
    blob = bucket.blob("%s/%s"%(catalog,source_filename))
    blob.upload_from_filename(source_filename)
    return blob.public_url

@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        print("Body:"+ body)
        #save messege body to firebase
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
            'U991007deaa6c52bd776443e7d89f2032'
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
    global reportList
    

    if event.reply_token == "00000000000000000000000000000000":
        return "OK"

    # saveToFirebase(event)
    #resume exiting 
    print(conversation.keys())
    uid = event.source.user_id
    if uid in conversation:
        intent = conversation[uid]
        o = intent.handle(event.message.text)
        line_bot_api.reply_message(
              event.reply_token,
              [
                  TextSendMessage(text=o)
              ]
         )
        if intent.endIntent():
            output = intent.getData()
            print(output)
            saveFirebase(output,event.source.user_id)
            del conversation[uid]
        return

    userIntent = Intent.evaluateIntent(event.message.text)
    if uid in reportingUsers:
        if isinstance(userIntent, EndReportIntent):
            profile = line_bot_api.get_profile(uid)
            del reportingUsers[uid]
            line_bot_api.reply_message(
                event.reply_token,
                [
                    TextSendMessage(text='บันทึกเสร็จสิ้นค่ะ คุณ%s'%profile.display_name)
                ]
            )
            return
        catalog = reportingUsers[uid]
        saveToFirebase(catalog,event)
        print('Saving to firebase')
        return

    if isinstance(userIntent, StartReportIntent):
        profile = line_bot_api.get_profile(uid)
        dateStr = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        reportingUsers[uid] = "report-%s-%s"%(uid,dateStr)
        line_bot_api.reply_message(
            event.reply_token,
            [
                TextSendMessage(text='กำลังจดบันทึกให้ค่ะ คุณ%s'%profile.display_name)
            ]
        )
        return

        # rego = None

        if uid in conversation:
            rego = conversation[uid]
        else:        
            rego = keepdata()
            conversation[uid] = rego
            o = rego.handle(event.message.text)
            line_bot_api.reply_message(
                event.reply_token,
                [
                    TextSendMessage(text=o)
                ]
            )

    if isinstance(userIntent, ViewReportIntent):        
        id = int(userIntent.id)
        print('id:',id)
        (uid,dateStr) = reportList[id-1]
        d,t = dateStr.split()
        (ye,mo,da) = d.split('-')
        (h,m,s) = t.split(':')
        key = 'report-%s-%s-%s-%s-%s-%s-%s'%(uid,ye,mo,da,h,m,s)
        print('Key:',key)
        report = Report.viewReport(key)
        line_bot_api.reply_message(
            event.reply_token,
            [
                TextSendMessage(text=report)
            ]
        )
        return

    if isinstance(userIntent,ListReportIntent):
        reportList = Report.listReports()
        s = 'รายงานทั้งหมด\n'
        i = 1
        for r in reportList:
            (uid,dateStr) = r
            profile = line_bot_api.get_profile(uid)
            s += "%d: %s (%s)\n" % (i,profile.display_name,dateStr)
            i += 1

        line_bot_api.reply_message(
            event.reply_token,
            [
                TextSendMessage(text=s)
            ]
        )
        return

    if event.message.text == 'ออกไปได้แล้ว':
       if isinstance(event.source,SourceGroup):
           if event.source.user_id == 'U991007deaa6c52bd776443e7d89f2032':
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

    if event.message.text == 'ราคาน้ำมัน':
        l = oil_price.get_prices()
        s = ""
        for p in l:
            s += "%s %.2f บาท\n"%(p[0],p[1])

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=s))
    elif event.message.text == 'วิเคราะห์รูป':
        line_bot_api.reply_message(
            event.reply_token, [
                TextSendMessage(text='สักครู่ค่ะ')
            ])

        # Process image
        try:
            lp = LicencePlate()
            result = lp.process(latest_image_path)
            s = lp.translate(result)

            line_bot_api.push_message(
                     event.source.user_id, [
                           TextSendMessage(text = s)
                    ])

        except Exception as e:
            print('Exception:',type(e),e) 
            line_bot_api.push_message(
                 event.source.user_id,[
                     TextSendMessage(text='ไม่สามารถวิเคราะห์รูปได้')
                ])
            
    else:
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
        saveToFirebase(catalog,event)
        imageURL = saveImageToFirebase(catalog,dest_path)
        print('Saved image to firebase:',imageURL)
        return

    # Save image path
    latest_image_path = dest_path
    line_bot_api.reply_message(
        event.reply_token, [
            TextSendMessage(text='เก็บรูปให้แล้วค่ะ')
        ])


if __name__ == "__main__":
    app.run()
