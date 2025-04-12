import os
from pymongo import MongoClient
from dotenv import load_dotenv
import pandas as pd

from langchain_openai import OpenAIEmbeddings
from langchain.vectorstores import MongoDBAtlasVectorSearch

from langchain_core.prompts.chat import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain_openai import ChatOpenAI


load_dotenv()

MONGO_AQILA_URL_PRD = os.getenv('MONGO_AQILA_URL_PRD')
MONGO_AQILA_URL_HML = os.getenv('MONGO_AQILA_URL_HML')
MONGO_DB_ALFREDO = os.getenv('MONGO_DB_ALFREDO') 

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
      list_documents.append(f"{document[0].page_content} - {document[0].metadata['comandos']}")
    print(f"command_helper - list: {list_documents}")
    awnser = self.answer_question(list_documents, query)

    return awnser.content

  def create_vector_search(self):
    print(f"create_vector_search: {MONGO_DB_ALFREDO}")
    return MongoDBAtlasVectorSearch.from_connection_string(
      MONGO_DB_ALFREDO,
      'alfredo.comandos',
      OpenAIEmbeddings(),
      index_name='default',
      text_key='descricao'
    )

  def answer_question(self, documents:list, question: str):
    model_name = 'gpt-3.5-turbo-0613'
    chat = ChatOpenAI(model_name=model_name, temperature=0)
    template = (
      """
        Você é um assistante online que irá auxiliar a encontrar comandos de código para realizar tarefas, utilizando o contexto de documentos a seguir.
        {documents}
        Retorne os comandos encontrados com a forma de um comando por linha. Formatado em markdown.
        Responda em português.
      """
    )
    system_message_prompt = SystemMessagePromptTemplate.from_template(template)
    human_message_prompt = HumanMessagePromptTemplate.from_template("{question}")

    chat_prompt = ChatPromptTemplate.from_messages([system_message_prompt, human_message_prompt])
    return chat.invoke(chat_prompt.format_prompt(question=question, documents=documents).to_messages())
