from chat_logic_main import ChatLogic

#import pandas as pd

# 創建 ChatLogic 的實例
chat = ChatLogic()

#創建一個示例 DataFrame
#df = pd.DataFrame({'column1':[1, 2, 3],'column2':['a','b','c']})

#傳遞 DataFrame 作為參數
chat.create_prompt_template()



def main():
    print("聊天機器人: 你好！請輸入一些問題，或者輸入 '退出' 來結束對話。")

    while True:
        user_input = input("你: ")
        if user_input.lower() == "退出":
            print("聊天機器人: 再見！")
            break

        response = chat.execute_chat(user_input, chat_history,4)
        print("聊天機器人:", response)

if __name__ == "__main__":
    chat_history = []
    main()
