import os
import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage
from langchain.tools import StructuredTool
from langchain.pydantic_v1 import BaseModel, Field
from langchain_community.utilities import GoogleSearchAPIWrapper
from langchain_openai import OpenAIEmbeddings
from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain.tools.retriever import create_retriever_tool
from pymongo.mongo_client import MongoClient

from dotenv import load_dotenv

load_dotenv()
class Chat_Tools:
    def __init__(self):
        self.db_uri = os.getenv('MONGODB_URI')
        self.db_name = os.getenv('Database_Name')
        self.openai_api_key = os.getenv('OPENAI_API_KEY')

    def collection_knowledge(self, collection_name):
        DB_NAME = self.db_name
        COLLECTION_NAME = collection_name
        index_name = self.replace_spaces_with_underscores(str(collection_name)) + '_vector_search_index'
        ATLAS_VECTOR_SEARCH_INDEX_NAME = index_name
        vector_search = MongoDBAtlasVectorSearch.from_connection_string(
            self.db_uri,
            DB_NAME + "." + COLLECTION_NAME,
            OpenAIEmbeddings(disallowed_special=(),openai_api_key=self.openai_api_key),
            index_name=ATLAS_VECTOR_SEARCH_INDEX_NAME,
        )
        retriever = vector_search.as_retriever(
            search_type="similarity",
            search_kwargs={
                "k": 15,
                "score_threshold": 0.8,
            },
        )
        return retriever

    def replace_spaces_with_underscores(self,input_string):
        # Replace all spaces with underscores
        return input_string.replace(' ', '_')

def get_tools(collection_name):
    Chat_tools = Chat_Tools()
    collections = collection_name
    tools = []

    for collection in collections:
        tools.append(create_retriever_tool(
            Chat_tools.collection_knowledge(collection),
            Chat_tools.replace_spaces_with_underscores("Search_" + str(collection)),
            "Searches and returns " + str(collection) + " knowledge."
        )
        )
    return tools
