import os
from pymongo import MongoClient
from dotenv import load_dotenv
import pandas as pd
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import MongoDBAtlasVectorSearch

from langchain.chat_models import ChatOpenAI

from langchain.prompts.chat import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)


load_dotenv()

MONGO_AQILA_URL_PRD = os.getenv('MONGO_AQILA_URL_PRD')
MONGO_AQILA_URL_HML = os.getenv('MONGO_AQILA_URL_HML')
MONGO_ALFREDO_URL = os.getenv('MONGO_ALFREDO_URL') 

class Mongo:
  def __init__(self, database: str = None):
    self.database = database
    if self.database=='aqila-hml':
       self.database = 'aqila-homologacao'
    
    self.client = MongoClient(MONGO_AQILA_URL_HML)

    if database == 'aqila':
      self.client = MongoClient(MONGO_AQILA_URL_PRD)    


  def summarize_collections_with_error(self) -> pd.DataFrame:
    db = self.client[self.database]

    collection_names = db.list_collection_names()
    result = []
    
    for collection_name in collection_names:
      pipeline = [
        {'$match': {'has_sync_error': True, 'pending_sync': True}},
        {'$group': {'_id': {'_gpa_code': '$_gpa_code'}, 'count': {'$sum': 1}}}
      ]

      data = db[collection_name].aggregate(pipeline)

      for doc in data:
        result.append(
          {
            '_gpa_code': doc['_id']['_gpa_code'],
            'collection': collection_name,
            'qtde': doc['count']
          }
        )
    
    df = pd.DataFrame.from_dict(result)
    print(f"summarize_collections_with_error: {df}")
    return df

  def summarize_pictures_by_status(self, status: str) -> pd.DataFrame:
    db = self.client[self.database]

    collection_name = 'fotos'
    result = []    
    pipeline = [
      {'$match': {'status': status}},
      {'$group': {'_id': {'_gpa_code': '$_gpa_code'}, 'count': {'$sum': 1}}}
    ]

    data = db[collection_name].aggregate(pipeline)

    for doc in data:
      result.append(
        {
          '_gpa_code': doc['_id']['_gpa_code'],
          'collection': collection_name,
          'status': status,
          'qtde': doc['count'], 
        }
      )
    
    df = pd.DataFrame.from_dict(result)
    print(f"summarize_pictures_by_status: {df}")
    return df
  
  def command_helper(self, query: str) -> str:
    print(f"command_helper: {query}")
    documents = self.create_vector_search().similarity_search_with_score(
      query=query,
      k=5,
    )

    list_documents = []
    for document in documents:
      list_documents.append(document[0])

    awnser = self.answer_question(list_documents, query)
    print(f"command_helper: {awnser.content}")  
    return awnser.content

  def create_vector_search(self):
    print(f"create_vector_search: {MONGO_ALFREDO_URL}")
    return MongoDBAtlasVectorSearch.from_connection_string(
      MONGO_ALFREDO_URL,
      'alfredo.comandos',
      OpenAIEmbeddings(),
      index_name='default',
      text_key='descricao'
    )

  def create_system_message_template(self) -> SystemMessagePromptTemplate:
    template = """
      Você é um assistante online que irá auxiliar em buscas em uma database.
      Se você não souber a resposta, apenas diga que não sabe, não tente inventar uma resposta.
      Procure sumarizar o contexto e responder a pergunta de forma clara e objetiva.
      {context}
      Responda em português.
    """
    return SystemMessagePromptTemplate.from_template(template)

  def answer_question(self, documents:list, question: str):
    system_message_prompt = self.create_system_message_template()
    human_message_prompt = HumanMessagePromptTemplate.from_template("{question}")

    chat_prompt = ChatPromptTemplate.from_messages([system_message_prompt, human_message_prompt])

    model_name = 'gpt-3.5-turbo'
    llm = ChatOpenAI(model_name=model_name, temperature=0)

    return llm(
      chat_prompt.format_prompt(
        context=documents, question=question
      ).to_messages()
    )