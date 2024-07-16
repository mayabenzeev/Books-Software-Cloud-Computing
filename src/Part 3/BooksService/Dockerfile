FROM python:3.11-slim
WORKDIR /app

# Copy the app contents into the container at /app
COPY BooksService/BooksCollection.py .
COPY BooksService/BooksAPI.py .
COPY BooksService/run.py .
COPY requirements.txt .
COPY tests/ tests/

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Run the application when the container launches
CMD ["python3", "run.py"]
