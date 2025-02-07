from pymongo import MongoClient
from dotenv import load_dotenv
from requests.auth import HTTPDigestAuth
import os
import requests
import time
from pymongo.errors import PyMongoError
import logging

load_dotenv()

class MongoDBManager:
    def __init__(self, MONGODB_URI, MONGODB_Public_Key, MONGODB_Private_Key, MONGODB_Group_ID, Cluster_Name, Database_Name):
        self.MONGODB_URI = MONGODB_URI
        self.public_key = MONGODB_Public_Key
        self.private_key = MONGODB_Private_Key
        self.group_id = MONGODB_Group_ID
        self.cluster_name = Cluster_Name
        self.db_name = Database_Name
        self.client = None  # 延遲初始化
    
    def __enter__(self):
        # 在進入 with 語句時初始化 MongoClient
        self.client = MongoClient(self.MONGODB_URI)
        print("Connected to MongoDB.")
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        # 在退出 with 語句時關閉 MongoClient
        if self.client:
            self.client.close()
            print("MongoDB connection closed.")
    
    def create_collection(self, collection_name):
        db = self.client[self.db_name]
        if collection_name not in db.list_collection_names():
            db.create_collection(collection_name)
            print(f"Collection '{collection_name}' created.")
            index_name = self.replace_spaces_with_underscores(str(collection_name)) + '_vector_search_index'
            self.create_vector_search_index(collection_name, index_name)
            print((f"Index '{index_name}' created."))
            time.sleep(1)
        else:
            print(f"Collection '{collection_name}' already exists.")

    def update_collection(self, old_collection_name, new_collection_name):
        self.db = self.client[self.db_name]
        old_collection = self.db[old_collection_name]

        # 检查旧的和新的集合名称是否相同，如果相同则跳过重命名
        if old_collection_name == new_collection_name:
            print(f"Collection name '{old_collection_name}' is the same as '{new_collection_name}'. Skipping rename.")
            return f"Collection '{old_collection_name}' is the same as '{new_collection_name}'. No rename necessary."

        # 创建新的 vector search index 名称
        old_index_name = self.replace_spaces_with_underscores(old_collection_name) + '_vector_search_index'
        new_index_name = self.replace_spaces_with_underscores(new_collection_name) + '_vector_search_index'

        logging.info(f"---------------old_collection_name:{old_collection_name}---------------")
        logging.info(f"---------------old_index_name:{old_index_name}---------------")

        # 删除旧的索引
        self.delete_vector_search_index(old_collection_name, old_index_name)
        print(f"Index '{old_index_name}' deleted.")
        
        # 确保新集合名称不存在
        if new_collection_name in self.db.list_collection_names():
            return f"Collection '{new_collection_name}' already exists."

        # 重命名集合
        new_collection = old_collection.rename(new_collection_name)
        print(f"Collection '{old_collection_name}' renamed to '{new_collection_name}'.")
        
        time.sleep(40)

        # 为新集合创建向量搜索索引
        self.create_vector_search_index(new_collection_name, new_index_name)
        print(f"Index '{new_index_name}' created.")
        
        return f"Collection '{old_collection_name}' successfully updated to '{new_collection_name}'."


    def delete_collection(self, collection_name):
        self.db = self.client[self.db_name]
        self.collection = self.db[collection_name]
        try:
            # 删除 self.collection 集合
            self.collection.drop()
        except PyMongoError as e:
            return e
        return f"Collection '{collection_name}' deleted."

    def create_vector_search_index(self, collection_name, index_name, num_dimensions=1536, path='embedding', similarity='cosine'):
        url = f'https://cloud.mongodb.com/api/atlas/v1.0/groups/{self.group_id}/clusters/{self.cluster_name}/fts/indexes'
        data = {
            "collectionName": collection_name,
            "database": self.db_name,
            "type": "vectorSearch",
            "name": index_name,
            "fields": [
                {
                    "numDimensions": num_dimensions,
                    "path": path,
                    "similarity": similarity,
                    "type": "vector"
                }
            ]
        }
        response = requests.post(
            url,
            auth=HTTPDigestAuth(self.public_key, self.private_key),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json"
            },
            json=data
        )
        print(response.status_code)
        print(response.text)

    def delete_vector_search_index(self, collection_name, index_name):
        try:
            self.db = self.client[self.db_name]
            self.collection = self.db[collection_name]
            # 使用 pymongo 库删除索引
            self.collection.drop_search_index(index_name)
            print(f"Index '{index_name}' deleted successfully.")
        except Exception as e:
            print(f"Failed to delete index: {str(e)}")

    def check_vector_search_index(self, collection_name):
        """
        檢查該集合是否有向量搜尋索引，若無則建立一個新的。
        """
        try:
            self.db = self.client[self.db_name]
            self.collection = self.db[collection_name]
            
            # 列出現有的索引
            existing_indexes = self.collection.index_information()
            index_name = self.replace_spaces_with_underscores(str(collection_name)) + '_vector_search_index'
            
            # 檢查是否已存在指定的向量搜尋索引
            if index_name in existing_indexes:
                logging.info(f"向量搜尋索引 '{index_name}' 已經存在於集合 '{collection_name}' 中。")
            else:
                logging.info(f"向量搜尋索引 '{index_name}' 不存在，正在為集合 '{collection_name}' 創建索引...")
                # 如果索引不存在，則創建向量搜尋索引
                self.create_vector_search_index(collection_name, index_name)
                logging.info(f"向量搜尋索引 '{index_name}' 已成功創建。")
        except Exception as e:
            logging.info(f"檢查或創建索引時發生錯誤: {str(e)}")

    def replace_spaces_with_underscores(self, input_string):
        # Replace all spaces with underscores
        return input_string.replace(' ', '_')
    
    def ensure_text_index(self):
        # 检查集合中是否已经存在文本索引，如果不存在则创建
        if "text" not in self.collection.index_information():
            self.collection.create_index([("text", "text")])

    def search_text(self, collection_name, text):
        self.db = self.client[self.db_name]
        self.collection = self.db[collection_name]

        # 检查并创建文本索引
        self.ensure_text_index()
        
        # 执行文本搜索
        search_result = self.collection.find({"$text": {"$search": f"\"{text}\""}})
        
        if self.collection.count_documents({"$text": {"$search": f"\"{text}\""}}) > 0:
            # 只返回第一个匹配文档的 _id 和 "text" 字段
            for document in search_result:  # 使用循环访问第一个文档
                return {
                    "_id": str(document.get("_id", "")),  # 将 ObjectId 转换为字符串
                    "text": document.get("text", "No text found")
                }
                break  # 找到第一个匹配项后退出循环
        else:
            return "No found"

    def get_distinct_sources(self, collection_name):
        self.db = self.client[self.db_name]
        self.collection = self.db[collection_name]
        distinct_sources = self.collection.distinct('source')
        return distinct_sources

    def delete_document(self, collection_name, document_source):
        self.db = self.client[self.db_name]
        self.collection = self.db[collection_name]
        try:
            # 删除 self.collection 集合中 "source" 字段值为 collection_name 的文档
            result = self.collection.delete_many({"source": document_source})
        except PyMongoError as e:
            return e
        return f"Deleted {result.deleted_count} documents."
