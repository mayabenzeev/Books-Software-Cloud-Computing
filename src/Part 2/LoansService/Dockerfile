FROM python:3.11-slim
WORKDIR /app

# Copy the app contents into the container at /app
COPY LoansService/LoansCollection.py .
COPY LoansService/LoansAPI.py .
COPY LoansService/run.py .
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# # Make port 80 available to the world outside this container
# EXPOSE 80

# Run the application when the container launches
CMD ["python3", "run.py"]
