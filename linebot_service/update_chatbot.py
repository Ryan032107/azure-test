import os
import sys
import logging
from db import SQLManager

# 将 LAOSHIFU 目录添加到 sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from chat_logic_main import ChatLogic

# Set up logging
logging.basicConfig(level=logging.INFO)

def update_chatbot():
    logging.info(f"模型開始更新！")
    try:
        # 5.& 6. create new tools & create new system prompt
        df, need_update_df = SQLManager().get_collections()
        logging.info(f"這是新版的 collection_name： {df['collection_name']}")
        ChatLogic().create_prompt_template(df)
        logging.info(f"新的 system prompt 已更新完成")
        
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return {"status": "failed", "message": f"模型更新失敗：{e} 請儘速通知管理員！"}
    return {"status": "completed", "message": "模型更新成功！"}

# update_chatbot()