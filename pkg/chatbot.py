from dotenv import load_dotenv
import os
import openai
import json
import pkg.rabbit as rabbit_service

class Chatbot:
  def __init__(self):
    load_dotenv()
    self.rabbit = rabbit_service.Rabbit()
    self.vhost = None
    openai.api_key = os.getenv('OPENAI_API_KEY')

  def chat(self, query:str, vhost: str) -> list:
    self.vhost = vhost
    initial_response = self.make_openai_request(query)
    
    message = initial_response['choices'][0]['message']
    
    if message.get('function_call'):
      function_name = message['function_call']['name']
      arguments = json.loads(message['function_call']['arguments'])

      print(f"callgin function: {function_name} with arguments: {arguments}")
      
      function_response = getattr(self, function_name)(**arguments)
      #follow_up_response = self.make_follow_up_request(query, message, function_name, function_response)
      return function_response #follow_up_response['choices'][0]['message']['content']
    else:
      return message
  
  def make_openai_request(self, query:str) -> dict:
    response = openai.ChatCompletion.create(
      model='gpt-3.5-turbo-0613',
      messages=[{'role': 'user', 'content': query}],
      functions=self.FUNCTIONS
    )
    return response

  def make_follow_up_request(self, query:str, initial_message:str, function_name:str, function_response) -> dict:
    response = openai.ChatCompletion.create(
      model='gpt-3.5-turbo-0613',
      messages=[
        {'role': 'user', 'content': query},
        initial_message,
        {
          'role': 'function',
          'name': function_name,
          'content': function_response,
        },
      ],
    )
    return response
  
  def get_queue_messages(self, queue_name:str, limit:int=5) -> list:
    return self.rabbit.get_queue_messages(queue_name, limit, vhost=self.vhost)

  def get_queue_estatus(self, queue_name:str=None, without_messages:bool=False) -> list:
    return self.rabbit.get_queue_estatus(queue_name, without_messages, vhost=self.vhost)
  
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
          'limit': {
            'type': 'integer',
            'description': 'The maximum number of messages to return',
            'default': 5,
          },
        }
      },
    },
    {
      'name': 'get_queue_estatus',
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
    }
  ]
  