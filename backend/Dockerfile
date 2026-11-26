FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
EXPOSE 8000
# Trust X-Forwarded-For from any peer: in the compose topology nginx is the
# only ingress and the API ports are not published, so the only peers are
# the nginx and API containers on the private compose network. Without this,
# uvicorn ignores the forwarded client IP and the rate limiter keys every
# request on the nginx container IP as one shared bucket.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
