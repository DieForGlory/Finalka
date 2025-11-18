# --- Этап 1: "Сборщик" (Builder) ---
# Используем образ Python, который включает инструменты для компиляции
FROM python:3.11-slim-bullseye AS builder

# 1. Устанавливаем системные зависимости, необходимые для СБОРКИ
# (компиляторы C, заголовки Python и т.д. для bcrypt, numpy, Levenshtein)
#
# --- ИСПРАВЛЕНИЕ: Меняем репозиторий apt на зеркало Yandex ---
# Это решает проблемы с 'Hash Sum mismatch'
RUN echo "deb http://mirror.yandex.ru/debian/ bullseye main" > /etc/apt/sources.list && \
    echo "deb http://mirror.yandex.ru/debian/ bullseye-updates main" >> /etc/apt/sources.list && \
    echo "deb http://mirror.yandex.ru/debian-security/ bullseye-security main" >> /etc/apt/sources.list && \
    apt-get \
        -o Acquire::ForceIPv4=true \
        -o Acquire::http::No-Cache=true \
        -o Acquire::http::Cache-Directives="no-cache, max-age=0, must-revalidate" \
        update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        python3-dev \
    && apt-get clean && \
       rm -rf /var/lib/apt/lists/*

# 2. Создаем виртуальное окружение
WORKDIR /opt/venv
RUN python -m venv .
ENV PATH="/opt/venv/bin:$PATH"

# 3. Устанавливаем зависимости Python
# Копируем только requirements.txt, чтобы Docker мог кэшировать этот слой
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# --- Этап 2: "Финальный" (Final) ---
# Начинаем с чистого, легкого образа
FROM python:3.11-slim-bullseye

# 1. Создаем пользователя без прав root для безопасности
RUN addgroup --system app && adduser --system --group app
USER app

# 2. Устанавливаем рабочую директорию
WORKDIR /app

# 3. Копируем ТОЛЬКО виртуальное окружение из "Сборщика"
COPY --from=builder /opt/venv /opt/venv

# 4. Копируем код приложения.
# (Убедитесь, что у вас есть .dockerignore, чтобы не скопировать venv, .git и т.д.)
COPY --chown=app:app . .

# 5. Устанавливаем переменные окружения
# Добавляем venv в PATH
ENV PATH="/opt/venv/bin:$PATH"
# Включает небуферизованный вывод, чтобы логи Gunicorn появлялись сразу
ENV PYTHONUNBUFFERED=1

# 6. Открываем порт, который будет слушать Gunicorn
EXPOSE 5000

# 7. Запускаем приложение (эта команда будет перезаписана 'command' из docker-compose.yml)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "run:app"]