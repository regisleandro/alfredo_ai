import base64
from fastapi import (
    FastAPI,
    Body,
    Depends,
    HTTPException,
    status,
    Request,
    File,
    UploadFile,
    Form
)

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
import logging
from typing import Optional

import sys
sys.path.append('../')

from dotenv import load_dotenv
import os

load_dotenv()

from pydantic import BaseModel
from pkg.chatbot import Chatbot

import json
import traceback
# Import the response translator
from api.formatters.response_translator import translate_response

log = logging.getLogger(__name__)

app = FastAPI()

SIMPLE_TOKEN = os.getenv('API_TOKEN')

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
async def chat(request: Request):
  try:
    # Check content type
    content_type = request.headers.get('content-type', '')
    
    # Handle different content types
    if 'multipart/form-data' in content_type:
      form_data = await request.form()
      query = form_data.get('query')
      user_id = form_data.get('user_id', 'default')
      file = form_data.get('file')
      
      file_content = None
      file_name = None
      
      if file:
        file_content = await file.read()
        file_name = file.filename
    else:
      try:
        # Try to parse JSON first
        data = await request.json()
        query = data.get('query')
        user_id = data.get('user_id', 'default')
        
        file_content = None
        file_name = None
        
        if 'file' in data:
          file_data = data.get('file')
          if file_data:
            if 'content' in file_data and file_data['content']:
              try:
                file_content = base64.b64decode(file_data['content']) if isinstance(file_data['content'], str) else file_data['content']
              except Exception as e:
                log.error(f"Error decoding base64 content: {e}")
                file_content = file_data['content']
            file_name = file_data.get('name', 'uploaded_file')
      except json.JSONDecodeError:
        # If JSON parsing fails, try to get raw body
        try:
          body = await request.body()
          if body:
            # Try to decode with different encodings
            try:
              body_str = body.decode('utf-8')
            except UnicodeDecodeError:
              try:
                body_str = body.decode('latin-1')
              except:
                body_str = body.decode('utf-8', errors='replace')
            
            # Try to parse as JSON again
            try:
              data = json.loads(body_str)
              query = data.get('query')
              user_id = data.get('user_id', 'default')
            except:
              # If still not JSON, treat as raw query
              query = body_str
              user_id = 'default'
        except Exception as e:
          log.error(f"Error processing request body: {e}")
          raise HTTPException(status_code=400, detail="Invalid request format")
    
    if not query:
      raise HTTPException(status_code=400, detail="Query parameter is required")
    
    chatbot = app.state.chatbot
    files = None

    if file_content and file_name:
      files = [{'content': file_content, 'name': file_name}]
    response = chatbot.chat(
      query=query,
      vhost='aqila',
      user_id=user_id,
      files=files
    )

    return translate_response(response)
  except Exception as e:
    print(e)
    print(traceback.format_exc())
    log.error(f"Error in chat: {str(e)}")
    raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

@app.post("/task_manager_analyst")
async def task_manager_analyst(request: Request):
  data = await request.json()
  task_description = data.get("task_description")
  user_id = data.get("user_id", "default") 
  
  chatbot = app.state.chatbot
  response = chatbot.task_manager_analyst(task_description=task_description, user_id=user_id)
  
  return translate_response(response)

@app.post("/task_analyst")
async def task_analyst(request: Request):
  data = await request.json()
  task_id = data.get("task_id")
  query = data.get("query")
  board_name = data.get("board_name", "inovacao")
  user_id = data.get("user_id", "default") 
  
  chatbot = app.state.chatbot
  # Update task_analyst method in chatbot.py to accept user_id
  response = chatbot.task_analyst(task_id=task_id, query=query, board_name=board_name)
  
  return translate_response(response)