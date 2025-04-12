import os
from dotenv import load_dotenv
from trello import TrelloClient


load_dotenv()

TRELLO_API_SECRET = os.getenv('TRELLO_API_SECRET')
TRELLO_API_KEY = os.getenv('TRELLO_API_KEY')
class Trello:
  def __init__(self):
    self.client = TrelloClient(
      api_key=TRELLO_API_KEY,
      api_secret=TRELLO_API_SECRET
    )

  def search(self, query:str):
    cards = self.client.search(query, partial_match=True, cards_limit=5)
    cards_json = []
    for index, card in enumerate(cards):
      comments = self.get_comments(card)
      checklists = self.get_checklists(card)
      cards_json.append({
        'id': index + 1,
        'name': card.name,
        'card_id': card.id,
        'url': card.url,
        'desc': card.desc,
        'comments': comments,
        'due': card.due,
        'checklists': checklists
      })
    return cards_json

  def get_comments(self, card):
    comments = []
    for comment in card.comments:
      data = comment.get('data')
      comments.append({
        'text': data.get('text'),
        'id': data.get('id'),
        'name': data.get('name')
      })
    return comments
  
  def get_checklists(self, card):
    checklists = []
    for checklist in card.checklists:
      checklists.append({
        'name': checklist.name,
        'id': checklist.id,
        'items': [item.get('name') for item in checklist.items]
      })
    return checklists
