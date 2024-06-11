import requests
import os
import json
import base64
from dotenv import load_dotenv

load_dotenv()

USER_PULPO = os.getenv('USER_PULPO')
PASSWORD_PULPO = os.getenv('PASSWORD_PULPO')
PULPO_SEARCH_URL = os.getenv('PULPO_SEARCH_URL')
PULPO_URL = os.getenv('PULPO_URL')

class Pulpo:

  def search_documents(self, search_term: str) -> list:
    print(f"Searching for documents in knowledge base with term: {search_term}")
    token = base64.b64encode(f"{USER_PULPO}:{PASSWORD_PULPO}".encode()).decode()
    headers = {
      'authorization': f"Basic {token}",
      'origin': PULPO_URL,
      'Content-Type': 'application/json',
    }

    search_params = self.search_params(search_term)

    response = requests.post(PULPO_SEARCH_URL, data=search_params, headers=headers)

    print(f"response {response}")

    if response.status_code == 200:
      data = response.json()
      print(f"data {data}")
      search_result = data[0]['data']['findAnswer']

      return {
        'answer': search_result['answer'],
        'title': search_result['record']['parent']['title'],
        'url': f"{PULPO_URL}/{search_result['record']['parent']['slug']}"
      }
    else:
      print(f"Error: {response}")
      return {
        'answer': 'Não encontrei nada na base de conhecimento',
        'title': 'Nada encontrado',
        'url': ''
      }

  def search_params(self, search_term: str) -> dict:    
    query = """
    query findAnswer($query: String, $parent: String, $cacheOnly: Boolean) {
      systemTime
      findAnswer(query: $query, parent: $parent, cacheOnly: $cacheOnly) {
        cached
        answer
        relatedQuestions
        record {
          ...recordWithParent
        }
        documents {
          id
          content
        }
      }
    }

    fragment recordWithParent on Record {
      ...record
      parent {
        id
        slug
        title
        typename
        color
        thumbnailUrl
      }
    }

    fragment record on Record {
      id
      slug
      title
      trail
      typename
      color
      thumbnailUrl
      downloadUrl
      origin
      identifier
      createdAt
      updatedAt
      status
    }
    """

    variables = {
      'query': search_term,
      'cacheOnly': False
    }

    payload = {
        'query': query,
        'variables': variables,
        'operationName': 'findAnswer'
    }

    return json.dumps([payload])