# --- Builder Stage ---
# This stage installs dependencies into a virtual environment.
FROM python:3.12-slim as builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Create a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# --- Runtime Stage ---
# This stage copies the installed dependencies and source code into a clean image.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy the virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create a non-root user to run the application
RUN addgroup --system django && adduser --system --ingroup django django

# Copy application source
COPY . .
RUN chown -R django:django /app

EXPOSE 8000

# Switch to the non-root user
USER django

CMD ["gunicorn","-b","0.0.0.0:8000","vendora_backend.wsgi:application"]
