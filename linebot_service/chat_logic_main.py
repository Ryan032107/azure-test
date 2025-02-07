import os
import json
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, PromptTemplate
from langchain.agents.format_scratchpad.openai_tools import format_to_openai_tool_messages
from langchain.agents.output_parsers.openai_tools import OpenAIToolsAgentOutputParser
from langchain.agents import AgentExecutor
from chat_costomer_support_tools import get_tools
from db import SQLManager

class ChatLogic:
    def __init__(self, env_file=".env"):
        # 定义聊天历史的键
        self.MEMORY_KEY = "chat_history"
        self.prompt_message = None
        self.sql_manager = SQLManager()
        # 在第一次創建時先指派，後續更新只要不重新創建物件就不會變為 None。
        self.prompt = None
        self.tools = None

        load_dotenv(env_file)
        self.openai_api_key = os.getenv('OPENAI_API_KEY')

        self.prompt_llm = ChatOpenAI(model="gpt-4o", temperature=0, openai_api_key=self.openai_api_key, max_tokens=500)

    def generate_prompt(self, df):
        prompt_message = """
        Generate a concise system prompt in English:
        You are an assistant. Your primary task is to assist based on user inquiries by prioritizing database information.
        Call databases when needed. Respond in Traditional Chinese.
        If the database does not return relevant results, avoid giving a response that is incorrect or random.
        For every question, please follow the guideline below:
        """
        collections = df['collection_name']
        descriptions = df['prompt']
        
        tools_name_list = [f"Search_{item}" for item in collections]

        for tools_name, description in zip(tools_name_list, descriptions):
            tool_for = f"use {tools_name} when the user asks about {description}. "
            prompt_message += tool_for
        self.system_prompt = self.prompt_llm.invoke(prompt_message).content
    
    def create_prompt_template(self, df):
        self.generate_prompt(df)  # 确保提示信息已加载
        self.tools = get_tools(df['collection_name'])
        print("Prompt template 更新完畢！")

    def configure_agent(self, user_id, model_version, image_data):
        # 取得此 user 能 access 的 collection_name:List
        collection_permission_name = self.sql_manager.get_user_permission_collections(user_id)
        # 只保留能 access 的 collections
        self.tools = [tool for tool in self.tools if any(n in tool.name for n in collection_permission_name)]

        # 基本消息模板
        if image_data:
            self.prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", self.system_prompt),
                    MessagesPlaceholder(variable_name=self.MEMORY_KEY),
                    ("user", "{input}"),
                    MessagesPlaceholder(variable_name="agent_scratchpad"),
                    # image url
                    ("human", [
                        {
                            "type": "image_url",
                            "image_url": {"url": "data:image/jpeg;base64,{image_data}"},
                        },
                    ]),
                ]
            )
            model_name = "gpt-4o"
        else:
            self.prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", self.system_prompt),
                    MessagesPlaceholder(variable_name=self.MEMORY_KEY),
                    ("user", "{input}"),
                    MessagesPlaceholder(variable_name="agent_scratchpad"),
                ]
            )
            model_name = "gpt-4o-mini"
        
        # model_name = "gpt-4o" if model_version == 4 else "gpt-3.5-turbo"
        llm = ChatOpenAI(model=model_name, temperature=0, openai_api_key=self.openai_api_key, max_tokens=1000)
        agent = (
            {
                "input": lambda x: x["input"],
                "agent_scratchpad": lambda x: format_to_openai_tool_messages(x["intermediate_steps"]),
                "chat_history": lambda x: x["chat_history"],
                "image_data": lambda x: x["image_data"],
            }
            | self.prompt
            | llm.bind_tools(self.tools)
            | OpenAIToolsAgentOutputParser()
        )
        return AgentExecutor(agent=agent, tools=self.tools, verbose=True, max_execution_time=20)

    def execute_chat(self, user_id, input_message, chat_history, model_version, image_data=None):
        agent_executor = self.configure_agent(user_id, model_version, image_data)
        result = agent_executor.invoke({"input": input_message, "chat_history": chat_history, "image_data": image_data})
        return result["output"]