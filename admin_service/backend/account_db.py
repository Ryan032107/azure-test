import os
import bcrypt
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

class AccountManager:
    def __init__(self):
        self.account = "account"
        self.conn = self.get_connection()

    def get_connection(self):
        """創建與MySQL數據庫的連接"""
        return mysql.connector.connect(
            host=os.getenv('DB_HOST'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=self.account
        )

    def create_table_users(self):
        """創建 users 表"""
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INT PRIMARY KEY AUTO_INCREMENT,
                user_name VARCHAR(255) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL,
                database_name VARCHAR(255) NOT NULL,
                database_line_id VARCHAR(255),
                limit_size FLOAT DEFAULT 2.0  -- 新增 limit_size 欄位，預設為 2.0 GB
            )
        ''')
        self.conn.commit()

    def check_and_create_tables(self):
        """檢查並創建必要的表"""
        self.create_table_users()

    def insert_user(self, user_name, password, user_database_name, database_line_id, limit_size):
        """插入新用戶"""
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO users (user_name, password, database_name, database_line_id, limit_size)
            VALUES (%s, %s, %s, %s, %s)
        ''', (user_name, hashed_password.decode('utf-8'), user_database_name, database_line_id, limit_size))
        self.conn.commit()

    def update_user(self, user_id, new_password=None, new_database_name=None, new_limit_size=None):
        """更新用戶信息"""
        cursor = self.conn.cursor()
        updates = {}
        if new_password:
            updates['password'] = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        if new_database_name:
            updates['database_name'] = new_database_name
        if new_limit_size is not None:
            updates['limit_size'] = new_limit_size

        if updates:
            set_clause = ', '.join([f"{column} = %s" for column in updates.keys()])
            parameters = list(updates.values())
            parameters.append(user_id)
            sql = f"UPDATE users SET {set_clause} WHERE id = %s"
            cursor.execute(sql, parameters)
            self.conn.commit()

    def delete_admin(self, user_id):
        """刪除用戶"""
        cursor = self.conn.cursor()
        cursor.execute('''
            DELETE FROM users WHERE id = %s
        ''', (user_id,))
        self.conn.commit()

    def get_users(self, username=None):
        cursor = self.conn.cursor()
        """獲取所有用戶"""
        if username is None:
            cursor.execute('SELECT * FROM users')
            rows = cursor.fetchall()
            column_names = [column[0] for column in cursor.description]
            dict_rows = [dict(zip(column_names, row)) for row in rows]
        else:
            cursor.execute("SELECT * FROM users WHERE user_name = %s", (username,))
            rows = cursor.fetchall()
            column_names = [column[0] for column in cursor.description]
            dict_rows = [dict(zip(column_names, row)) for row in rows]
            if not dict_rows:
                return None
        return dict_rows

    def verify_user(self, user_name, password):
        """驗證用戶密碼"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT password FROM users WHERE user_name = %s', (user_name,))
        result = cursor.fetchone()
        if result:
            stored_password = result[0]
            return bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8'))
        return False

    def get_user_info(self, user_name):
        """根據用戶名獲取用戶信息"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_name = %s', (user_name,))
        result = cursor.fetchone()
        if result:
            column_names = [column[0] for column in cursor.description]
            return dict(zip(column_names, result))
        return None
    
if __name__ == "__main__":
    manager = AccountManager()
    manager.check_and_create_tables()
    manager.insert_user("admin", "hjkl1234", "admin_laoshifu", "@pp657783", limit_size=5.0)
    users = manager.get_users()
    print("所有用戶:", users)
