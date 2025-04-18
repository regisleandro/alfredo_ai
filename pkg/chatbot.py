from dotenv import load_dotenv
import os
from openai import AzureOpenAI
import tiktoken
import json
import pandas as pd
import pkg.rabbit as rabbit_service
import pkg.mongo as mongo_service
import pkg.github as github_service
import pkg.pulpo as pulpo_service
import pkg.trello as trello_service
import inspect
from pkg.file_processor import FileProcessor
from pkg.constants import TOOLS

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
        self.file_processor = FileProcessor()  # Initialize FileProcessor

    def chat(self, query: str, vhost: str, user_id: str = "default", files=None) -> list:
        try:
            self.vhost = vhost

            if user_id not in self.user_chat_histories:
                self.user_chat_histories[user_id] = []

            chat_history = self.user_chat_histories[user_id]

            history_limit_warning = None
            if len(chat_history) >= 10:
                history_limit_warning = """⚠️ Você atingiu o limite de conversas sobre este tópico.
                  Uma nova conversa está começando. Os dados das interações anteriores não estarão disponíveis.
                """
                # Clear the chat history since we're starting fresh
                chat_history = []
                self.user_chat_histories[user_id] = chat_history

            file_content = None
            if files:
                file_content = self.file_processor.process_files(files)

                if file_content and isinstance(file_content, str):
                    query = f"{query}\n\nContent from file(s):\n{file_content}"

            if files and not isinstance(file_content, str):
                initial_response = self.make_vision_request(query, file_content, user_id)
            else:
                initial_response = self.make_openai_request(query, user_id)

            message = initial_response.choices[0].message

            print(f"user_id: {user_id} || chat_history: {chat_history}")
            print('--------------------------------')
            print(f"Initial response: {message}")

            if hasattr(message, 'tool_calls') and message.tool_calls:
                tool_call = message.tool_calls[0]
                function_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)
                print(f"function_name: {function_name}, arguments: {arguments}")

                # Check if method accepts user_id parameter
                method = getattr(self, function_name)
                signature = inspect.signature(method)
                if 'user_id' in signature.parameters:
                    arguments['user_id'] = user_id

                function_response = method(**arguments)
                chat_history.append({
                    'role': 'assistant',
                    'content': self.format_function_response(function_response)
                })

                return function_response

            chat_history.append({'role': 'assistant', 'content': message.content})

            if history_limit_warning:
                return history_limit_warning + "\n\n" + message.content

            self.user_chat_histories[user_id] = chat_history

            return message.content
        except Exception as e:
            print(f"Error: {e}")
            return f'Perdão, mas não consegui responder a sua pergunta. Erro: {str(e)}'
    
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
        messages = self.user_chat_histories.get(user_id, [])
        messages.append({'role': 'user', 'content': query})
        
        token_limit = 8000  # Conservative token limit for GPT-4o
        messages = self.ensure_context_size(messages, token_limit)
        
        response = self.client.chat.completions.create(
            model=self.MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice='auto'
        )
        return response
    
    def make_vision_request(self, query: str, image_contents, user_id: str = "default") -> dict:
        """Make a request to the vision model with image content"""
        
        content = [{"type": "text", "text": query}]
        
        for img in image_contents:
            content.append(img)
        
        response = self.client.chat.completions.create(
            model=self.VISION_MODEL,
            messages=[{"role": "user", "content": content}],
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
            functions=TOOLS
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
    
    def get_queue_messages(self, queue_name:str=None, gpa_code:int=None, collection:str=None, limit:int=None) -> list:
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
        return mongo.summarize_pictures_by_status(status=status)
    
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
    
    def task_helper(self, task_query: str, user_id:str="default") -> str:
        trello = trello_service.Trello()
        cards = trello.search(task_query)
        chat_history = self.user_chat_histories.get(user_id, [])
        chat_history.append({
            'role': 'user',
            'content': f"### Context:\n{cards}"
        })
        prompt = f"""
          You are an experienced tech leader assisting a development team to search and get information about tasks in Trello.  
          Your goal is to provide **clear, objective, and well-founded answers** based strictly on the provided context.  

          ### Instructions:  
          You will receive a JSON with multiple tasks. 
          If the context has only one task then you will summarize the task and provide the answer.
          Else, create a list of tasks with the id (the number in the card), name and a link to the task.
          Then, ask which task you would like to discuss. If I send a number or description, respond based on that information.
          ---  
          ### Context:  
          {cards}
          ---  
          ### Instructions:  
          - **Always provide the answer in Portuguese.**  

          Now, provide your response.
        """

        response = self.client.chat.completions.create(
            model=self.MODEL,
            messages=[{'role': 'user', 'content': prompt}],
            max_tokens=8000
        )

        self.user_chat_histories[user_id] = chat_history
      
        return response.choices[0].message.content
    
    def strip_content(self, content: str) -> str:
        content_index = content.find('\n', 0)
        return content[:content_index].strip()

    def format_function_response(self, function_response):
        """Format the function response for better readability."""
        if isinstance(function_response, dict):
            return json.dumps(function_response, indent=4, ensure_ascii=False)
        elif isinstance(function_response, list):
            return '\n'.join(map(str, function_response))
        else:
            return str(function_response)