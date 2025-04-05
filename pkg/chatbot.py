from dotenv import load_dotenv
import os
from openai import AzureOpenAI
import tiktoken

import json

load_dotenv()

client =  AzureOpenAI(
  api_version=os.getenv('AZURE_AP_VERSION'),
  api_key=os.getenv('AZURE_OPENAI_API_KEY'),
  azure_deployment=os.getenv('AZURE_DEPLOYMENT_ID')
)

MODEL = 'gpt-4o-2024-11-20'

# import json
import pandas as pd
import pkg.rabbit as rabbit_service
import pkg.mongo as mongo_service
import pkg.github as github_service
import pkg.pulpo as pulpo_service
import pkg.trello as trello_service

class Chatbot:
  def __init__(self):
    load_dotenv()
    self.rabbit = rabbit_service.Rabbit()
    self.vhost = None
    self.user_chat_histories = {}  # Dictionary to store chat histories by user ID

  def chat(self, query:str, vhost: str, user_id: str = "default") -> list:
    try:
      self.vhost = vhost
      
      # Initialize chat history for this user if it doesn't exist
      if user_id not in self.user_chat_histories:
        self.user_chat_histories[user_id] = []
      
      # Get the user's chat history
      chat_history = self.user_chat_histories[user_id]
      
      # Check if we'll exceed the limit with this new message
      history_limit_warning = None
      if len(chat_history) >= 10:
        history_limit_warning = "⚠️ Você atingiu o limite de conversas sobre este tópico. Uma nova conversa está começando. Os dados das interações anteriores não estarão disponíveis."
        # Clear the chat history since we're starting fresh
        chat_history = []
        self.user_chat_histories[user_id] = chat_history
      
      # Add user message to chat history
      chat_history.append({'role': 'user', 'content': query})
      
      # Keep only the last 5 conversations (10 messages total)
      if len(chat_history) > 10:
        chat_history = chat_history[-10:]
        self.user_chat_histories[user_id] = chat_history
      
      initial_response = self.make_openai_request(query, user_id)
      message = initial_response.choices[0].message

      print(f"chat_history: {chat_history}")
      
      print(f"Initial response: {message}")

      # Add assistant's response to chat history
      if message.content:
        chat_history.append({'role': 'assistant', 'content': message.content})
      
      if message.function_call:
        function_name = message.function_call.name
        arguments = json.loads(message.function_call.arguments)
        
        # Add function call to chat history
        chat_history.append({
          'role': 'assistant', 
          'content': None,
          'function_call': {
            'name': function_name,
            'arguments': message.function_call.arguments
          }
        })
        
        function_response = getattr(self, function_name)(**arguments)
        
        # Add function response to chat history
        chat_history.append({
          'role': 'function',
          'name': function_name,
          'content': str(function_response)
        })
        
        # Keep only the last 5 conversations
        if len(chat_history) > 10:
          chat_history = chat_history[-10:]
          self.user_chat_histories[user_id] = chat_history
          
        # If we had a history limit warning, prepend it to the response
        if history_limit_warning:
          if isinstance(function_response, str):
            return history_limit_warning + "\n\n" + function_response
          else:
            # For non-string responses (like DataFrames or lists), we can't easily prepend the warning
            # So we'll just return the function response as is
            return function_response
        
        return function_response
      
      # If we had a history limit warning, prepend it to the response
      if history_limit_warning:
        return history_limit_warning + "\n\n" + message.content
      
      return message.content
    except Exception as e:
      print(f"Error: {e}")
      return 'Perdão, mas não consegui responder a sua pergunta'
    
  def ensure_context_size(self, messages, token_limit):
    # Use a supported encoding
    tokenizer = tiktoken.get_encoding("cl100k_base")  # Use a known supported encoding

    # Calculate the total number of tokens in the messages
    total_tokens = sum(len(tokenizer.encode(message['content'])) for message in messages if message['content'])

    # Check if the total tokens exceed the limit
    if total_tokens > token_limit:
      raise ValueError("The context size exceeds the model's token limit.")

    return messages

  def make_openai_request(self, query: str, user_id: str = "default") -> dict:
    # Get the user's chat history or use an empty list if not found
    chat_history = self.user_chat_histories.get(user_id, [])
    
    # If chat history is empty, use just the current query
    messages = chat_history if chat_history else [{'role': 'user', 'content': query}]
    
    # Validate context size and raise an error if it exceeds the limit
    token_limit = 8000  # Conservative token limit for GPT-4o
    self.ensure_context_size(messages, token_limit)
    
    response = client.chat.completions.create(
      model=MODEL,
      messages=messages,
      functions=self.FUNCTIONS
    )
    return response

  def make_follow_up_request(self, query:str, initial_message:str, function_name:str, function_response, user_id:str = "default") -> dict:
    # Get the user's chat history
    chat_history = self.user_chat_histories.get(user_id, [])
    
    # Create a temporary messages list that includes the chat history plus the function response
    messages = chat_history.copy()
    
    # If chat history is empty, add the initial query and response
    if not messages:
      messages = [
        {'role': 'user', 'content': query},
        initial_message
      ]
    
    # Add the function response if not already in history
    if not messages or messages[-1].get('role') != 'function' or messages[-1].get('name') != function_name:
      messages.append({
        'role': 'function',
        'name': function_name,
        'content': function_response,
      })
    
    # Validate context size and truncate if necessary
    token_limit = 8000  # Conservative token limit for GPT-4o
    messages = self.ensure_context_size(messages, token_limit)
    
    response = client.chat.completions.create(
      model=MODEL,
      messages=messages,
      functions=self.FUNCTIONS
    )
    return response
  
  def get_queue_messages(self, queue_name:str=None, gpa_code:int=None, collection:str=None, limit:int= None) -> list:
    print(f"queue_name: {queue_name}, gpa_code: {gpa_code}, collection: {collection}, limit: {limit}")
    if queue_name is None and gpa_code is not None:
      queue_name = str(gpa_code)
    return self.rabbit.get_queue_messages(queue_name, gpa_code, collection, limit, vhost=self.vhost)

  def get_queue_status(self, queue_name:str=None, without_messages:bool=False) -> pd.DataFrame:
    return self.rabbit.get_queue_status(queue_name, without_messages, vhost=self.vhost)
  
  def summarize_queue_messages(self, queue_name:str, limit:int=None) -> pd.DataFrame:
    return self.rabbit.summarize_queue_messages(queue_name, limit, vhost=self.vhost)
  
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
  
  def task_analyst(self, task_id: int, query: str, board_name: str='inovacao', user_id: str = "default") -> str:
    trello = trello_service.Trello()
    task = trello.call_trello_tasks(task_id, board_name)
    task_description = task.get('description', 'not found')
    comments = ""
    for comment in task.get('comments', []):
      user = comment.get('user', '')
      date = comment.get('comment_date')
      text = comment.get('comment', '')
      comments += f"**comment** {text} by member **{user}** in **{date}** |"

    prompt = f"""
      You are an experienced tech leader assisting a development team with a specific task.  
      Your goal is to provide **clear, objective, and well-founded answers** based strictly on the provided context.  

      ---  
      ### Context:  
      Name: {task.get('name', 'Not available')}  
      Description: {task_description}  
      Comments: {comments}  
      ---  

      ### Question:  
      {query}  
      ---  

      ### Instructions:  
      - **Use all sections of the provided context**, including the Comments, to formulate a precise answer.  
      - **Do not omit insights from the Task Comments**; incorporate them naturally into your response.  
      - **If the information is insufficient, ask for clarification concisely.**  
      - **Always provide the answer in Portuguese.**  

      Now, provide your response.
    """

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{'role': 'user', 'content': prompt}],
        max_tokens=500
    )

    return response.choices[0].message.content

  def task_manager_analyst(self, task_description: str, user_id: str = "default") -> str:
    prompt = f"""
      You are a software/quality analyst responsible for creating a task in BDD (Behavior-Driven Development) format for the development team. The task description is: **{task_description}**.

      Your goal is to write a clear and structured task in BDD format, following these guidelines:

      1. **Task Structure**: Use the provided markdown format to structure the task:
        - **Feature**: [Feature Name]
        - **As a** [Role/User]  
        - **I want** [Functionality]  
        - **So that** [Benefit/Value]
        - **Scenario**: [Scenario Name]  
          - **Given** [Initial Context]  
          - **When** [Event/Action]  
          - **Then** [Expected Outcome]

      2. **Scenarios**: Always include three scenarios:
        - One for the **success case** (when everything works as expected).
        - One for the **failure case** (when something goes wrong or an error occurs).
        - One for the **edge case** (an unusual or extreme situation).

      3. **Doubts/Risks**: Include a section called **Pontos de dúvida** (Points of Doubt) to highlight any risks, uncertainties, or questions that need clarification before implementation.

      4. Always generate the task in Portuguese.

      Let's proceed step by step:
    """
    
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{'role': 'user', 'content': prompt}],
        max_tokens=500
    )

    return response.choices[0].message.content
  
  def strip_content(self, content: str) -> str:
    content_index = content.find('\n', 0)
    return content[:content_index].strip()

  FUNCTIONS = [
    {
      'name': 'get_queue_messages',
      'description': 'Get messages from a queue, either by queue name or GPA code',
      'parameters': {
        'type': 'object',
        'properties': {
          'queue_name': {
            'type': 'string',
            'description': 'The name of the queue to get messages from, e.g. "sync_mongo_to_postgres" or "8504"',
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
      'name': 'search_documents',
      'description': 'Search in the Pulpo knowledge base for documents that match the provided search term.',
      'parameters': {
        'type': 'object',
        'properties': {
          'search_term': {
            'type': 'string',
            'description': "The term or phrase to search for in the Pulpo knowledge base, e.g., 'how to create a new user in Pulpo'."
          }
        },
        'required': ['search_term']
      }
    },
    {
      'name': 'task_analyst',
      'description': 'Extracts the task ID, board name, and user`s query about the task from a given text.',
      'parameters': {
        'type': 'object',
        'properties': {
          'query': {
            'type': 'string',
            'description': 'The user`s question about the task, excluding task ID and board name. Example: "quais os comentários da tarefa?" instead of "quais os comentários da tarefa 2256 do time inovacao?" or "resuma a tarefa 2256 do time inovacao.".'
          },
          'board_name': {
            'type': 'string',
            'description': "The development team or board name to get the task information, e.g. 'inovacao'",
            'default': 'inovacao',
          },
          'task_id': {
            'type': 'integer',
            'description': 'The numeric ID of the task, extracted from the input text. Example: 2256 if the question is "quais os comentários da tarefa 2256 do time inovacao?".'
          },          
        },
      'required': ['task_id', 'query'],
      },
    },
    # {
    #   'name': 'task_manager_analyst',
    #   'description': 'Create tasks for developers, analysing the request and creating a task in BDD format',
    #   'parameters': {
    #     'type': 'object',
    #     'properties': {
    #       'task_description': {
    #         'type': 'string',
    #         'description': 'The description of the task to be created, e.g. "describe a task to create a new user in the system"',
    #         'default': 'describe a task to create a new user in the system',
    #       },
    #     }
    #   },
    # },        
  ]
