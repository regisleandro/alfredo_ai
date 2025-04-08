from dotenv import load_dotenv
import os
from openai import AzureOpenAI
import tiktoken
import json
import pandas as pd
import base64
import mimetypes
import tempfile
import pkg.rabbit as rabbit_service
import pkg.mongo as mongo_service
import pkg.github as github_service
import pkg.pulpo as pulpo_service
import pkg.trello as trello_service

# New imports for file processing
from PyPDF2 import PdfReader
import csv
import io
from PIL import Image

class Chatbot:
  def __init__(self):
    load_dotenv()
    self.client = AzureOpenAI(
      api_version=os.getenv('AZURE_AP_VERSION'),
      api_key=os.getenv('AZURE_OPENAI_API_KEY'),
      azure_deployment=os.getenv('AZURE_DEPLOYMENT_ID')
    )
    self.MODEL = 'gpt-4o-2024-11-20'
    self.VISION_MODEL = 'gpt-4o-vision-2024-05'
    self.rabbit = rabbit_service.Rabbit()
    self.vhost = None
    self.user_chat_histories = {}  # Dictionary to store chat histories by user ID

  def chat(self, query:str, vhost: str, user_id: str = "default", files=None) -> list:
    try:
      self.vhost = vhost

      if user_id not in self.user_chat_histories:
        self.user_chat_histories[user_id] = []
      
      chat_history = self.user_chat_histories[user_id]
      
      history_limit_warning = None
      if len(chat_history) >= 10:
        history_limit_warning = "⚠️ Você atingiu o limite de conversas sobre este tópico. Uma nova conversa está começando. Os dados das interações anteriores não estarão disponíveis."
        # Clear the chat history since we're starting fresh
        chat_history = []
        self.user_chat_histories[user_id] = chat_history
      
      file_content = None
      if files:
        file_content = self.process_files(files)
        
        if file_content and isinstance(file_content, str):
          query = f"{query}\n\nContent from file(s):\n{file_content}"
      
      chat_history.append({'role': 'user', 'content': query})
      
      if len(chat_history) > 10:
        chat_history = chat_history[-10:]
        self.user_chat_histories[user_id] = chat_history
      
      if files and not isinstance(file_content, str):
        initial_response = self.make_vision_request(query, file_content, user_id)
      else:
        initial_response = self.make_openai_request(query, user_id)
      
      message = initial_response.choices[0].message

      print(f"user_id: {user_id} || chat_history: {chat_history}")
      print('--------------------------------')
      print(f"Initial response: {message}")

      if message.content:
        chat_history.append({'role': 'assistant', 'content': message.content})
      
      if hasattr(message, 'function_call') and message.function_call:
        function_name = message.function_call.name
        arguments = json.loads(message.function_call.arguments)
        
        chat_history.append({
          'role': 'assistant', 
          'content': None,
          'function_call': {
            'name': function_name,
            'arguments': message.function_call.arguments
          }
        })
        
        function_response = getattr(self, function_name)(**arguments)
        
        chat_history.append({
          'role': 'function',
          'name': function_name,
          'content': str(function_response)
        })
        
        if len(chat_history) > 10:
          chat_history = chat_history[-10:]
          self.user_chat_histories[user_id] = chat_history
          
        if history_limit_warning:
          if isinstance(function_response, str):
            return history_limit_warning + "\n\n" + function_response
          else:
            return function_response
        
        return function_response
      
      if history_limit_warning:
        return history_limit_warning + "\n\n" + message.content
      
      return message.content
    except Exception as e:
      print(f"Error: {e}")
      return f'Perdão, mas não consegui responder a sua pergunta. Erro: {str(e)}'
    
  def process_files(self, files):
    """Process uploaded files based on their type"""
    if not files:
      return None
    
    results = []
    image_contents = []
    
    for file in files:
      print(f"file: {file.get('name')}")
      filename = file.get('name')
      content = file.get('content')
      
      # Try to detect content type from base64 content
      content_type = None
      if isinstance(content, str) and content.startswith('data:'):
        # Handle data URL format
        content_type = content.split(';')[0].split(':')[1]
      elif isinstance(content, (str, bytes)):
        # Try to detect from content
        if isinstance(content, str):
          try:
            content = base64.b64decode(content)
          except:
            pass
        
        if isinstance(content, bytes):
          # Check for common file signatures
          if content.startswith(b'\x89PNG\r\n\x1a\n'):
            content_type = 'image/png'
          elif content.startswith(b'\xff\xd8\xff'):
            content_type = 'image/jpeg'
          elif content.startswith(b'%PDF-'):
            content_type = 'application/pdf'
          elif content.startswith(b'\x50\x4B\x03\x04'):  # ZIP file signature
            content_type = 'application/zip'
          elif content.startswith(b'\x25\x50\x44\x46'):  # PDF alternative signature
            content_type = 'application/pdf'
          elif content.startswith(b'RIFF') and content[8:12] == b'WEBP':
            content_type = 'image/webp'
          elif content.startswith(b'GIF87a') or content.startswith(b'GIF89a'):
            content_type = 'image/gif'
          elif content.startswith(b'BM'):  # BMP file signature
            content_type = 'image/bmp'
          elif content.startswith(b'II*\x00') or content.startswith(b'MM\x00*'):  # TIFF file signature
            content_type = 'image/tiff'
      
      # Fallback to filename-based detection
      if not content_type:
        content_type = mimetypes.guess_type(filename)[0]
      # Additional fallback for image files
      if not content_type and filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff')):
        content_type = f'image/{filename.split(".")[-1].lower()}'
      
      with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        if isinstance(content, str):
          try:
            content = base64.b64decode(content)
          except:
            content = content.encode('utf-8')
        temp_file.write(content)
        file_path = temp_file.name
      
      try:
        if content_type == 'application/pdf':
          text = self.extract_text_from_pdf(file_path)
          results.append(f"=== PDF Content from {filename} ===\n{text}\n")
        
        elif content_type and content_type.startswith('image/'):
          try:
            # Try to open the image to verify it's valid
            with Image.open(file_path) as img:
              # Convert to RGB if necessary
              if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                img = img.convert('RGB')
              
              # Save the processed image
              processed_path = f"{file_path}_processed.jpg"
              img.save(processed_path, 'JPEG', quality=95)
              
              # Read the processed image
              with open(processed_path, 'rb') as img_file:
                processed_content = img_file.read()
              
              image_contents.append({
                'type': 'image_url',
                'image_url': {
                  'url': f"data:image/jpeg;base64,{base64.b64encode(processed_content).decode('utf-8')}"
                },
                'filename': filename
              })
              
              # Clean up the processed image
              os.unlink(processed_path)
          except Exception as e:
            print(f"Error processing image {filename}: {str(e)}")
            results.append(f"Error processing image {filename}: {str(e)}")
        
        elif content_type == 'text/csv':
          csv_data = self.extract_data_from_csv(file_path)
          results.append(f"=== CSV Content from {filename} ===\n{csv_data}\n")
        
        else:
          results.append(f"Unsupported file type for {filename}: {content_type or 'unknown'}")
      
      finally:
        os.unlink(file_path)
    
    if image_contents:
      return image_contents
    
    return "\n".join(results) if results else None
  
  def extract_text_from_pdf(self, file_path):
    """Extract text from PDF file"""
    try:
      reader = PdfReader(file_path)
      text = ""
      for page in reader.pages:
        text += page.extract_text() + "\n"
      return text
    except Exception as e:
      return f"Error extracting text from PDF: {str(e)}"
  
  def extract_data_from_csv(self, file_path):
    """Extract data from CSV file"""
    try:
      with open(file_path, 'r', encoding='utf-8') as f:
        csv_reader = csv.reader(f)
        rows = list(csv_reader)
        
        if rows:
          df = pd.DataFrame(rows[1:], columns=rows[0])
          
          if len(df) > 20:
            summary = f"CSV contains {len(df)} rows and {len(df.columns)} columns.\n"
            summary += f"Columns: {', '.join(df.columns)}\n"
            summary += f"First 5 rows:\n{df.head(5).to_string()}\n"
            summary += f"Last 5 rows:\n{df.tail(5).to_string()}"
            return summary
          else:
            return df.to_string()
      
      return "Empty CSV file"
    except Exception as e:
      return f"Error processing CSV: {str(e)}"
  
  def prepare_image_for_vision_api(self, file_path):
    """Prepare image for vision API by encoding it as base64"""
    try:
      with open(file_path, 'rb') as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
      print(f"Error preparing image: {str(e)}")
      return None
  
  def ensure_context_size(self, messages, token_limit):
    tokenizer = tiktoken.get_encoding("cl100k_base")  # Use a known supported encoding

    total_tokens = sum(len(tokenizer.encode(message.get('content', ''))) for message in messages if message.get('content'))

    if total_tokens > token_limit:
      while total_tokens > token_limit and len(messages) > 1:
        for i in range(len(messages)):
          if messages[i]['role'] != 'system':
            removed = messages.pop(i)
            total_tokens = sum(len(tokenizer.encode(message.get('content', ''))) for message in messages if message.get('content'))
            break

    return messages

  def make_openai_request(self, query: str, user_id: str = "default") -> dict:
    chat_history = self.user_chat_histories.get(user_id, [])
    
    messages = chat_history if chat_history else [{'role': 'user', 'content': query}]
    
    token_limit = 8000  # Conservative token limit for GPT-4o
    messages = self.ensure_context_size(messages, token_limit)
    
    response = self.client.chat.completions.create(
      model=self.MODEL,
      messages=messages,
      functions=self.FUNCTIONS
    )
    return response

  def make_vision_request(self, query: str, image_contents, user_id: str = "default") -> dict:
    """Make a request to the vision model with image content"""
    content = [{"type": "text", "text": query}]
    
    for img in image_contents:
      content.append(img)
    
    message = [{"role": "user", "content": content}]
    
    response = self.client.chat.completions.create(
      model=self.VISION_MODEL,
      messages=message,
      max_tokens=1000
    )
    return response

  def make_follow_up_request(self, query:str, initial_message:str, function_name:str, function_response, user_id:str = "default") -> dict:
    chat_history = self.user_chat_histories.get(user_id, [])
    
    messages = chat_history.copy()
    
    if not messages:
      messages = [
        {'role': 'user', 'content': query},
        initial_message
      ]
    
    if not messages or messages[-1].get('role') != 'function' or messages[-1].get('name') != function_name:
      messages.append({
        'role': 'function',
        'name': function_name,
        'content': function_response,
      })
    
    token_limit = 8000  # Conservative token limit for GPT-4o
    messages = self.ensure_context_size(messages, token_limit)
    
    response = self.client.chat.completions.create(
      model=self.MODEL,
      messages=messages,
      functions=self.FUNCTIONS
    )
    return response
  
  def analyze_file(self, file_content: str, file_type: str) -> str:
    """Analyze file content and return a summary"""
    prompt = f"""
    Please analyze the following {file_type} content and provide a concise summary:
    
    {file_content}
    
    Focus on:
    1. Key information and main topics
    2. Important statistics or data points
    3. Overall insights
    4. Potential issues or anomalies
    
    Please format your response as a clear, structured summary.
    """
    
    response = self.client.chat.completions.create(
      model=self.MODEL,
      messages=[{'role': 'user', 'content': prompt}],
      temperature=0.3,
      max_tokens=800
    )
    
    return response.choices[0].message.content
  
  def summarize_file(self, file_content: str, file_type: str) -> str:
    """Analyze and summarize file content"""
    return self.analyze_file(file_content, file_type)
  
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

    response = self.client.chat.completions.create(
        model=self.MODEL,
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
    
    response = self.client.chat.completions.create(
        model=self.MODEL,
        messages=[{'role': 'user', 'content': prompt}],
        max_tokens=500
    )

    return response.choices[0].message.content
  
  def strip_content(self, content: str) -> str:
    content_index = content.find('\n', 0)
    return content[:content_index].strip()

  # Update FUNCTIONS list to include the new file-related function
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
    {
      'name': 'summarize_file',
      'description': 'Analyze and summarize content from a file (PDF, CSV, etc.)',
      'parameters': {
        'type': 'object',
        'properties': {
          'file_content': {
            'type': 'string',
            'description': 'The extracted content from the file to be analyzed'
          },
          'file_type': {
            'type': 'string',
            'description': 'The type of file (PDF, CSV, image)',
            'enum': ['PDF', 'CSV', 'image', 'other']
          }
        },
        'required': ['file_content', 'file_type']
      }
    }
  ]