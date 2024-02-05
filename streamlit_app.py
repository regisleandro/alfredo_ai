import streamlit as st
import json

import pkg.chatbot as chatbot_service

chatbot = chatbot_service.Chatbot()

def chat(query):
  return chatbot.chat(query) 

## Stremalit App
st.title('🕵️‍♀️ Alfredo`s AI')

if 'messages' not in st.session_state:
    st.session_state.messages = []
    st.session_state['messages'] = [{'role': 'assistant', 'content': 'Olá, como posso ajudá-lo?'}]

for message in st.session_state.messages:
  with st.chat_message(message['role'], avatar=message['role'] == 'assistant' and '🕵️‍♀️' or '🧑‍💻'):    
    if isinstance(message['content'], list):
      json_data = json.dumps(message['content'], indent=2)
      st.code(json_data, language='json')
    else:
      st.markdown(message['content'])

if prompt := st.chat_input('Olá, sou o Alfredo, sou um agente que monitora o RabbitMQ, como posso ajudá-lo?'):
  st.session_state.messages.append({'role': 'user', 'content': prompt})

  with st.chat_message('user', avatar='🧑‍💻'):
    st.markdown(prompt)
  with st.chat_message('assistant', avatar='🕵️‍♀️'):
    with st.spinner('Consultando 🔍 ...'):
      message_place_holder = st.empty()
      responses = chat(prompt)
      json_data = json.dumps(responses, indent=2)
      st.code(json_data, language='json')

  st.session_state.messages.append({'role': 'assistant', 'content': responses})
