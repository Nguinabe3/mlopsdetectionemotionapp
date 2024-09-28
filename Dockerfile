FROM python:3.12

# Step 2: Set the working directory in the container
WORKDIR /code

# Step 3: Copy the requirements.txt file to the working directory
COPY ./requirements.txt /code/requirements.txt

# Step 4: Install the Python dependencies specified in requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Step 5: Copy the entire application code to the working directory
COPY ./main.py /code/main.py
COPY ./app.py /code/app.py
 # Assuming your main.py is in the 'app' directory

# Expose the ports for FastAPI (8000) and Streamlit (8501)
EXPOSE 8000
EXPOSE 8501

# Set environment variables
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Command to start FastAPI and Streamlit
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port 8000 & sleep 5 && streamlit run app.py --server.port 8501 --server.address 0.0.0.0"]