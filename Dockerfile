FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY requirements-build.txt .

RUN pip install --no-cache-dir -r requirements-build.txt

COPY src/ ./src/
COPY static/ ./static/

COPY build.py .

# Minify the static assets into dist/; main.py serves dist/ when it exists.
RUN python build.py && pip uninstall -y rjsmin rcssmin

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
