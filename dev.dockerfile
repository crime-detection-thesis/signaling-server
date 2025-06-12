FROM python:3.13

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY . .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

EXPOSE 8002

CMD ["uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8002"]
