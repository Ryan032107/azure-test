from flask import Flask, render_template, request, redirect, url_for, jsonify, abort, make_response, g
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from urllib.parse import quote
import json
import os
import re
import time
import requests
import logging
from datetime import timedelta
from dotenv import load_dotenv
from backend.google_cloud_storage import GoogleCloudStorage
from backend.account_db import AccountManager  # 用於用戶登入管理
from backend.MongoDB_tools import MongoDBManager
from backend.doc2vec_processor import process_sheet, process_docx, create_document, process_and_save_all
from backend.db import DatabaseManager
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer

logging.basicConfig(level=logging.INFO)
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("ADMIN_SECRETKEY")  # 使用隨機生成的 secret_key

# 設置會話過期時間為2個小時
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=2)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.abspath('utility-encoder-420001-0db7ee074ec6.json')

# 初始化 Flask-Mail
mail = Mail(app)

# 設定 Flask-Mail 配置
app.config['MAIL_SERVER'] = os.getenv("MAIL_SERVER")
app.config['MAIL_PORT'] = int(os.getenv("MAIL_PORT"))
app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")
app.config['MAIL_USE_TLS'] = os.getenv("MAIL_USE_TLS") == 'True'
app.config['MAIL_USE_SSL'] = os.getenv("MAIL_USE_SSL") == 'True'

mail.init_app(app)

# 初始化序列化器
serializer = URLSafeTimedSerializer(app.secret_key)

BATCH_SIZE = 10  # 設定批次大小

def safe_filename(filename):
    """
    保留中文字符，并清理文件名中的潛在危險字符，允許空格。
    """
    safe_name = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fa5\s_.-]', '_', filename)
    return safe_name

def generate_token(email):
    return serializer.dumps(email, salt='email-confirm-salt')

def confirm_token(token, expiration=3600):
    try:
        email = serializer.loads(token, salt='email-confirm-salt', max_age=expiration)
    except:
        return False
    return email

def send_verification_email(user_email, token):
    try:
        # 建立驗證連結
        verification_url = url_for('verify_email', token=token, _external=True)

        # 設定郵件內容
        msg = Message('請驗證您的電子郵件', 
                      sender=os.getenv("MAIL_USERNAME"), 
                      recipients=[user_email])
        
        msg.body = f"請點擊以下連結驗證您的電子郵件：{verification_url}"
        msg.html = f"""
        <p>親愛的用戶，</p>
        <p>請點擊以下按鈕來驗證您的電子郵件：</p>
        <a href="{verification_url}"><button>驗證郵件</button></a>
        <p>如果您沒有請求此驗證，請忽略此郵件。</p>
        """

        # 發送郵件
        mail.send(msg)
        logging.info(f"成功發送驗證郵件至 {user_email}")
    except Exception as e:
        logging.error(f"發送驗證郵件失敗: {str(e)}")

def get_current_user_db():
    logging.info(f"get_current_user_db.current_user.is_authenticated:{current_user.is_authenticated}")
    if current_user.is_authenticated:
        db_manager = AccountManager()
        user_info = db_manager.get_user_info(current_user.id)
        db_name = user_info['database_name'] if user_info else None
        if db_name:
            # 在使用数据库前，确保数据库和表格已创建
            db = DatabaseManager(db_name)
            logging.info(f"useing_db_ame:{db_name}")
            db.setup_database_and_tables()
            return db_name  
    return None

@lru_cache(maxsize=32)
def cached_get_distinct_sources(mg, collection_name):
    return mg.get_distinct_sources(collection_name)

