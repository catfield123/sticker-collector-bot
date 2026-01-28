FROM python:3.11-slim

WORKDIR /app

RUN pip install uv

# Copy shared modules
COPY shared/ /app/shared/

# Copy db_worker files and install dependencies
COPY db_worker/requirements.txt /app/db_worker/
RUN uv pip install --system -r /app/db_worker/requirements.txt

COPY db_worker/ /app/db_worker/

# Set working directory to db_worker
WORKDIR /app/db_worker

# Run the worker
CMD ["python", "worker.py"]
