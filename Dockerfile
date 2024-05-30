FROM python:latest

LABEL name="alfredo-ai"
LABEL maintainer="Regis Leandro Buske - regisleandro@gmail.com"

WORKDIR /app

RUN apt-get update && apt-get install -y \
  build-essential \
  curl \
  software-properties-common \
  git \
  && curl -fsSL https://deb.nodesource.com/setup_21.x | bash - \
  && apt-get install -y nodejs \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/regisleandro/alfredo_ai.git .

RUN pip3 install -r requirements.txt

# Set up Node.js environment
WORKDIR /app/alfredo_rocket
RUN npm install

WORKDIR /app

# Create a non-root user and change ownership of the /app directory
RUN useradd -u 1002 -ms /bin/bash user
RUN chown user:user -R /app

# Switch to the non-root user
USER user

# Expose the port
EXPOSE 8501

# Healthcheck to ensure the service is running
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Start the services using a shell script to run both FastAPI and the Node.js server
COPY start_services.sh /app/start_services.sh
RUN chmod +x /app/start_services.sh

ENTRYPOINT ["/app/start_services.sh"]
