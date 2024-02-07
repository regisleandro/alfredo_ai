
FROM python:3.9-slim

LABEL name="alfredo-ai"
LABEL maintener="Regis Leandro Buske - regisleandro@gmail.com"

WORKDIR /app

RUN apt-get update && apt-get install -y \
  build-essential \
  curl \
  software-properties-common \
  git \
  && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/regisleandro/alfredo_ai.git .

RUN pip3 install -r requirements.txt

RUN useradd -u 1002 -ms /bin/bash user
RUN chown user:user -R /app
USER user

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]