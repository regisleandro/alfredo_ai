import requests
import base64
import json
import pika
import ssl
import pandas as pd
import pkg.constants as constants
from dotenv import load_dotenv
import os
load_dotenv()

RABBITMQ_USER = os.getenv('RABBITMQ_USERNAME')
RABBITMQ_PASSWORD = os.getenv('RABBITMQ_PASSWORD')
RABBITMQ_VHOST = os.getenv('RABBITMQ_VIRTUAL_HOST')
RABBITMQ_URL = os.getenv('RABBITMQ_URL')
RABBITMQ_HML_USER = os.getenv('RABBITMQ_HML_USER')
RABBITMQ_HML_PASSWORD = os.getenv('RABBITMQ_HML_PASSWORD')
RABBITMQ_HML_PORT = os.getenv('RABBITMQ_HML_PORT')
RABBITMQ_HML_VIRTUAL_HOST = os.getenv('RABBITMQ_HML_VIRTUAL_HOST')
RABBITMQ_PRD_USER = os.getenv('RABBITMQ_PRD_USER')
RABBITMQ_PRD_PASSWORD = os.getenv('RABBITMQ_PRD_PASSWORD')
RABBITMQ_PRD_PORT = os.getenv('RABBITMQ_PRD_PORT')
RABBITMQ_PRD_VIRTUAL_HOST = os.getenv('RABBITMQ_PRD_VIRTUAL_HOST')

class Rabbit:

  def __init__(self):
    print(RABBITMQ_URL)
    self.rabbitmq_api_host = f"https://{RABBITMQ_URL}/api/queues/"
    self.auth = (RABBITMQ_USER, RABBITMQ_PASSWORD)
    self.vhost = None
  
  def get_queue_url(self, queue_name: str) -> str:
    queue_url = f"{self.rabbitmq_api_host}{RABBITMQ_VHOST}"
    if self.vhost is not None:
      queue_url = f"{self.rabbitmq_api_host}{self.vhost}"
    if queue_name is not None:
      queue_url = f"{queue_url}/{queue_name}"
    return queue_url

  def get_queue_status(self, queue_name: str=None, without_messages: bool = False, vhost:str = None) -> pd.DataFrame:
    self.vhost = vhost
    queue_url = self.get_queue_url(queue_name)

    response = requests.get(queue_url, auth=self.auth)
    queues = []
    if response.status_code == 200:
      queues_data = response.json()
      if not isinstance(queues_data, list):
        queues_data = [queues_data]

      for queue in queues_data:
        queues.append(
          {
            'queue_name': queue['name'],
            'consumers': queue['consumers'],
            'state':  queue['state'],
            'messages_count':  queue['messages']
          }
        )
        print(without_messages, queue_name)
        if not without_messages and queue_name is None:
          print(f"Getting messages from queue: {queue_name}")
          queues = list(filter(lambda x: x['messages_count'] > 0, queues))
      queues_df = pd.DataFrame(queues)
      return queues_df
    else:
      print(f"Error: {response.status_code} - {response.text}")
      return None

  def get_queue_messages(self, queue_name: str, gpa_code: int = None, limit: int = None, vhost: str = None) -> list:
    self.vhost = vhost
    if limit is None:
      queue_status = self.get_queue_status(queue_name, without_messages=True, vhost=vhost)
      limit = int(queue_status['messages_count'].values[0])
    
    print(f"Getting {limit} messages from {queue_name} in {self.vhost} from gpa_code {gpa_code}")

    params = {'count': limit, 'ackmode': 'ack_requeue_true', 'encoding': 'auto'}
    queue_url = f"{self.get_queue_url(queue_name)}/get"
    response = requests.post(queue_url, auth=self.auth, json=params)

    messages = []
    if response.status_code == 200:
      messages_data = response.json()
      for message in messages_data:
        message_body = message['payload']

        try:
          payload = json.loads(message_body)['payload']
          message_body = base64.b64decode(payload).decode('utf-8')

        except Exception as e:
          print(f"Error decoding message: {e}")
        
        if type(message_body) == str:
          try:
            message_body = json.loads(message_body)
          except Exception as e:
            print(f"Error parsing message: {e}")
        print('message_body', message_body)
        messages.append(message_body)
      
      if gpa_code is not None:
        messages = list(filter(lambda x: x.get('config', {}).get('gpa_code') == gpa_code, messages))
      print(len(messages))
      return messages
    else:
      print(f"Error: {response.status_code} - {response.text}")
      return None
    
  def resend_to_queue(self, queue_name: str, limit: int, vhost: str = None) -> str: 
    self.vhost = vhost
    destination_queue = queue_name.split('-')[0]
    messages = self.get_queue_messages(queue_name=queue_name, limit=limit, vhost=vhost)
    print(f"Resending {len(messages)} messages to {destination_queue}")
    try:
      if messages is not None:
        for message in messages:
          self.send_message(destination_queue, message)
        return f"Foram reprocessadas {len(messages)} mensagens da fila {queue_name} para a fila {destination_queue}"
      else:
        return f"Não foi possível reprocessar as mensagens da fila {queue_name} para a fila {destination_queue}"
    except Exception as e:
      print(f"Error resending messages: {e}")
      return f"Ocorreu um erro ao reenviar as mensagens: {e}"
    
  def send_message(self, queue_name: str, message: dict) -> bool:
    url = self.get_rabbitmq_amq_string()
    print(f"Connecting to {url}")
    params = pika.URLParameters(url)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()

    channel.exchange_declare(exchange='aqila_exg', exchange_type='topic', durable=True)
    
    routing_key = None
    match queue_name:
      case 'sync_to_postgres':
        routing_key = constants.RoutingKey.AQILA_FIREBIRD_TO_API
      case 'sync_to_mongo':
        routing_key = constants.RoutingKey.AQILA_API_TO_MONGO
      case _:
        routing_key = f"{constants.RoutingKey.AQILA_API_TO_FIREBIRD}.{queue_name}"

    channel.basic_publish(exchange='aqila_exg', routing_key=routing_key, body=json.dumps(message))
    print(f"Sending {message} to {queue_name}  - routing_key {routing_key} - in {self.vhost}")
    channel.close()
    connection.close()
    return True

  def summarize_queue_messages(self, queue_name: str, limit: int = None, vhost: str = None) -> pd.DataFrame:
    messages = self.get_queue_messages(queue_name=queue_name, limit=limit, vhost=vhost)
    try:
      if messages is not None:
        df = pd.DataFrame.from_dict(messages)

        config_df = pd.DataFrame.from_dict(df['config'].values.tolist())
        config_df = config_df.astype(str)
        grouped = config_df.groupby(['gpa_code', 'tenant', 'model', 'origin']).count()
        grouped.columns = ['qtde']

        return grouped
      else:
        return None
      
    except Exception as e:
      print(f"Error summarizing messages: {e}")
      return None
    
  def get_rabbitmq_amq_string(self) -> str:
    if self.vhost == 'aqila':
      return f"amqps://{RABBITMQ_PRD_USER}:{RABBITMQ_PRD_PASSWORD}@{RABBITMQ_URL}:{RABBITMQ_PRD_PORT}/{RABBITMQ_PRD_VIRTUAL_HOST}"
    elif self.vhost == 'aqila-hml':
      return f"amqps://{RABBITMQ_HML_USER}:{RABBITMQ_HML_PASSWORD}@{RABBITMQ_URL}:{RABBITMQ_HML_PORT}/{RABBITMQ_HML_VIRTUAL_HOST}"
