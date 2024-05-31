import requests
import os
import json
from dotenv import load_dotenv

load_dotenv()

BEARER = os.getenv('PULPO_BEARER')
PULPO_SEARCH_URL = os.getenv('PULPO_SEARCH_URL')
PULPO_URL = os.getenv('PULPO_URL')

class Pulpo:

  def search_documents(self, search_term: str) -> list:
    print(f"Searching for documents in knowledge base with term: {search_term}")
    headers = {
      'authorization': f"Bearer {BEARER}",
      'origin': PULPO_URL,
      'Content-Type': 'application/json',
    }

    search_params = self.search_params(search_term)

    response = requests.post(PULPO_SEARCH_URL, data=search_params, headers=headers)

    if response.status_code == 200:
      data = response.json()
      search_result = data[0]['data']['findAnswer']

      return {
        'answer': search_result['answer'],
        'title': search_result['record']['parent']['title'],
        'url': f"{PULPO_URL}/{search_result['record']['parent']['slug']}"
      }
    else:
      print(f"Error: {response}")
      return {}

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