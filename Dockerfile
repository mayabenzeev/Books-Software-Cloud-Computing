FROM python:3.11-slim
WORKDIR /app
COPY ./src/ /app
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 8000
#CMD ["python3", "BooksAPI.py"] #start-up cmd

ENV FLASK_APP=BooksAPI.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV PORT=8000

CMD flask run --host=0.0.0.0 --port=$PORT
