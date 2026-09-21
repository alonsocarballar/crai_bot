FROM python:3.11-slim

# Evita que Python bufferee stdout/stderr — imprescindible para ver logs en tiempo real en Docker/Portainer
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instalar dependencias primero (aprovecha la cache de Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del proyecto
COPY . .

# El bot corre en bucle infinito con polling, no necesita exponer puertos
CMD ["python", "-u", "bot.py"]
