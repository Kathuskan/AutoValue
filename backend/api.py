"""Serve the combined-data model and the local website."""
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator
from .predict import load_bundle, predict_car

@asynccontextmanager
async def lifespan(app):
    app.state.bundle=load_bundle()
    yield

app=FastAPI(title='AutoValue LK',lifespan=lifespan)
WEB=Path(__file__).resolve().parents[1]/'web'
app.mount('/web',StaticFiles(directory=WEB),name='web')

class CarRequest(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
    brand:str=Field(min_length=1,max_length=100)
    model_name:str=Field(min_length=1,max_length=150)
    yom:int=Field(ge=1886,le=2026)
    engine_cc:Optional[float]=Field(default=None,ge=0,le=20000)
    gear:str=Field(min_length=1,max_length=30)
    fuel_type:str=Field(min_length=1,max_length=30)
    millage:Optional[float]=Field(default=None,ge=0,le=3000000)
    condition:str=Field(default='USED',min_length=1,max_length=20)

    @field_validator('yom', 'engine_cc', 'millage', mode='before')
    @classmethod
    def reject_boolean_numbers(cls, value):
        if isinstance(value, bool):
            raise ValueError('Enter a number, not true or false.')
        return value

    @field_validator('brand','model_name','gear','fuel_type','condition')
    @classmethod
    def nonblank(cls,value):
        if not value.strip(): raise ValueError('Must not be blank.')
        return value.strip()

@app.get('/',include_in_schema=False)
def website(): return FileResponse(WEB/'index.html')

@app.get('/health')
def health(): return {'status':'ok','model':app.state.bundle['metadata']['metrics']['winner'],'workflow':'vehicle-price'}

@app.get('/metadata')
def metadata(): return app.state.bundle['metadata']

@app.post('/predict')
def predict(car:CarRequest):
    try: return predict_car(car.model_dump(),app.state.bundle)
    except ValueError as exc: raise HTTPException(status_code=422,detail=str(exc)) from exc
