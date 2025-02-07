from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv
import os
load_dotenv()

class Chat_Record_Manager:
    def __init__(self):
        self.db_uri = os.getenv('MONGODB_URI')
        self.client = MongoClient(self.db_uri)
        self.db = self.client['Chat_Record']
        self.user_usage_collection = self.db['UserUsage']
        self.group_info_collection = self.db['GroupInfo']

    def get_or_create_user_usage(self, user_id):

        user_data = self.user_usage_collection.find_one({"userId": user_id})
        current_time = datetime.now().isoformat()
        if not user_data:
            user_data = {
                "userId": user_id,
                "chat_history": [],
                "model_version": 4,
                "GTP 4o frequency of use": 0,
                "All frequency of use": 0,
                "createAt": current_time,
                "updateAt": current_time
            }
            self.user_usage_collection.insert_one(user_data)
        else:
            current_date = datetime.now().date().isoformat()  # 獲取當前日期
            previous_update_date = user_data['updateAt'][:10]
            
            if previous_update_date != current_date:
                self.user_usage_collection.update_one(
                    {"userId": user_id},
                    {"$set": {"GTP 4o frequency of use": 0, "All frequency of use":0, "updateAt":current_time}},
                    upsert=True
                )
                user_data["GTP 4o frequency of use"] = 0
                user_data["All frequency of use"] = 0
                user_data["updateAt"] = current_time

        return user_data
    
    def delete_user_chat_history(self, user_id):
        try:
            # 查找用戶的資料
            user_data = self.user_usage_collection.find_one({"userId": user_id})
            
            if user_data:
                # 更新資料，刪除 chat_history
                self.user_usage_collection.update_one(
                    {"userId": user_id},
                    {"$set": {"chat_history": [], "updateAt": datetime.now().isoformat()}}
                )
            return True
        
        except:
            return False
        
        
    def add_chat_record(self, user_id, role, content, user_data):
        # 構造新的聊天記錄，包括角色和內容
        new_record = {"role": role, "content": content}
                
        # 初始化要更新的字段
        update_fields = {
            "$push": {"chat_history": {"$each": [new_record], "$slice": -5}},
            "$set":{}
        }
        
        # 如果為GPT回復
        if role == "assistant":
            if user_data['model_version'] == 4:
                update_fields["$set"]["GTP 4o frequency of use"] = user_data["GTP 4o frequency of use"] + 1
            update_fields["$set"]["All frequency of use"] = user_data["All frequency of use"] + 1

        # 更新UserUsage集合
        self.user_usage_collection.update_one(
            {"userId": user_id},
            update_fields,
            upsert=True
        )
    def get_or_create_group_info(self, type, group_or_room_Id):
        group_info = self.group_info_collection.find_one({"group_or_room_Id": group_or_room_Id})
        current_time = datetime.now().isoformat()
        if not group_info:
            group_info = {
                "type": type,
                "group_or_room_Id": group_or_room_Id,
                "enable status": True,
                "createAt": current_time,
                "updateAt": current_time
            }
            self.group_info_collection.insert_one(group_info)

        return group_info
    def switch_group_enable_status(self, group_or_room_id, enable_status):
        current_time = datetime.now().isoformat()
        self.group_info_collection.update_one(
            {"group_or_room_Id": group_or_room_id},
            {"$set": {"enable status": enable_status, "updateAt": current_time}}
        )

    def switch_model(self, user_id, model_version):
        # 初始化要更新的字段
        self.user_usage_collection.update_one(
            {"userId": user_id},
            {"$set": {"model_version": model_version}}
        )

# Chat = Chat_Record_Manager()
# Chat.add_chat_record("Uc9d5b03cd10ed201c67459b3cd8c2b72","assistant","回復",3)
