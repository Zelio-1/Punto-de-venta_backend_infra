# Imagen base para python 3.13.7 y Flask 3.1.2
FROM python:3.13.7-slim

# Creando un directorio de trabajo para el proyecto
WORKDIR /usr/src/pos-app

# Dependencias del sistema para los paquetes psycopg2 y Flask-Bcrypt en el requirements.txt
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    libffi-dev \
    libssl-dev \
    libpq-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiando las dependencias del proyecto e instalando las dependencias sin guardar archivos temporales
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiando todo el codigo del proyecto
COPY . .

# Exponiendo el puerto que el backend usará 
EXPOSE 8080

# Comando para ejecutar el contenedor para que se inicie el backend de la aplicacion
CMD ["python", "app.py"]