import os
import json
import base64
import requests
import logging
from flask import Flask, request, abort, jsonify
from linebot.v3 import WebhookHandler
from linebot import LineBotApi
from linebot.models import TextSendMessage, QuickReply, QuickReplyButton, MessageAction, AudioSendMessage
from chat_record import Chat_Record_Manager
from audio_recognize import TTS_Transcription
from file_recognize import FileReader
from chat_logic_main import ChatLogic
from update_chatbot import update_chatbot
from db import SQLManager
from dotenv import load_dotenv
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler

load_dotenv()

app = Flask(__name__)

class LineBotApp:
    def __init__(self):
        self.access_token = os.getenv('ACCESS_TOKEN')
        self.secret = os.getenv('SECRET')
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.subdomain = os.getenv('SUBDOMAIN')

        self.sql_manager = SQLManager()
        self.line_bot_api = LineBotApi(self.access_token)
        self.handler = WebhookHandler(self.secret)
        self.record_manager = Chat_Record_Manager()
        self.audio_processor = TTS_Transcription()
        self.file_reader = FileReader()
        self.chat = ChatLogic()
        self.setting = SQLManager().get_init_setting()

        self.user_chat_histories = {}
        self.chat.create_prompt_template(self.setting)
        self.sql_manager.insert_or_update_server_info_record(os.getenv('Database_Name'), os.getenv('MONGODB_URI'), os.getenv('MONGODB_Public_Key'), os.getenv('MONGODB_Private_Key'), os.getenv('MONGODB_Group_ID'), os.getenv('Cluster_Name'), os.getenv('SUBDOMAIN'))

        self.scheduler = BackgroundScheduler()
        self.schedule_daily_tasks()

        self.allowed_extensions = {'.pdf', '.docx', '.txt', '.html', '.csv', '.pptx'}
        self.max_file_size = 10000000

    def schedule_daily_tasks(self):
        # 每天午夜执行 create_tools
        # self.scheduler.add_job(self.chat.create_prompt_template, 'cron', hour=0)
        # self.scheduler.start()
        print("老師傅開發中，暫停使用")

    def display_loading_animation(self, chat_id, loading_seconds=10):
        url = "https://api.line.me/v2/bot/chat/loading/start"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.access_token}'
        }
        payload = {
            "chatId": chat_id,
            "loadingSeconds": loading_seconds
        }
        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            if response.status_code == 200:
                logging.info("Loading animation started successfully")
            else:
                logging.error(f"Failed to start loading animation: {response.status_code} - {response.text}")
        except requests.RequestException as e:
            logging.error(f"Exception during loading animation request: {e}")

    def generate_questions(self, msg_type, group_type):
        str_questions_list = os.getenv('QUICK_QUESTION')
        questions_list = eval(str_questions_list)
        
        if group_type in ["group", "room"]:
            questions_list.insert(1, "關閉群組功能")
        return questions_list

    def switch_model_tool(self, user_information, user_line_id, tk, GPT_4o_Limit):
        current_model = user_information['model_version']
        usage_count = user_information['GTP 4o frequency of use']

        if current_model == 4:
            self.record_manager.switch_model(user_line_id, 3)
            reply = '已切換成GPT 3.5 turbo'
        elif current_model == 3 and usage_count < GPT_4o_Limit:
            self.record_manager.switch_model(user_line_id, 4)
            reply = '已切換成GPT 4o'
        else:
            reply = 'GPT 4o 次數已達上限'

        return reply
    
    def find_image_path(self, user_line_id):
        # 設定儲存圖片的資料夾路徑
        folder_path = 'image_buffer'
        os.makedirs(folder_path, exist_ok=True)
        return os.path.join(folder_path, f'{user_line_id}.jpg')

    def get_user_profile(self, user_line_id):
        url = f"https://api.line.me/v2/bot/profile/{user_line_id}"
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to get user profile: {response.status_code}")

    def linebot(self):
        body = request.get_data(as_text=True)
        try:
            json_data = json.loads(body)
            signature = request.headers['X-Line-Signature']
            self.handler.handle(body, signature)
            tk = json_data['events'][0]['replyToken']
            msg_type = json_data['events'][0]['message']['type']
            source_type = json_data['events'][0]['source']['type']
            user_line_id = json_data['events'][0]['source']['userId']
            profile = self.get_user_profile(user_line_id)
            user_line_name = profile.get("displayName")
            user_picture_url = profile.get("pictureUrl")
            if user_picture_url is None:
                user_picture_url = 'https://upload.wikimedia.org/wikipedia/commons/a/ac/Default_pfp.jpg'
            
            user_info = self.sql_manager.get_users(user_line_id)
            logging.info(f"line infoooo: {user_info}")
            # 新增並帶有 defualt 權限 arg: user_line_id, user_line_name, user_picture_url
            if not user_info: # first access (not exist in users table)
                # 新增此 user
                self.sql_manager.add_user(user_line_id, user_line_name, user_picture_url)
                logging.info(f"line info: {user_line_id}, {user_line_name}, {user_picture_url}")
                # 給予default權限
                logging.info(f"line id: {self.sql_manager.get_users(user_line_id)[0]['id']}")
                self.sql_manager.add_default_permission(self.sql_manager.get_users(user_line_id)[0]['id'])
            
            # 判斷是否為已訪問過用戶
            if user_info: # exist in users table
                db_user_line_name = user_info[0]['user_line_name']
                db_user_picture_url = user_info[0]['user_picture_url']
                logging.info(f"db_user_line_name: {db_user_line_name} db_user_picture_url {db_user_picture_url}")
                logging.info(f"user_line_name: {user_line_name} user_picture_url {user_picture_url}")
                # 檢查 user_line_name 是否更新
                if user_line_name != db_user_line_name:
                    self.sql_manager.update_user_line_name(user_line_id, user_line_name)
                # 檢查 user_picture_url 是否更新
                if user_picture_url != db_user_picture_url:
                    self.sql_manager.update_user_picture_url(user_line_id, user_picture_url)

            # 群組開啟關閉功能
            if source_type in ["group", "room"]:
                group_or_room_id = json_data['events'][0]['source']['groupId'] if source_type == "group" else json_data['events'][0]['source']['roomId']
                group_or_room_info = self.record_manager.get_or_create_group_info(source_type, group_or_room_id)
                if not group_or_room_info["enable status"]:
                    if msg_type == 'text':
                        msg = str(json_data['events'][0]['message']['text'])   
                        if msg == '開啟群組功能':
                            self.record_manager.switch_group_enable_status(group_or_room_id, True)
                            reply = '群組功能已開啟'
                            
                            # 生成快速回復按鈕
                            questions = self.generate_questions(msg_type, source_type)
                            quick_reply_items = [QuickReplyButton(action=MessageAction(label=question, text=question)) for question in questions]
                            quick_reply = QuickReply(items=quick_reply_items)
                            
                            # 創建包含快速回復按鈕的消息
                            reply_message = TextSendMessage(text=reply, quick_reply=quick_reply)
                            self.line_bot_api.reply_message(tk, reply_message)
                        
                    return 'OK'
                elif msg_type == 'text':
                    msg = str(json_data['events'][0]['message']['text'])   
                    if msg == '關閉群組功能':
                        self.record_manager.switch_group_enable_status(group_or_room_id, False)
                        reply = '群組功能已關閉，輸入[開啟群組功能]就能再次啟用!'
                        # Create a message with quick reply buttons
                        reply_message = TextSendMessage(text=reply)

                        self.line_bot_api.reply_message(tk, reply_message)
                        return 'OK'

            # 顯示載入動畫
            self.display_loading_animation(user_line_id)

            user_information = self.record_manager.get_or_create_user_usage(user_line_id)

            print(f"user_information:{user_information}\n")
            System_Limit = 100
            GPT_4o_Limit = 100
            
            if user_information['All frequency of use'] > System_Limit:
                reply = '今天的使用次數已到上限了呦～歡迎明天再來!'
                self.line_bot_api.reply_message(tk, TextSendMessage(reply))
            else:
                ############### text ################
                if msg_type == 'text': 

                    msg = str(json_data['events'][0]['message']['text'])   
                    if msg == "使用教學":
                        reply = """★ 使用教學

➔ 詢問問題：你可以使用文字、照片或語音向我提問，我會根據資料庫中的內容盡力回答你的問題。
➔ 刪除聊天歷史：如果發現我的回答經常出錯或重複，可以點擊[刪除聊天歷史]，清除過去的聊天記錄，重新開始。
➔ 上傳照片：當你上傳照片後，我的回答將以這張照片為核心。如果想恢復到文字對答，可以點擊[刪除上傳的照片]。
"""
                    elif msg == "刪除聊天歷史":
                        if self.record_manager.delete_user_chat_history(user_line_id):
                            reply = f"聊天歷史刪除成功!"
                        else:
                            reply = f"聊天歷史刪除失敗，請重新嘗試!"
                            
                    elif msg == "刪除上傳的照片":
                        file_path = self.find_image_path(user_line_id)
                        if os.path.exists(file_path):
                            os.remove(file_path)
                            reply = "照片已刪除"
                        else:
                            reply = "目前沒有上傳的照片喔 ~"

                    # elif msg == "切換模型":
                    #     reply = self.switch_model_tool(user_information, user_line_id, tk, GPT_4o_Limit)

                    # elif msg == "當前用量":
                    #     reply = f"今天 GPT 4o 使用量為 {user_information['GTP 4o frequency of use']} 次，總使用數量為 {user_information['All frequency of use']} 次。"                   
                    
                    else:
                        if user_information['model_version'] == 4 and user_information['GTP 4o frequency of use'] > GPT_4o_Limit:
                            self.record_manager.switch_model(user_line_id, 3)
                            user_information['model_version'] = 3
                        # 設定儲存圖片的資料夾路徑
                        file_path = self.find_image_path(user_line_id)
                        
                        self.record_manager.add_chat_record(user_line_id, "user", msg, user_information)
                        if os.path.exists(file_path):
                            # 獲取文件的修改時間
                            file_mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                            current_time = datetime.now()
                            time_diff = current_time - file_mod_time
                            
                            # 如果文件超過3分鐘，則刪除
                            if time_diff > timedelta(minutes=3):
                                os.remove(file_path)
                                reply = str(self.chat.execute_chat(user_line_id, msg, user_information['chat_history'], user_information['model_version']))
                            else:
                                with open(file_path, "rb") as image_file:
                                    base64_image = base64.b64encode(image_file.read()).decode('utf-8')
                                reply = str(self.chat.execute_chat(user_line_id, msg, user_information['chat_history'], user_information['model_version'], base64_image))
                        else:
                            reply = str(self.chat.execute_chat(user_line_id, msg, user_information['chat_history'], user_information['model_version']))
                        self.record_manager.add_chat_record(user_line_id, "assistant", reply, user_information)
                elif msg_type == 'audio':
                    # 解讀並儲存音檔
                    message_content = self.line_bot_api.get_message_content(json_data['events'][0]['message']['id'])
                    folder_path = 'audio_buffer'
                    os.makedirs(folder_path, exist_ok=True)
                    m4a_file_path = os.path.join(folder_path, f'{user_line_id}.m4a')
                    reply_wav_file_path = os.path.join(folder_path, f'reply_{user_line_id}.wav')
                    with open(m4a_file_path, 'wb') as fd:
                        for chunk in message_content.iter_content():
                            fd.write(chunk)
                    # 將用戶的音檔轉為文字
                    text = self.audio_processor.transcribe_audio(os.path.abspath(m4a_file_path))
                    # 保存用戶對話紀錄
                    self.record_manager.add_chat_record(user_line_id, "user", text, user_information)
                    
                    # 使用LLM模型回復
                    gpt_reply = str(self.chat.execute_chat(user_line_id, text, user_information['chat_history'], user_information['model_version']))
                    # 保存模型回復紀錄
                    self.record_manager.add_chat_record(user_line_id, "assistant", gpt_reply, user_information)
                    # 將模型回復轉換成語音
                    self.audio_processor.text_to_speech(gpt_reply, reply_wav_file_path)
                    # 宣告url
                    url = f'{self.subdomain}/files/reply_{user_line_id}.wav'
                    # 宣告回復參數
                    reply_message = AudioSendMessage(original_content_url=url, duration=2000)

                    self.line_bot_api.reply_message(tk, reply_message)

                    return 'OK'                    

                ############### image ################
                elif msg_type == 'image':
                    if user_information['model_version'] == 4 and user_information['GTP 4o frequency of use'] < GPT_4o_Limit:
                        # 根據訊息 ID 取得訊息內容
                        message_content = self.line_bot_api.get_message_content(json_data['events'][0]['message']['id'])  
                        # 設定要儲存圖片的資料夾路徑
                        file_path = self.find_image_path(user_line_id)
                        with open(file_path, 'wb') as fd:
                            fd.write(message_content.content)

                        with open(file_path, "rb") as image_file:
                            base64_image = base64.b64encode(image_file.read()).decode('utf-8')

                        msg = "告訴我照片中的內容。"

                        self.record_manager.add_chat_record(user_line_id, "user", msg, user_information)
                        reply = str(self.chat.execute_chat(user_line_id, msg, user_information['chat_history'], user_information['model_version'], base64_image))
                        self.record_manager.add_chat_record(user_line_id, "assistant", reply, user_information)
                    else:
                        reply = "GPT4o模型才能做圖片辨識喔～"
                ############### file ################
                elif msg_type == 'file':
                    # 獲取事件中的文件信息
                    file_info = json_data['events'][0]['message']
                    file_size = file_info['fileSize']
                    file_name = file_info['fileName']
                    file_extension = os.path.splitext(file_name)[1].lower()
                    
                    # 根據文件大小和格式進行檢查
                    if file_size > self.max_file_size:
                        reply = f'檔案:{file_name}太大了，目前只能讀取10MB以下的檔案～'
                    elif file_extension not in self.allowed_extensions:
                        reply = f'檔案:{file_name}格式不支持，目前僅支持 pdf、docx、txt、html、csv'
                    else:
                        # 根據訊息 ID 取得訊息內容
                        message_content = self.line_bot_api.get_message_content(file_info['id'])
                        user_line_id = json_data['events'][0]['source']['userId']
                        folder_path = 'file_buffer'
                        os.makedirs(folder_path, exist_ok=True)
                        
                        # 在指定的資料夾中建立以 user_line_id 為檔名的文件
                        file_path = os.path.join(folder_path, f'{user_line_id}{file_extension}')
                        with open(file_path, 'wb') as fd:
                            fd.write(message_content.content)
                        # 執行文本讀取以及聊天邏輯
                        file_txt = "摘要以下文本:\n" + str(self.file_reader.read_file(file_path))
                        self.record_manager.add_chat_record(user_line_id, "user", file_txt, user_information)
                        reply = str(self.chat.execute_chat(user_line_id, file_txt, user_information['chat_history'], user_information['model_version']))
                        self.record_manager.add_chat_record(user_line_id, "assistant", reply, user_information)
                        # 刪除文件
                        if os.path.exists(file_path):
                            os.remove(file_path)
                else:
                    reply = '目前只接受文字、圖片、音檔、文字檔案呦～'

                # Generate quick reply buttons
                questions = self.generate_questions(msg_type, source_type)
                quick_reply_items = [QuickReplyButton(action=MessageAction(label=question, text=question)) for question in questions]
                quick_reply = QuickReply(items=quick_reply_items)
                
                # Create a message with quick reply buttons
                
                reply_message = TextSendMessage(text=reply, quick_reply=quick_reply)

                self.line_bot_api.reply_message(tk, reply_message)
                
                logging.info(f'Reply: {reply}')
        except Exception as e:
            logging.error(f"Exception: {e}")
            logging.error(f"Request body: {body}")
        return 'OK'

line_bot_app = LineBotApp()

@app.route("/", methods=['POST'])
def webhook():
    return line_bot_app.linebot()

@app.route('/update_endpoint', methods=['POST'])
def update_endpoint():
    print("收到更新請求囉～")
    global line_bot_app
    line_bot_app = LineBotApp()
    
    try:
        result = update_chatbot()
        line_bot_app.sql_manager.update_model_status("completed")
        model_status = line_bot_app.sql_manager.get_model_status()
        logging.info(f"model_status:{model_status}")
        if model_status != "completed":
            line_bot_app.sql_manager.update_model_status("completed")
            model_status = line_bot_app.sql_manager.get_model_status()
            logging.info(f"model_status:{model_status}")
    except Exception as e:
        logging.info(f"Exception:{e}")
        # 如果請求失敗，返回一個包含錯誤信息的 JSON 對象
        line_bot_app.sql_manager.update_model_status("failed") 
        return jsonify({"status": "error", "message": "出現意外了，後台沒有收到消息"}), 500
    # 如果請求成功，返回一個成功信息的 JSON 對象
    return jsonify({"status": "success", "message": "已通知後台使用者囉"}), 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)