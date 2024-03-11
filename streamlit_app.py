import streamlit as st
import json
import pandas as pd

import pkg.chatbot as chatbot_service

chatbot = chatbot_service.Chatbot()

def chat(query):
  if query:
    return chatbot.chat(query, vhost)

with st.sidebar:
  vhost = st.selectbox(
      'Qual ambiente você deseja monitorar?',
      ('aqila', 'aqila-hml')
    )

## Stremalit App
st.title('🕵️‍♀️ Alfredo`s AI')

if 'messages' not in st.session_state:
    st.session_state.messages = []
    st.session_state['messages'] = [{'role': 'assistant', 'content': '''
                            Olá, sou o Alfredo, sou um agente de monitaramento de sistemas. Como posso ajudar você?
                            Você pode me perguntar sobre os sistemas que monitoramos, como por exemplo:
                            - Quais são as coleções com erro?
                            - Quantas mensagens tem nas filas?
                            - Quais são as mensagens da fila X?
                           '''}]

for message in st.session_state.messages:
  with st.chat_message(message['role'], avatar=message['role'] == 'assistant' and '🕵️‍♀️' or '🧑‍💻'):    
    if isinstance(message['content'], list):
      json_data = json.dumps(message['content'], indent=2)
      st.code(json_data, language='json')
    elif isinstance(message['content'], pd.DataFrame):
      st.dataframe(message['content'])
    else:
      st.markdown(message['content'])

if prompt := st.chat_input('Como posso ajudá-lo?'):
  if not vhost:
    st.info('Por favor, informe o Ambiente')
    st.stop()

  st.session_state.messages.append({'role': 'user', 'content': prompt})

  with st.chat_message('user', avatar='🧑‍💻'):
    st.markdown(prompt)
  with st.chat_message('assistant', avatar='🕵️‍♀️'):
    with st.spinner('Consultando 🔍 ...'):
      message_place_holder = st.empty()
      responses = chat(prompt)

      if type(responses) == list:
        json_data = json.dumps(responses, indent=2)
        st.code(json_data, language='json')
      elif type(responses) == pd.DataFrame:
        st.dataframe(responses)
      else:
        st.markdown(responses)

  st.session_state.messages.append({'role': 'assistant', 'content': responses})