def process_file_in_parallel(new_file_name, mg, MongoDB_db, collection_name, id, db_name):
    try:
        content_type, file_data = GoogleCloudStorage("laoshifu", db_name).download_file(f"{id}/{new_file_name}")
        if "sheet" in content_type:
            logging.info(f"成功識別 {new_file_name}，開始萃取資料")
            data_list = process_sheet(file_data, new_file_name)
            logging.info(f"{new_file_name}識別完成。")
            is_sheet = True
        elif "pdf" in content_type:
            data_list = [process_and_save_all(file_data)]
            is_sheet = False
        elif "word" in content_type:
            data_list = [process_docx(file_data)]
            is_sheet = False
        else:
            return

        if not data_list:
            logging.info(f"萃取 {new_file_name}失敗，跳過文件 {new_file_name}")
            return

        vector_index = f"{collection_name.replace(' ', '_')}_vector_index"
        logging.info(f"開始新建 {new_file_name} 資料至 {collection_name}")

        for data in data_list:
            create_document(data, MongoDB_db[collection_name], vector_index, new_file_name, is_sheet=is_sheet)

        logging.info(f"新建成功 {new_file_name}")
    except Exception as e:
        logging.error(f"{new_file_name} 處理失敗：{e}")

def update_model_Handler():
    logging.info("模型開始更新！")
    db_name = get_current_user_db()

    db = DatabaseManager(db_name)
    df, need_update_df = db.get_collections_update_model()
    mongodb_info = db.get_mongodb_info_by_database_name(db_name)
    logging.info(f"mongodb_info: {mongodb_info}")

    # 使用 with 語句來確保 mg 正確定義
    with MongoDBManager(mongodb_info['MONGODB_URI'], mongodb_info['MONGODB_Public_Key'], mongodb_info['MONGODB_Private_Key'], mongodb_info['MONGODB_Group_ID'], mongodb_info['Cluster_Name'], db_name) as mg:
        MongoDB_db = mg.client[mg.db_name]
        logging.info("已取得 collections 資料表")
        logging.info("開始更新有被修改的 collections")

        for index, row in need_update_df.iterrows():
            id = row["id"]
            logging.info("檢查是否需要在 MongoDB 中建立新的 collection")
            if row["new_collection_name"]:
                logging.info(f"需要更新 collection, 將{row['collection_name']}更新為{row['new_collection_name']}")
                mg.update_collection(row["collection_name"], row["new_collection_name"])
                collection_name = row["new_collection_name"]
            else:
                logging.info("使用現有的 collection")
                collection_name = row["collection_name"]
                logging.info("檢查 vector_search_index 是否存在")
                mg.check_vector_search_index(collection_name)

            unique_sources = set(cached_get_distinct_sources(mg, collection_name))
            files = set(json.loads(row["files"]))
            new_files = set(json.loads(row["new_files"]))
            to_remove = (unique_sources - files) | (unique_sources & new_files)
            for file_name in to_remove:
                mg.delete_document(collection_name, file_name)

            with ThreadPoolExecutor(max_workers=5) as executor:  # 並行處理
                for batch_start in range(0, len(new_files), BATCH_SIZE):
                    batch_files = list(new_files)[batch_start:batch_start + BATCH_SIZE]
                    for new_file_name in batch_files:
                        executor.submit(process_file_in_parallel, new_file_name, mg, MongoDB_db, collection_name, id, db_name)

            logging.info(f"collection id: {id} 已更新完成")

    db.reset_update_status()
    logging.info("collections 資料表更新狀態已重置")
    logging.info(f"這是更新之前的 collection_name： {df['collection_name']}")

class User(UserMixin):
    def __init__(self, username):
        self.id = username

@login_manager.user_loader
def load_user(user_id):
    db_manager = AccountManager()
    user_info = db_manager.get_user_info(user_id)
    if user_info:
        return User(user_id)
    return None

@app.before_request
def before_request():
    g.username = current_user.id if current_user.is_authenticated else None

@app.context_processor
def inject_user():
    return dict(username=g.username)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        data = request.json
        username = data.get('username')
        password = data.get('password')
        db_manager = AccountManager()
        db_manager.check_and_create_tables()
        if db_manager.verify_user(username, password):
            user = User(username)
            login_user(user)
            # logging.info(f"login.current_user.is_authenticated:{current_user.is_authenticated}")
            return jsonify({"status": "success"}), 200
        return jsonify({"status": "failure"}), 401
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

#新增帳戶管理頁面路由
@app.route('/mail-management')
def mail_management():
    return render_template('mail_management.html')

@app.route('/password-management')
def password_management():
    return render_template('password_management.html')


