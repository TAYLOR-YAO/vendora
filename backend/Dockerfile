FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# system deps (time zone only)
RUN apt-get update && apt-get install -y tzdata && rm -rf /var/lib/apt/lists/*

# install python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy app source into the image
COPY . .

# bake static files into the image (WhiteNoise will serve them)
ENV DJANGO_SETTINGS_MODULE=vendora_backend.settings.prod
ARG DJANGO_SECRET_KEY=dummy
ENV DJANGO_SECRET_KEY=$DJANGO_SECRET_KEY
RUN DJANGO_SETTINGS_MODULE=vendora_backend.settings.base python -m django collectstatic --noinput

EXPOSE 8000
CMD ["gunicorn","-b","0.0.0.0:8000","vendora_backend.wsgi:application"]
