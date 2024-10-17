# Используем официальный образ Python
FROM python:3.10.12

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем только файл зависимостей
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальные файлы проекта
COPY . .

# Запускаем бота
CMD ["python", "memehub.py"]
