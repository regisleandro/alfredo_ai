import requests
import os
from dotenv import load_dotenv

load_dotenv()

TRELLO_URL = os.getenv('TRELLO_URL')
TRELLO_TOKEN = os.getenv('TRELLO_TOKEN')

class Trello:
  def __init__(self):
    pass

  def call_trello_tasks(self, task_id):
    url = f"{TRELLO_URL}/api/cards/{task_id}"
    print(f"Fetching data from: {url}")
    response = requests.get(url, headers={'Authorization': f"Token {TRELLO_TOKEN}"})
    return response.json()

