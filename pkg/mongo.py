import os
from pymongo import MongoClient
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

MONGO_AQILA_URL_PRD = os.getenv('MONGO_AQILA_URL_PRD')
MONGO_AQILA_URL_HML = os.getenv('MONGO_AQILA_URL_HML')


class Mongo:
  def __init__(self, database: str = None):
    self.database = database
    if self.database=='aqila-hml':
       self.database = 'aqila-homologacao'
    
    self.client = MongoClient(MONGO_AQILA_URL_HML)

    if database == 'aqila':
      self.client = MongoClient(MONGO_AQILA_URL_PRD)    


  def summarize_collections_with_error(self) -> pd.DataFrame:
    db = self.client[self.database]

    collection_names = db.list_collection_names()
    result = []
    
    for collection_name in collection_names:
      pipeline = [
        {'$match': {'has_sync_error': True}},
        {'$group': {'_id': {'_gpa_code': '$_gpa_code'}, 'count': {'$sum': 1}}}
      ]

      data = db[collection_name].aggregate(pipeline)

      for doc in data:
        result.append(
          {
            '_gpa_code': doc['_id']['_gpa_code'],
            'collection': collection_name,
            'qtde': doc['count']
          }
        )
    
    df = pd.DataFrame.from_dict(result)
    print(df)
    return df



  



