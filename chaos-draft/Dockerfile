# Chaos Draft, for any host that runs a container.
#
# Works unchanged on Hugging Face Spaces, Render, Fly, Railway or your own box.
# The join QR is built from the incoming request's Host header, so it is correct
# wherever this ends up without any configuration.

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Hosts hand the port over in $PORT. 7860 is the Hugging Face Spaces default.
ENV PORT=7860
EXPOSE 7860

CMD ["python", "server.py", "--host", "0.0.0.0"]
