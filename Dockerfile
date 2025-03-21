FROM python:3.9-alpine

WORKDIR /app

# Instalar dependencias del sistema necesarias
RUN apk add --no-cache build-base libffi-dev

# Instalar dependencias Python
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    rm -rf /root/.cache/pip

# Copiar sólo los archivos necesarios
COPY app/main.py .

# Crear directorio para datos
RUN mkdir -p /data/input /data/output

# Volumen para persistir datos
VOLUME ["/data"]

# Comando por defecto
ENTRYPOINT ["python", "main.py"]   