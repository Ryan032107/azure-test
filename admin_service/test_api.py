import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

load_dotenv()

class DatabaseManager:
    def __init__(self, database_name):
        self.database_name = database_name
        self.conn = self.get_connection()

    def get_connection(self):
        """創建與MySQL數據庫的連接"""
        try:
            conn = mysql.connector.connect(
                host=os.getenv('DB_HOST'),
                user=os.getenv('DB_USER'),
                password=os.getenv('DB_PASSWORD'),
                database=self.database_name
            )
            return conn
        except Error as e:
            print(f"無法建立連接: {e}")
            return None

    def test_mysql_connection(self):
        """測試與MySQL數據庫的連接"""
        try:
            connection = self.get_connection()
            if connection and connection.is_connected():
                print("成功連接到MySQL數據庫")
                connection.close()  # 測試完成後關閉連接
            else:
                print("無法連接到MySQL數據庫")
        except Error as e:
            print(f"連接MySQL時發生錯誤: {e}")

# 使用示例
if __name__ == '__main__':
    db_manager = DatabaseManager('test_db')
    db_manager.test_mysql_connection()
