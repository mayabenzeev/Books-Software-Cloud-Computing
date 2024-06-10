FROM python:3.11-slim
WORKDIR /app

# Copy the app contents into the container at /app
COPY ./LoansCollection.py .
COPY ./LoansAPI.py .
COPY ./run.py .
COPY ../common/CreateMongoServer.py .
COPY ../common/requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 5002 available to the world outside this container
EXPOSE 5002

# Run the application when the container launches
CMD ["python3", "run.py"]
