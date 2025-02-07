import os
import time
import json
import pandas as pd
import mysql.connector.pooling
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv()

class DatabaseManager:
    def __init__(self, database_name):
        self.database_name = database_name
        self.pool = self.create_connection_pool()

    def create_connection_pool(self):
        dbconfig = {
            "host": os.getenv('DB_HOST'),
            "user": os.getenv('DB_USER'),
            "password": os.getenv('DB_PASSWORD'),
            "database": self.database_name,
            "autocommit": True  # 自動提交
        }
        return mysql.connector.pooling.MySQLConnectionPool(
            pool_name="mypool",
            pool_size=10,  # 根據需要調整連接池大小
            **dbconfig
        )

    def get_connection(self):
        return self.pool.get_connection()

    @contextmanager
    def get_cursor(self):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            yield cursor
        finally:
            cursor.close()
            conn.close()

    def create_database_if_not_exists(self):
        """檢查數據庫是否存在，如果不存在則創建"""
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            autocommit=True
        )
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{self.database_name}`")
        cursor.close()
        conn.close()

    def reset_update_status(self):
        with self.get_cursor() as cursor:
            cursor.execute("""
                UPDATE collections 
                SET 
                    new_files = '[]', 
                    is_update = 0,
                    collection_name = CASE 
                        WHEN new_collection_name <> '' THEN new_collection_name 
                        ELSE collection_name 
                    END,
                    new_collection_name = ''
            """)

    def create_table_collections(self):
        """創建 collections 表並插入預設數據"""
        with self.get_cursor() as cursor:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS collections (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    collection_name VARCHAR(255) NOT NULL,
                    new_collection_name VARCHAR(255),
                    prompt TEXT,
                    files TEXT,
                    new_files TEXT,
                    is_update TINYINT(1) DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            ''')

            cursor.execute('SELECT COUNT(*) FROM collections')
            count = cursor.fetchone()[0]

            if count == 0:
                cursor.execute('''
                    INSERT INTO collections (collection_name, new_collection_name, prompt, files, new_files)
                    VALUES 
                    ('Group1', 'Group1', 'Group1 系統提示詞', '[]', '[]'),
                    ('Group2', 'Group2', 'Group2 系統提示詞', '[]', '[]'),
                    ('Group3', 'Group3', 'Group3 系統提示詞', '[]', '[]')
                ''')

    def create_table_user_permissions(self):
        """創建 user_permissions 表並初始化"""
        with self.get_cursor() as cursor:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_permissions (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    user_id INT NOT NULL,
                    collection_id INT NOT NULL,
                    is_permission TINYINT(1) DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            ''')

            cursor.execute('SELECT COUNT(*) FROM user_permissions')
            count = cursor.fetchone()[0]

            if count == 0:
                cursor.execute('''
                    INSERT INTO user_permissions (user_id, collection_id, is_permission)
                    VALUES 
                    (1, 1, 1)
                ''')

    def create_table_users(self):
        """創建 users 表並插入預設數據"""
        with self.get_cursor() as cursor:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    user_line_id VARCHAR(255) NOT NULL UNIQUE,
                    user_line_name VARCHAR(255) NOT NULL,
                    user_picture_url VARCHAR(255),
                    notes TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            ''')

            cursor.execute('SELECT COUNT(*) FROM users')
            count = cursor.fetchone()[0]

            if count == 0:
                cursor.execute('''
                    INSERT INTO users (user_line_id, user_line_name, user_picture_url)
                    VALUES 
                    ('testing_lineid', 'admin', 'https://upload.wikimedia.org/wikipedia/commons/a/ac/Default_pfp.jpg')
                ''')

    def create_server_info_table(self):
        """創建 server_info 表（如果尚未存在）"""
        with self.get_cursor() as cursor:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS server_info (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    database_name VARCHAR(255) NOT NULL,
                    MONGODB_URI TEXT NOT NULL,
                    MONGODB_Public_Key TEXT NOT NULL,
                    MONGODB_Private_Key TEXT NOT NULL,
                    MONGODB_Group_ID TEXT NOT NULL,
                    Cluster_Name VARCHAR(255) NOT NULL,
                    subdomain VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            ''')

    def get_mongodb_info_by_database_name(self, database_name):
        """根據 database_name 搜尋 server_info 並返回相關的 MongoDB 設定資訊"""
        with self.get_cursor() as cursor:
            cursor.execute('''
                SELECT 
                    MONGODB_URI, 
                    MONGODB_Public_Key, 
                    MONGODB_Private_Key, 
                    MONGODB_Group_ID, 
                    Cluster_Name
                FROM server_info 
                WHERE database_name = %s
            ''', (database_name,))

            result = cursor.fetchone()

        if result:
            keys = ['MONGODB_URI', 'MONGODB_Public_Key', 'MONGODB_Private_Key', 'MONGODB_Group_ID', 'Cluster_Name']
            return dict(zip(keys, result))
        else:
            return None

    def get_subdomain_by_database_name(self, database_name):
        """根據 database_name 搜尋 server_info 並返回 subdomain"""
        with self.get_cursor() as cursor:
            cursor.execute('''
                SELECT 
                    subdomain
                FROM server_info 
                WHERE database_name = %s
            ''', (database_name,))

            result = cursor.fetchone()

        if result:
            return result[0]  # 返回 subdomain 值
        else:
            return None

    def create_table_model_status(self):
        """創建 model_status 表並初始化"""
        with self.get_cursor() as cursor:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS model_status (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    status VARCHAR(255) NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            ''')

            cursor.execute('SELECT COUNT(*) FROM model_status')
            count = cursor.fetchone()[0]

            if count == 0:
                cursor.execute('''
                    INSERT INTO model_status (status)
                    VALUES ('pending')
                ''')

    def check_and_create_tables(self):
        """檢查並創建所有必要的表"""
        self.create_table_collections()
        self.create_table_user_permissions()
        self.create_table_users()
        self.create_table_model_status()
        self.create_server_info_table()

    def setup_database_and_tables(self):
        """設置數據庫和表格"""
        # 檢查數據庫是否存在，如果不存在則創建
        self.create_database_if_not_exists()
        # 檢查並創建所有表
        self.check_and_create_tables()

    def insert_collection(self, collection_name, prompt=None, files='[]', new_files='[]'):
        """插入新的集合記錄"""
        with self.get_cursor() as cursor:
            cursor.execute('''
                INSERT INTO collections (collection_name, prompt, files, new_files)
                VALUES (%s, %s, %s, %s)
            ''', (collection_name, prompt, files, new_files))

    def update_collection(self, id, collection_name=None, prompt=None, files=None, new_files=None):
        """更新集合記錄"""
        updates = {
            'new_collection_name': collection_name,
            'prompt': prompt,
            'files': files,
            'new_files': new_files
        }
        updates = {column: value for column, value in updates.items() if value is not None}
        if updates:
            set_clause = ', '.join([f"{column} = %s" for column in updates.keys()])
            parameters = list(updates.values())
            parameters.append(id)
            sql = f"UPDATE collections SET {set_clause}, is_update = 1, updated_at = CURRENT_TIMESTAMP WHERE id = %s"
            with self.get_cursor() as cursor:
                cursor.execute(sql, parameters)

    def delete_table_collections(self):
        """刪除 collections 表"""
        with self.get_cursor() as cursor:
            cursor.execute('''
                DROP TABLE IF EXISTS collections
            ''')

    def get_collections_update_model(self):
        """獲取需要更新模型的集合"""
        with self.get_connection() as conn:
            df = pd.read_sql_query("SELECT * FROM collections", conn)
            need_update_df = df[df['is_update'] == 1]
            return df, need_update_df

    def get_collections(self):
        """獲取所有集合記錄"""
        with self.get_cursor() as cursor:
            cursor.execute('''
                SELECT
                    id,
                    CASE
                        WHEN new_collection_name != '' THEN new_collection_name
                    ELSE collection_name
                    END AS collection_name,
                    prompt,
                    new_files,
                    files,
                    is_update
                FROM collections
            ''')
            rows = cursor.fetchall()
            column_names = [column[0] for column in cursor.description]
            dict_rows = [dict(zip(column_names, row)) for row in rows]

        for row in dict_rows:
            row['files'] = json.loads(row['files'])
            row['new_files'] = json.loads(row['new_files'])
        return dict_rows

    def get_users(self, user_line_id=None):
        """獲取所有用戶"""
        with self.get_cursor() as cursor:
            if user_line_id is None:
                cursor.execute('SELECT * FROM users')
                rows = cursor.fetchall()
                column_names = [column[0] for column in cursor.description]
                dict_rows = [dict(zip(column_names, row)) for row in rows]
                return dict_rows
            else:
                cursor.execute("SELECT * FROM users WHERE user_line_id = %s", (user_line_id,))
                rows = cursor.fetchall()
                if not rows:
                    return None
                return rows

    def update_model_status(self, status):
        """更新模型狀態"""
        with self.get_cursor() as cursor:
            cursor.execute('''
                UPDATE model_status
                SET status = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
            ''', (status,))

    def get_model_status(self):
        """獲取模型狀態"""
        retries = 3  # 重試次數
        for attempt in range(retries):
            try:
                with self.get_cursor() as cursor:
                    cursor.execute('''
                        SELECT status, updated_at
                        FROM model_status
                        WHERE id = 1
                    ''')
                    result = cursor.fetchone()
                    return result
            except mysql.connector.Error as err:
                print(f"Error: {err}")
                if attempt < retries - 1:
                    time.sleep(2)  # 等待一段時間後重試
                else:
                    raise  # 如果多次重試後仍然失敗，拋出異常

    def get_user_permissions_info(self):
        """獲取用戶權限信息"""
        with self.get_cursor() as cursor:
            cursor.execute("SELECT DISTINCT collection_name FROM collections")
            collection_names = [row[0] for row in cursor.fetchall()]
            columns = ", ".join([
                f"MAX(CASE WHEN c.collection_name = '{collection_name}' THEN up.is_permission ELSE 0 END) AS `{collection_name}`"
                for collection_name in collection_names
            ])
            query = f'''
            SELECT 
                u.id,
                u.user_picture_url,
                u.user_line_name,
                {columns},
                u.notes
            FROM 
                users u
            LEFT JOIN 
                user_permissions up ON u.id = up.user_id
            LEFT JOIN 
                collections c ON up.collection_id = c.id
            GROUP BY 
                u.id, u.user_line_name;
            '''
            cursor.execute(query)
            rows = cursor.fetchall()
            column_names = [column[0] for column in cursor.description]
            dict_rows = [dict(zip(column_names, row)) for row in rows]
            return dict_rows

    def transfer_name2id(self, collection_name):
        """根據集合名稱獲取集合ID"""
        with self.get_cursor() as cursor:
            cursor.execute("SELECT id FROM collections WHERE collection_name = %s", (collection_name,))
            result = cursor.fetchone()
        if result:
            return result[0]
        else:
            return None

    def insert_user_permission(self, user_id, collection_name):
        """插入用戶權限"""
        collection_id = self.transfer_name2id(collection_name)
        if collection_id:
            with self.get_cursor() as cursor:
                cursor.execute('''
                    INSERT INTO user_permissions (user_id, collection_id, is_permission)
                    VALUES (%s, %s, 1)
                ''', (user_id, collection_id))

    def delete_user_permission(self, user_id, collection_name):
        """刪除用戶權限"""
        collection_id = self.transfer_name2id(collection_name)
        if collection_id:
            with self.get_cursor() as cursor:
                cursor.execute('''
                    DELETE FROM user_permissions
                    WHERE user_id = %s AND collection_id = %s
                ''', (user_id, collection_id))

    def add_user(self, user_line_id, user_line_name):
        """插入新用戶"""
        with self.get_cursor() as cursor:
            cursor.execute('''
                INSERT INTO 
                    users (user_line_id, user_line_name)
                VALUES
                    (%s, %s)
            ''', (user_line_id, user_line_name))

    def add_default_permission(self, user_id):
        """添加默認權限"""
        with self.get_cursor() as cursor:
            cursor.execute('''
                INSERT INTO 
                    user_permissions (user_id, collection_id, is_permission)
                VALUES 
                    (%s, %s, 1)
            ''', (user_id, 1))

    def get_user_permission_collections(self, user_id):
        """獲取用戶權限的集合"""
        with self.get_cursor() as cursor:
            cursor.execute('''
                SELECT
                    c.collection_name
                FROM
                    users u
                LEFT JOIN 
                    user_permissions up ON u.id = up.user_id
                LEFT JOIN 
                    collections c ON up.collection_id = c.id
                WHERE
                    u.user_line_id = %s
            ''', (user_id,))

            collection_permission_name = [row[0] for row in cursor.fetchall()]
            return collection_permission_name

    def update_user_note(self, user_id, new_note):
        """更新用戶備註"""
        with self.get_cursor() as cursor:
            cursor.execute('''
                UPDATE users
                SET notes = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', (new_note, user_id))

    def delete_user(self, user_id):
        """刪除用戶"""
        with self.get_cursor() as cursor:
            cursor.execute('''
                DELETE FROM users WHERE id = %s
            ''', (user_id,))

            cursor.execute('''
                DELETE FROM user_permissions WHERE user_id = %s
            ''', (user_id,))