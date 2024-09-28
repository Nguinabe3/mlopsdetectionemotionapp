import streamlit as st
import requests
import pandas as pd

# Streamlit app layout
st.title("Emotion Detection App")

# Define the FastAPI backend URL
# Update this URL to match the FastAPI container name
fastapi_url = "http://localhost:8000"# fastapi_url = "http://fastapi:8000"  # Update with your FastAPI server URL if different

# Sidebar options for different functionalities
option = st.sidebar.selectbox("Choose an option", ["Single Text Prediction", "Multiple Texts Prediction", "Predict from CSV"])

# Function to get access token
def get_access_token(username, password):
    response = requests.post(f"{fastapi_url}/token", data={"username": username, "password": password})
    if response.status_code == 200:
        return response.json().get("access_token")
    else:
        st.error("Authentication failed. Please check your credentials.")
        return None

# Authenticate user
st.sidebar.header("Authentication")
username = st.sidebar.text_input("Username")
password = st.sidebar.text_input("Password", type="password")

if st.sidebar.button("Login"):
    token = get_access_token(username, password)
    if token:
        st.session_state.token = token  # Store token in session state
        st.sidebar.success("Login successful. Please authorize to use the model.")

# Authorize user to use the model
if "token" in st.session_state:
    st.sidebar.header("Authorization")
    st.sidebar.text_area("Access Token", st.session_state.token, height=100)
    authorized = st.sidebar.checkbox("Authorize", value=True)

    if authorized:
        headers = {"Authorization": f"Bearer {st.session_state.token}"}

        if option == "Single Text Prediction":
            st.header("Single Text Emotion Prediction")

            # Input text
            input_text = st.text_area("Enter text:", "")

            # Predict emotion
            if st.button("Predict"):
                if input_text.strip():
                    response = requests.post(f"{fastapi_url}/predict/", json={"text": input_text}, headers=headers)
                    if response.status_code == 200:
                        result = response.json()
                        st.write(f"Emotion: {result['emotion']}")
                        st.write(f"Score: {result['score']}")
                    else:
                        st.error(f"Error: {response.json()['detail']}")
                else:
                    st.error("Text must not be empty.")

        elif option == "Multiple Texts Prediction":
            st.header("Multiple Texts Emotion Prediction")

            # Input multiple texts
            input_texts = st.text_area("Enter multiple texts (one per line):", "")

            # Predict emotions for multiple texts
            if st.button("Predict"):
                texts = [text.strip() for text in input_texts.split("\n") if text.strip()]
                if texts:
                    response = requests.post(f"{fastapi_url}/predict-multiple/", json={"texts": texts}, headers=headers)
                    if response.status_code == 200:
                        results = response.json()
                        results_df = pd.DataFrame(results)
                        st.write(results_df)
                    else:
                        st.error(f"Error: {response.json()['detail']}")
                else:
                    st.error("Please enter at least one text.")

        elif option == "Predict from CSV":
            st.header("Predict Emotions from CSV File")

            # File upload
            uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

            if uploaded_file:
                try:
                    # Read the CSV file into a DataFrame
                    df = pd.read_csv(uploaded_file)

                    if 'text' in df.columns:
                        csv_data = df.to_csv(index=False)
                        files = {'file': ('uploaded_file.csv', csv_data)}

                        # Send the file to the FastAPI backend
                        response = requests.post(f"{fastapi_url}/predict-csv/", files=files, headers=headers)
                        if response.status_code == 200:
                            results = response.json()
                            results_df = pd.DataFrame(results)
                            st.write(results_df)
                        else:
                            st.error(f"Error: {response.json()['detail']}")
                    else:
                        st.error("CSV must contain a 'text' column.")
                except Exception as e:
                    st.error(f"Internal Server Error: {str(e)}")

else:
    st.warning("Please log in and authorize to access the prediction functionalities.")
