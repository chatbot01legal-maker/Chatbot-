# Usar una imagen base oficial de Python (ligera)
FROM python:3.11-slim

# Establecer la carpeta de trabajo
WORKDIR /app

# Copiar el archivo de requisitos e instalar las dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código de la aplicación
COPY . .

# Comando de ejecución del servidor
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
