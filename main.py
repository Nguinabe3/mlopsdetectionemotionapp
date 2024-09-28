from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
import pandas as pd
from transformers import pipeline
import logging
import io
from datetime import datetime, timedelta, timezone
from typing import Union
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
import jwt
# from jwt.exceptions import PyJWTError
from jwt import PyJWTError
# Set up logging
logging.basicConfig(level=logging.INFO)

# Load the emotion detection model
try:
    classifier = pipeline("text-classification", model="j-hartmann/emotion-english-distilroberta-base", top_k=None)
    logging.info("Model loaded successfully.")
except Exception as e:
    logging.error(f"Error loading model: {e}")



# JWT settings
SECRET_KEY = "1b09eae62fffc38eac635a40e90f68652ef34161ade629343429538b53a67344"  # Replace with your own secret key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# User database
users_db = {
    "admin": {"username": "admin", "password": pwd_context.hash("adminpass"), "role": "admin"},
    "user": {"username": "user", "password": pwd_context.hash("userpass"), "role": "user"},
}


# Helper functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def authenticate_user(username: str, password: str):
    user = users_db.get(username)
    if not user or not verify_password(password, user["password"]):
        return False
    return user


def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            )
        return username
    except PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )


class TextRequest(BaseModel):
    text: str

class MultiTextRequest(BaseModel):
    texts: list[str]

@app.get("/")
def root():
    return {"message": "Emotion detection API is running"}

# Prediction endpoint with authentication
@app.post("/predict/")
async def predict_emotion(request: TextRequest, token: str = Depends(oauth2_scheme)):
    if not request.text:
        raise HTTPException(status_code=400, detail="Text must not be empty")

    outputs = classifier(request.text)
    best_prediction = max(outputs[0], key=lambda x: x['score'])
    
    return {
        "emotion": best_prediction['label'],
        "score": best_prediction['score']
    }

# Prediction for multiple texts with authentication
@app.post("/predict-multiple/")
async def predict_multiple_emotions(request: MultiTextRequest, token: str = Depends(oauth2_scheme)):
    results = []
    for text in request.texts:
        outputs = classifier(text)
        best_prediction = max(outputs[0], key=lambda x: x['score'])
        results.append({
            "text": text,
            "emotion": best_prediction['label'],
            "score": best_prediction['score']
        })
    return results

# Prediction from CSV file with authentication
@app.post("/predict-csv/")
async def predict_emotion_csv(file: UploadFile = File(...), token: str = Depends(oauth2_scheme)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File type not supported. Please upload a CSV file.")

    try:
        # Read CSV file
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode('utf-8')))  # Read the CSV

        if 'text' not in df.columns:
            raise HTTPException(status_code=400, detail="CSV must contain a 'text' column.")

        results = []
        for _, row in df.iterrows():
            text = row['text']
            if not text:
                results.append({"text": text, "error": "Text must not be empty"})
                continue

            outputs = classifier(text)
            best_prediction = max(outputs[0], key=lambda x: x['score'])
            results.append({
                "text": text,
                "emotion": best_prediction['label'],
                "score": best_prediction['score']
            })

        return JSONResponse(content=results)

    except Exception as e:
            logging.error(f"Error processing the CSV file: {e}")  # Log the specific error
            raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")  # Return the error