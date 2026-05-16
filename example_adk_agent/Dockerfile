FROM python:3.11-slim

WORKDIR /app

# Instala o git para poder baixar do Github via pip
RUN apt-get update && apt-get install -y git

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código da aplicação
COPY main.py .
COPY agent.py .

# A porta padrão do Cloud Run é 8080
EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
