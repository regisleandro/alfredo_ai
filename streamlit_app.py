import streamlit as st
import json
import pandas as pd
import uuid

import pkg.chatbot as chatbot_service

# Initialize chatbot in session state if it doesn't exist
if 'chatbot' not in st.session_state:
    st.session_state.chatbot = chatbot_service.Chatbot()

st.set_page_config(page_title='Alfredo', page_icon='🕵️‍♀️', initial_sidebar_state='auto')

# Generate a unique user ID for this session if it doesn't exist
if 'user_id' not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())

def chat(query):
    if query:
        # Remove file_content parameter
        return st.session_state.chatbot.chat(query, vhost, user_id=st.session_state.user_id)

with st.sidebar:
    vhost = st.selectbox(
        'Qual ambiente você deseja monitorar?',
        ('aqila', 'aqila-hml')
    )
  
    # Display user ID in sidebar (can be commented out in production)
    st.text(f"Session ID: {st.session_state.user_id[:8]}...")
  
    # Add a button to clear chat history (for debugging)
    if st.button("Clear Chat History"):
        if st.session_state.user_id in st.session_state.chatbot.user_chat_histories:
            st.session_state.chatbot.user_chat_histories[st.session_state.user_id] = []
            st.success("Chat history cleared!")

## Streamlit App
st.title('🕵️‍♀️ Alfredo`s AI')

if 'messages' not in st.session_state:
    st.session_state.messages = []
    st.session_state['messages'] = [{'role': 'assistant', 'content': '''
                            Olá, sou o Alfredo, sou um agente de monitaramento de sistemas.
                            Você pode me perguntar sobre os sistemas que monitoramos, como por exemplo:
                            - Quais são as coleções com erro?
                            - Quantas mensagens existem nas filas?
                            - Quais são as mensagens da fila X?
                            - Quais clientes possuem fotos com erro/pendentes? 
                            - Leia X mensagens da fila Y
                            - Leia X mensagens da fila Y filtrando pelo cliente Z
                            - Resuma X mensagens da fila Y   
                            - Liste os commits do repositorio X filtrando por label (nome da tarefa) e status (open, closed, all)
                            - Qual comando usar para fazer X?
                            - Sobre a tarefa 123, quais os principais detalhes?         
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

# Place chat input outside of any restricted containers
prompt = st.chat_input('Como posso ajudá-lo?')

if prompt:
    if not vhost:
        st.info('Por favor, informe o Ambiente')
        st.stop()

    st.session_state.messages.append({'role': 'user', 'content': prompt})

    with st.chat_message('user', avatar='🧑‍💻'):
        st.markdown(prompt)
    with st.chat_message('assistant', avatar='🕵️‍♀️'):
        with st.spinner('Consultando 🔍 ...'):
            message_place_holder = st.empty()
            # Remove file_content parameter from chat call
            responses = chat(prompt)

            if type(responses) == list:
                json_data = json.dumps(responses, indent=2)
                st.code(json_data, language='json')
            elif type(responses) == pd.DataFrame:
                st.dataframe(responses)
            else:
                st.markdown(responses)

    st.session_state.messages.append({'role': 'assistant', 'content': responses})
