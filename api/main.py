from fastapi import (
    FastAPI,
    Body,
    Depends,
    HTTPException,
    status
)

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
import logging

import sys
sys.path.append('../')

from dotenv import load_dotenv
import os

load_dotenv()

from pydantic import BaseModel
from pkg.chatbot import Chatbot

import json
import pandas as pd

log = logging.getLogger(__name__)

app = FastAPI()

SIMPLE_TOKEN = 'iOiJIUzI1NiJ9.eyJSb2xlIjoiQWRtaW4iLCJJc3N1ZXIiOiJJc3N1ZXIiLCJVc2VybmFtZSI6' #os.getenv('API_TOKEN')

security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
  token = credentials.credentials
  if token != SIMPLE_TOKEN:
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="Invalid token",
      headers={"WWW-Authenticate": "Bearer"},
    )

origins = ['*']

app.add_middleware(
  CORSMiddleware,
  allow_origins=origins,
  allow_credentials=True,
  allow_methods=['*'],
  allow_headers=['*'],
)

app.state.chatbot = Chatbot()

@app.get('/')
async def get_status():
  return {
    'status': True,
    'message': 'Alfredo is running'
  }

class ChatRequest(BaseModel):
  query: str

@app.post('/chat', dependencies=[Depends(verify_token)])
async def chat(chat_request: ChatRequest = Body(...)):
  vhost = 'aqila'
  log.info(f"Chatting with Alfredo: {chat_request.query}")
  response = app.state.chatbot.chat(chat_request.query, vhost)

  return translate_response(response)

def translate_response(response):
  if isinstance(response, list):
    return {
      "text": f"```\n{json.dumps(response, indent=2)}\n```"
    }
  if isinstance(response, pd.DataFrame):
    return dataframe_to_markdown_list(response)
  else:
    return {
      "text": response
    }

def dataframe_to_markdown_list(df):
  markdown_list = ""
  for _, row in df.iterrows():
    list_item = "- " + ", ".join([f"{col}: *{row[col]}*" for col in df.columns]) + "\n"
    markdown_list += list_item
  return format_markdown_to_google_chat_card(markdown_list)

def format_markdown_to_google_chat_card(markdown_text):
  # Substituir caracteres de escape por seus equivalentes reais
  markdown_text = (
    markdown_text.replace('\\n', '\n')
    .replace('\\t', '    ')
    .replace('\\"', '"')
  )

  # Dividir o texto em linhas
  lines = markdown_text.split('\n')

  # Criar widgets para cada linha
  widgets = []
  for line in lines:
    if line.strip():  # Ignorar linhas vazias
        # Processar formatação básica de markdown
        # Substituir *texto* por <b>texto</b> para negrito
        formatted_line = line.replace('*', '<b>', 1)
        if '*' in formatted_line:
          formatted_line = formatted_line.replace('*', '</b>', 1)
          remaining_asterisks = formatted_line.count('*')
          for i in range(0, remaining_asterisks, 2):
            if i < remaining_asterisks:
              formatted_line = formatted_line.replace('*', '<b>', 1)
            if i + 1 < remaining_asterisks:
              formatted_line = formatted_line.replace('*', '</b>', 1)
        
        widgets.append({
          "keyValue": {
            "content": formatted_line,
            "contentMultiline": True
          }
        })

  card = {
    "cards": [
      {
        "sections": [
          {
            "widgets": widgets
          }
        ]
      }
    ]
  }

  return card