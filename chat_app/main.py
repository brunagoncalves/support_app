from fastapi import FastAPI

app = FastAPI()


@app.get('/')
def app_home():
    return {'message': 'Welcome to the Chat App!'}
