import os
import json
import requests
import logging
from flask import Flask, request, abort, jsonify
from update_chatbot import SqliteManager, update_chatbot
from dotenv import load_dotenv
import time  # instead of import sleep
load_dotenv()

app = Flask(__name__)


@app.route('/update_endpoint', methods=['POST'])
def update_endpoint():
    print("收到更新請求囉～")
    # result = update_chatbot()
    time.sleep(5)  # instead of sleep(5)
    result = {"status": "completed", "message": "成功更新了！"}
    # 向 admin 回傳更新結果
    admin_service_url = 'http://127.0.0.1:5001/api/update_result'
    try:
        requests.post(admin_service_url, json=result)
    except requests.exceptions.RequestException as e:
        # 如果請求失敗，返回一個包含錯誤信息的 JSON 對象
        return jsonify({"status": "error", "message": "出現意外了，後台沒有收到消息"}), 500
    # 如果請求成功，返回一個成功信息的 JSON 對象
    return jsonify({"status": "success", "message": "已通知後台使用者囉"}), 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=6000, debug=True)
