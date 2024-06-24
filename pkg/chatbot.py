from dotenv import load_dotenv
import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
import json
import pandas as pd
import pkg.rabbit as rabbit_service
import pkg.mongo as mongo_service
import pkg.github as github_service
import pkg.pulpo as pulpo_service

class Chatbot:
  def __init__(self):
    load_dotenv()
    self.rabbit = rabbit_service.Rabbit()
    self.vhost = None

  def chat(self, query:str, vhost: str) -> list:
    try:
      self.vhost = vhost
      initial_response = self.make_openai_request(query)
      message = initial_response.choices[0].message
      
      print(f"Initial response: {message}")

      if message.function_call:
        function_name = message.function_call.name
        arguments = json.loads(message.function_call.arguments)
        
        function_response = getattr(self, function_name)(**arguments)
        return function_response
      else:
        return 'Olá, sou o Alfredo, sou um agente de monitaramento de sistemas, tenho um escopo limitado a funções de suporte e não consigo responder a essa pergunta.'
    except Exception as e:
      print(f"Error: {e}")
      return 'Perdão, mas não consegui responder a sua pergunta'
  
  def make_openai_request(self, query:str) -> dict:
    response = client.chat.completions.create(model='gpt-3.5-turbo-0613',
    messages=[{'role': 'user', 'content': query}],
    functions=self.FUNCTIONS)
    return response

  def make_follow_up_request(self, query:str, initial_message:str, function_name:str, function_response) -> dict:
    response = client.chat.completions.create(model='gpt-3.5-turbo-0613',
    messages=[
      {'role': 'user', 'content': query},
      initial_message,
      {
        'role': 'function',
        'name': function_name,
        'content': function_response,
      },
    ])
    return response
  
  def get_queue_messages(self, queue_name:str, gpa_code:int= None, collection:str= None, limit:int= None) -> list:
    return self.rabbit.get_queue_messages(queue_name, gpa_code, collection, limit, vhost=self.vhost)

  def get_queue_status(self, queue_name:str=None, without_messages:bool=False) -> pd.DataFrame:
    return self.rabbit.get_queue_status(queue_name, without_messages, vhost=self.vhost)
  
  def summarize_queue_messages(self, queue_name:str, limit:int=None) -> pd.DataFrame:
    return self.rabbit.summarize_queue_messages(queue_name, limit, vhost=self.vhost)
  
  def resend_to_queue(self, queue_name:str, limit:int=50) -> str:
    return self.rabbit.resend_to_queue(queue_name, limit, vhost=self.vhost)
  
  def summarize_collections_with_error(self) -> pd.DataFrame:
    mongo = mongo_service.Mongo(database=self.vhost)
    return mongo.summarize_collections_with_error()
  
  def summarize_pictures_by_status(self, status: str) -> pd.DataFrame:
    mongo = mongo_service.Mongo(database=self.vhost)
    return mongo.summarize_pictures_by_status(status= status)
  
  def search_pull_requests(self, repo_name:str='', label:str='', status:str='closed') -> list:
    github = github_service.Github()
    return github.search_pull_requests(repo_name, status, label)
  
  def command_helper(self, question: str) -> str:
    mongo = mongo_service.Mongo(database=self.vhost)
    return mongo.command_helper(question)
  
  def search_documents(self, search_term: str) -> str:
    pulpo = pulpo_service.Pulpo()
    search_result = pulpo.search_documents(search_term)

    documents = [
      f"[{self.strip_content(doc.get('content', ''))}]({doc.get('url')})\n\n"
      for doc in search_result.get('documents', [])
    ]
    
    documents = ''.join(documents)

    related_questions = None
    if search_result.get('related_questions'):
      related_questions = '\n\n'.join(search_result.get('related_questions'))
    
    anwser = f"### {search_result['title']}\n{search_result.get('answer')}\n\n**Documentos relacionados**:\n\n{documents}"
    if related_questions:
      anwser += f"\n\n**Você pode perguntar sobre:**\n\n{related_questions}"

    return anwser
  
  def strip_content(self, content: str) -> str:
    content_index = content.find('\n', 0)
    return content[:content_index].strip()

  FUNCTIONS = [
    {
      'name': 'get_queue_messages',
      'description': 'Get messages from a queue',
      'parameters': {
        'type': 'object',
        'properties': {
          'queue_name': {
            'type': 'string',
            'description': 'The name of the queue to get messages from, e.g. "sync_mongo_to_postgres"',
            'default': None,
          },
          'gpa_code': {
            'type': 'integer',
            'description': 'GPA or client code to filter the messages',
            'default': None,
          },
          'collection': {
            'type': 'string',
            'description': 'the collection or model to filter the messages',
            'default': None,
          },          
          'limit': {
            'type': 'integer',
            'description': 'The number of messages to get from the queue, if not provided will get all messages',
            'default': None,
          },
        }
      },
    },
    {
      'name': 'resend_to_queue',
      'description': 'Resend/reprocess messages from a queue',
      'parameters': {
          'type': 'object',
          'properties': {
            'queue_name': {
              'type': 'string',
              'description': 'The name of the queue to get the reprocess of, e.g. "sync_mongo_to_postgres-error"',
            },
            'limit': {
              'type': 'integer',
              'description': 'The maximum number of messages to reprocess',
              'default': 50,
            },
          }
        },
    },
    {
      'name': 'get_queue_status',
      'description': 'Get the status of a queue',
      'parameters': {
          'type': 'object',
          'properties': {
            'queue_name': {
              'type': 'string',
              'description': 'The name of the queue to get the status of, e.g. "sync_mongo_to_postgres"',
            },
            'without_messages': {
              'type': 'boolean',
              'description': 'Whether to include messages with count > 0 in the response',
              'default': False,
            },
          }
        },
    },
    {
      'name': 'summarize_queue_messages',
      'description': 'Summarize or get statistics from  messages in a queue',
      'parameters': {
        'type': 'object',
        'properties': {
          'queue_name': {
            'type': 'string',
            'description': 'The name of the queue to summarize the messages from, e.g. "sync_mongo_to_postgres"',
            'default': None,
          },
          'limit': {
            'type': 'integer',
            'description': 'The maximum number of messages to return',
            'default': 50,
          },
        }
      },
    },
    {
      'name': 'summarize_collections_with_error',
      'description': 'Summarize or get the status of the synchronization errors in Mongo',
    },
    {
      'name': 'summarize_pictures_by_status',
      'description': 'Summarize or get status for pictures in Mongo by status',
      'parameters': {
        'type': 'object',
        'properties': {
          'status': {
            'type': 'string',
            'description': 'The status to filter need to be "pending", "done" or "error"',
            'default': 'pending',
          },
        }
      },      
    },
    {
      'name': 'search_pull_requests',
      'description': 'List the commits from pull requests in a repository',
      'parameters': {
        'type': 'object',
        'properties': {
          'status': {
            'type': 'string',
            'description': 'The status to filter need to be "closed", "all" or "open"',
            'default': 'closed',
          },
          'repo_name': {
            'type': 'string',
            'description': 'The name of the repository to search for pull requests, e.g. "alfredo-ai"',
            'default': '',
          },
          'label': {
            'type': 'string',
            'description': 'The label to filter the pull requests, e.g. "bug" or "enhancement"',
            'default': '',
          },
        }
      },      
    },
    {
      'name': 'command_helper',
      'description': 'Search and retrieve information to anwser questions about the systems commands and functions',
      'parameters': {
        'type': 'object',
        'properties': {
          'question': {
            'type': 'string',
            'description': 'The question that need to be anwsered, e.g. "wich commands are available?"',
            'default': 'wich commands are available?',
          },
        }
      },
    },
    {
      "name": "search_documents",
      "description": "Search in the Pulpo knowledge base for documents that match the provided search term.",
      "parameters": {
        "type": "object",
        "properties": {
          "search_term": {
            "type": "string",
            "description": "The term or phrase to search for in the Pulpo knowledge base, e.g., 'how to create a new user in Pulpo'."
          }
        },
        "required": ["search_term"]
      }
    }
  ]