@app.route('/')
@login_required
def index():
    db_name = get_current_user_db()
    db = DatabaseManager(db_name)
    collections = db.get_collections()
    return render_template('index.html', collections=collections)

@app.route('/roles')
@login_required
def roles():
    db_name = get_current_user_db()
    db = DatabaseManager(db_name)    
    user_permissions_info = db.get_user_permissions_info()
    user_permissions_keys = user_permissions_info[0].keys()
    user_info_mapping = dict(zip(user_permissions_keys, ["編號", "頭貼", "名稱", "基礎", "中階", "高階", "備註"]))
    return render_template('role_management.html', user_permissions_info=user_permissions_info, user_permissions_keys=user_permissions_keys, user_info_mapping=user_info_mapping)

@app.route('/admins')
@login_required
def admins():
    if current_user.id != 'admin':
        return redirect(url_for('index'))
    account_manager = AccountManager()
    admin_users_info = account_manager.get_users()
    admin_users_keys = admin_users_info[0].keys()
    return render_template('admin_management.html', admin_users_info=admin_users_info, admin_users_keys=admin_users_keys)

@app.route('/index_teaching')
@login_required
def index_teaching():
    return render_template('index_teaching.html')

@app.route('/role_teaching')
@login_required
def role_teaching():
    return render_template('role_teaching.html')

@app.route('/RAG_intro')
@login_required
def RAG_intro():
    return render_template('RAG_intro.html')


@app.route('/line_management')
@login_required
def line_page():
    account_manager = AccountManager()
    admin_users_info = account_manager.get_users(current_user.id)
    admin_users_keys = admin_users_info[0].keys()
    
    db_name = get_current_user_db()
    db = DatabaseManager(db_name)   
    users_info = db.get_users()
    user_count = len(users_info)
    return render_template('line_management.html', admin_users_info=admin_users_info, admin_users_keys=admin_users_keys, user_count=user_count)

@app.route('/tmp')
@login_required
def tmp():
    return render_template('tmp.html')

@app.route('/add_admin', methods=['POST'])
@login_required
def add_admin():
    username = request.form.get('username')
    password = request.form.get('password')
    user_database_name = request.form.get('database_name')
    database_line_id = request.form.get('database_line_id')
    limit_size = request.form.get('limit_size')

    account_manager = AccountManager()
    
    if account_manager.get_users(username):
        return jsonify({"status": "error", "message": "用戶名稱已經存在，請選擇其他用戶名稱"})
    else:
        account_manager.insert_user(username, password, user_database_name, database_line_id, limit_size)
        return jsonify({"status": "success", "message": "新增用戶成功！"})

@app.route('/delete_admin/<user_id>', methods=['POST'])
@login_required
def delete_admin(user_id):
    if user_id:
        account_manager = AccountManager()
        account_manager.delete_admin(user_id)  # Assume this returns True/False
        return jsonify({"status": "success", "message": "用戶刪除成功！"})
    return 'User deleted successfully'

