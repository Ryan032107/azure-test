from pymongo import MongoClient
from dotenv import load_dotenv
from requests.auth import HTTPDigestAuth
import os
import requests
import time
from pymongo.errors import PyMongoError

load_dotenv()

class MongoDBManager:
    def __init__(self):
        self.client = MongoClient(os.getenv('MONGODB_URI'))
        self.public_key = os.getenv('MONGODB_Public_Key')
        self.private_key = os.getenv('MONGODB_Private_Key')
        self.group_id = os.getenv('MONGODB_Group_ID')
        self.cluster_name = os.getenv('Cluster_Name')
        self.db_name = os.getenv("Database_Name")

    def create_collection(self, collection_name):
        db = self.client[self.db_name]
        if collection_name not in db.list_collection_names():
            db.create_collection(collection_name)
            print(f"Collection '{collection_name}' created.")
            index_name = self.replace_spaces_with_underscores(str(collection_name)) + '_vector_search_index'
            self.create_vector_search_index(collection_name, index_name)
            print((f"index '{index_name}' created."))
            time.sleep(1)
        else:
            print(f"Collection '{collection_name}' already exists.")

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

    def replace_spaces_with_underscores(self,input_string):
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
    def delete_collection(self, collection_name):
        self.db = self.client[self.db_name]
        self.collection = self.db[collection_name]
        try:
            # 删除 self.collection 集合
            self.collection.drop()
        except PyMongoError as e:
            return e
        return f"Collection '{collection_name}' deleted."
    # print(get_distinct_sources('your_collection_name'))
# mg = MongoDBManager()
# search_result = mg.search_text("PFT", "Automation", "UO[8]")
# print(search_result)
