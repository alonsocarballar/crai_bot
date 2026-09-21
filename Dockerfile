FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias primero (aprovecha la cache de Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del proyecto
COPY . .

# El bot corre en bucle infinito con polling, no necesita exponer puertos
CMD ["python", "bot.py"]
