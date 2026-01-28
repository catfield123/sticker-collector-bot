FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy shared modules
COPY shared/ /app/shared/

# Copy telegram bot files and install dependencies
COPY telegram_bot/requirements.txt /app/telegram_bot/
RUN uv pip install --system -r /app/telegram_bot/requirements.txt

COPY telegram_bot/ /app/telegram_bot/

# Set working directory to telegram_bot
WORKDIR /app/telegram_bot

# Run the bot
CMD ["python", "bot.py"]