@app.route('/delete_user/<user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if user_id:
        db_name = get_current_user_db()
        db = DatabaseManager(db_name)
        db.delete_user(user_id)  # Assume this returns True/False
        return jsonify({"status": "success", "message": "用戶刪除成功！"})
    return 'User deleted successfully'

@app.route('/settings', methods=['POST'])
def settings():
    db_name = get_current_user_db()
    db = DatabaseManager(db_name)
    collections = db.get_collections()
    collection_id = request.form.get('collection_id')
    new_collection_name = request.form.get('collection_name')
    new_prompt = request.form.get('prompt')
    db.update_collection(collection_id, collection_name=new_collection_name, prompt=new_prompt)
    collections = db.get_collections()
    return 'Settings updated', 200

@app.route('/upload/<collection_id>', methods=['POST'])
def upload_file(collection_id):
    db_name = get_current_user_db()
    db = DatabaseManager(db_name)
    gcs = GoogleCloudStorage('laoshifu', db_name)
    collections = db.get_collections()
    files = request.files.getlist('file')
    if not files:
        return 'No file part or no selected files', 400

    for item in collections:
        if item['id'] == int(collection_id):
            file_list = item["files"]
            new_file_list = item["new_files"]
            if not isinstance(file_list, list):
                file_list = []
            if not isinstance(new_file_list, list):
                new_file_list = []
            break

    for file in files:
        if file.filename == '':
            return 'No selected file', 400
        filename = safe_filename(file.filename)
        gcs.upload_file(file, filename, collection_id)
        if filename in file_list:
            file_list.remove(filename)
            new_file_list.remove(filename)
        file_list.append(filename)
        new_file_list.append(filename)
    db.update_collection(collection_id, files=json.dumps(file_list, ensure_ascii=False), new_files=json.dumps(new_file_list, ensure_ascii=False))
    collections = db.get_collections()
    return 'Files uploaded successfully'

@app.route('/delete/<collection_id>/<filename>', methods=['POST'])
def delete_file(collection_id, filename):
    db_name = get_current_user_db()
    db = DatabaseManager(db_name)
    gcs = GoogleCloudStorage('laoshifu', db_name)
    
    collections = db.get_collections()
    for item in collections:
        if item['id'] == int(collection_id):
            file_list = item["files"]
            file_list.remove(filename)
            new_file_list = item["new_files"]
            if filename in new_file_list:
                new_file_list.remove(filename)
            break
    gcs.delete_file(filename, collection_id)
    db.update_collection(collection_id, files=json.dumps(file_list, ensure_ascii=False), new_files=json.dumps(new_file_list, ensure_ascii=False))
    collections = db.get_collections()
    return 'File deleted successfully'
    
@app.route('/download/<collection_id>/<filename>', methods=['GET'])
def download_file(collection_id, filename):
    db_name = get_current_user_db()
    gcs = GoogleCloudStorage('laoshifu', db_name)
    try:
        blob_name = f"{collection_id}/{filename}"
        content_type, file_data = gcs.download_file(blob_name)

        # URL 編碼文件名
        encoded_filename = quote(filename)

        response = make_response(file_data)
        response.headers.set('Content-Type', content_type)
        response.headers.set('Content-Disposition', f"attachment; filename*=UTF-8''{encoded_filename}")
        return response
    except Exception as e:
        print(f"Error downloading file: {e}")
        return abort(404)    
     
@app.route('/api/update_model', methods=['POST'])
def update_model():
    db_name = get_current_user_db()
    logging.info(f"check db_name is {db_name}")
    # 預防 db_name 讀取失敗
    if db_name == None:
        return jsonify({"status": "error", "message": "登入帳號逾時，請重新登入。"}), 500
    db = DatabaseManager(db_name)
    subdomain = db.get_subdomain_by_database_name(db_name)
    db.update_model_status("pending")
    linebot_service_url = f'{subdomain}update_endpoint'
    try:
        db.update_model_status("updating")
        update_model_Handler()
        requests.post(linebot_service_url)
        update_status = db.get_model_status()[0]
    except requests.exceptions.RequestException as e:
        db.update_model_status("failed")
        update_status = db.get_model_status()[0]
        logging.info(f'Exceptions:{e}')
        return jsonify({"status": "error", "message": "出現意外了，更新失敗，請儘速通知管理員!"}), 500
    return jsonify({"status": "success", "message": "模型正在更新囉！"}), 200

# @app.route('/api/update_result', methods=['POST'])
# def update_result():
#     db_name = get_current_user_db()
#     logging.info(f"db_name:{db_name}")
#     db = DatabaseManager(db_name)
#     data = request.json
#     if data and 'status' in data:
#         if data.get('status') == "completed":
#             logging.info(f"update_result.update_model_status(completed) start")
#             db.update_model_status("completed")
#             logging.info(f"update_result.update_model_status(completed) finish")
#         else:
#             logging.info(f"update_result.update_model_status(failed) start")
#             db.update_model_status("failed")
#             logging.info(f"update_result.update_model_status(failed) finish")
#         update_status = db.get_model_status()[0]
#     collections = db.get_collections()
#     return jsonify(update_status), 200

@app.route('/api/get_update_result', methods=['GET'])
def get_update_result():
    db_name = get_current_user_db()
    db = DatabaseManager(db_name)
    update_status = db.get_model_status()[0]
    update_time = db.get_model_status()[1]
    if update_status == "completed" or update_status == "failed":
        db.update_model_status("pending")
    return jsonify({"update_status": update_status, "update_time": update_time}), 200

@app.route('/api/get_update_time', methods=['GET'])
def get_update_time():
    db_name = get_current_user_db()
    db = DatabaseManager(db_name)
    update_time = db.get_model_status()[1]  # 只获取更新时间
    logging.info(f"update_time:{update_time}")
    return jsonify({"update_time": update_time}), 200

@app.route('/api/update_user_permissions', methods=['POST'])
def update_user_permissions():
    db_name = get_current_user_db()
    db = DatabaseManager(db_name)
    data = request.form
    user_collection = data.get('name')
    user_id = user_collection.split('|')[-1]
    collection_id = user_collection.split('|')[-2]
    permission = data.get('checked')
    if permission == 'true':
        db.insert_user_permission(user_id, collection_id)
    else:
        db.delete_user_permission(user_id, collection_id)
    user_permissions_info = db.get_user_permissions_info()
    return jsonify({"status": "success"}), 200

@app.route('/save_note', methods=['POST'])
def update_user_note():
    db_name = get_current_user_db()
    db = DatabaseManager(db_name)
    data = request.json
    user_id = data.get('user_id')
    new_note = data.get('new_note')
    logging.info(f'user_id: {user_id}, new_note: {new_note}')
    db.update_user_note(user_id, new_note)
    db.get_user_permissions_info()
    return jsonify({"status": "success"}), 200

@app.route('/api/bucket_size', methods=['GET'])
def bucket_info():
    db_name = get_current_user_db()
    logging.info(f"--------------------bucket_info--------------------")
    logging.info(f"--------------------db_name:{db_name}--------------------")
    logging.info(f"--------------------bucket_info--------------------")
    gcs = GoogleCloudStorage('laoshifu', db_name)

    # 获取已使用的存储容量
    used_size = gcs.get_bucket_size(db_name)  # 假设返回值为 GB 数字

    # 从数据库获取当前用户的存储限制
    account_manager = AccountManager()
    user_info = account_manager.get_user_info(current_user.id)
    limit_size = user_info.get('limit_size', 2.0)  # 默认容量限制为 2.0 GB

    # 构造返回的 JSON 数据
    data = {
        "used_size": used_size,
        "limit_size": limit_size
    }
    logging.info(f"used_size:{used_size},limit_size: {limit_size}")
    return jsonify(data)

@app.route('/bind_account', methods=['POST'])
def bind_account():
    # 從前端請求中獲取用戶的 email
    data = request.json
    email = data.get('email')

    account_manager = AccountManager()
    
    # 檢查該 email 是否已被綁定
    if account_manager.is_email_bound(email):
        return jsonify({"status": "failure", "message": "該電子郵件已被其他帳號綁定。"}), 400

    # 生成驗證 token 並發送郵件
    token = generate_token(email)
    send_verification_email(email, token)
    
    return jsonify({"status": "success", "message": "綁定驗證郵件已寄送！"}), 200

@app.route('/verify_email/<token>')
def verify_email(token):
    try:
        # 使用 token 解碼取得 email
        email = confirm_token(token)
        if email:
            # 更新資料庫，將該 email 與當前用戶帳號綁定
            account_manager = AccountManager()
            account_manager.bind_user_email(current_user.id, email)
            return jsonify({"status": "success", "message": "帳號綁定成功！"}), 200
        else:
            return jsonify({"status": "failure", "message": "驗證連結無效或已過期。"}), 400
    except Exception as e:
        logging.error(f"驗證失敗: {str(e)}")
        return jsonify({"status": "failure", "message": "驗證過程出錯。"}), 500

if __name__ == '__main__':
    app.run()
    # 使用 Gunicorn，不需要 Flask 自帶的開發服務器
    # pass  # 這裡不再需要 `app.run()`，Gunicorn 會處理
