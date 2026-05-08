import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class MaintenanceResponse(BaseModel):
    success: bool = False
    error_code: int = 2

HOST = '0.0.0.0'
PORT = 80


@app.get('/favicon.ico')
def favicon():
    return ''


@app.get('/{p:path}', response_model=MaintenanceResponse)
def hello(p):
    return MaintenanceResponse()


if __name__ == '__main__':
    uvicorn.run(app, host=HOST, port=PORT)
