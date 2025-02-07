import os
import json
import pandas as pd
import mysql.connector
from dotenv import load_dotenv
import logging

load_dotenv()

class SQLManager:
    def __init__(self):
        self.database_name = os.getenv('Database_Name')
        conn = self.get_connection()

    def get_connection(self):
        """創建與MySQL數據庫的連接，並在成功時回傳連接對象"""
        try:
            conn = mysql.connector.connect(
                host=os.getenv('DB_HOST'),
                user=os.getenv('DB_USER'),
                password=os.getenv('DB_PASSWORD'),
                database=self.database_name
            )
            logging.info("創建與MySQL數據庫的連接成功!")
            return conn
        except mysql.connector.Error as err:
            logging.error(f"無法連接到MySQL數據庫: {err}")
            return None

    # read "collections" table to all_rows, need_update_rows
    def get_init_setting(self):
        conn = self.get_connection()
        df = pd.read_sql_query("SELECT * FROM collections", conn)
        df["files"] = df['files'].apply(lambda x: json.loads(x))
        df["new_files"] = df['new_files'].apply(lambda x: json.loads(x))
        return df
    
    # read "collections" table to all_rows, need_update_rows
    def get_collections(self):
        conn = self.get_connection()
        df = pd.read_sql_query("SELECT * FROM collections", conn)
        need_update_df = df[df['is_update'] == 1]
        return df, need_update_df
    
    def get_model_status(self):
        """獲取模型狀態"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT status, updated_at
            FROM model_status
            WHERE id = 1
        ''')
        result = cursor.fetchone()
        return result
    
    def reset_udpate_status(self):
        conn = self.get_connection()
        cursor = conn.cursor()
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
        conn.commit()
        conn.close()

    def insert_or_update_server_info_record(self, database_name, mongodb_uri, mongodb_public_key, mongodb_private_key, mongodb_group_id, cluster_name, subdomain):
        """插入新記錄到 server_info 表，如果存在相同的 database_name 則更新記錄"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # 檢查是否已經存在相同的 database_name
        cursor.execute('''
            SELECT COUNT(*) FROM server_info WHERE database_name = %s
        ''', (database_name,))
        count = cursor.fetchone()[0]

        if count > 0:
            # 如果存在，更新記錄
            cursor.execute('''
                UPDATE server_info
                SET MONGODB_URI = %s,
                    MONGODB_Public_Key = %s,
                    MONGODB_Private_Key = %s,
                    MONGODB_Group_ID = %s,
                    Cluster_Name = %s,
                    subdomain = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE database_name = %s
            ''', (mongodb_uri, mongodb_public_key, mongodb_private_key, mongodb_group_id, cluster_name, subdomain, database_name))
        else:
            # 如果不存在，插入新記錄
            cursor.execute('''
                INSERT INTO server_info (database_name, MONGODB_URI, MONGODB_Public_Key, MONGODB_Private_Key, MONGODB_Group_ID, Cluster_Name, subdomain)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (database_name, mongodb_uri, mongodb_public_key, mongodb_private_key, mongodb_group_id, cluster_name, subdomain))
        logging.info("初始化資料mongodb資料傳輸成功!")
        conn.commit()
        conn.close()

    # add default permissions to the new user in the "user_permissions" table
    def add_default_permission(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO 
            user_permissions (user_id, collection_id, is_permission)
        VALUES 
            (%s, %s, 1)
        ''', (user_id, 1))
        conn.commit()
        conn.close()

    def get_user_permission_collections(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
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
        conn.commit()
        conn.close()
        return collection_permission_name
    
    def get_users(self, user_line_id=None):
        """獲取用戶"""
        conn = self.get_connection()
        cursor = conn.cursor()
        # 獲取所有用戶
        if user_line_id is None:
            cursor.execute('SELECT * FROM users')
        # 獲取特定用戶   
        else:
            cursor.execute("SELECT * FROM users WHERE user_line_id = %s", (user_line_id,))
        rows = cursor.fetchall()
        conn.close()
        column_names = [column[0] for column in cursor.description]
        dict_rows = [dict(zip(column_names, row)) for row in rows]
        if not dict_rows:
            return None
        return dict_rows
        
    def add_user(self, user_line_id, user_line_name, user_picture_url):
        """插入新用户"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO 
            users (user_line_id, user_line_name, user_picture_url)
        VALUES
            (%s, %s, %s)
        ''', (user_line_id, user_line_name, user_picture_url))
        conn.commit()
        conn.close()

    def update_model_status(self, status):
        """更新模型狀態"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE model_status
            SET status = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = 1
        ''', (status,))
        conn.commit()
        conn.close()

    def update_user_line_name(self, user_line_id, user_line_name):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users
            SET user_line_name = %s, updated_at = CURRENT_TIMESTAMP
            WHERE user_line_id = %s
        ''', (user_line_name, user_line_id))
        conn.commit()
        conn.close()

    def update_user_picture_url(self, user_line_id, user_picture_url):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users
            SET user_picture_url = %s, updated_at = CURRENT_TIMESTAMP
            WHERE user_line_id = %s
        ''', (user_picture_url, user_line_id))
        conn.commit()
        conn.close()