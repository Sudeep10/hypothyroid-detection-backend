import datetime
import pickle
from hashlib import sha512

import uvicorn
from bson import ObjectId, json_util
from fastapi import FastAPI, Request, Response
from pydantic import BaseModel
from pymongo import MongoClient

client = MongoClient("localhost", 27017)

app = FastAPI()
model = pickle.load(open("thyroid_model.pkl", "rb"))


class User(BaseModel):
    name: str = ""
    email: str = ""
    password: str = ""
    data: list = []


db = client["hypothyroid"]
userDB = db["user"]
historyDB = db["history"]


@app.post("/assessment")
def assessment(response: Response, user: User):
    userBson = userDB.find_one(
        {
            "email": user.email,
            "password": sha512(user.password.encode()).hexdigest(),
        }
    )
    if userBson is not None:
        print(user.data)
        result = model.predict([user.data])
        print(result[0])
        historyDB.insert_one(
            {
                "user_id": userBson["_id"],
                "data": user.data,
                "result": result[0],
                "date": datetime.datetime.now(tz=datetime.timezone.utc),
            }
        )
        return result[0]
    else:
        response.status_code = 403
        return "Invalid Credentials"


@app.get("/history")
def history(response: Response, request: Request):
    userBson = userDB.find_one(
        {
            "email": request.headers.get("email"),
            "password": sha512(request.headers.get("password").encode()).hexdigest(),
        }
    )
    if userBson is not None:
        historyBson = historyDB.find({"user_id": ObjectId(userBson["_id"])})
        historyJson = []
        for i in historyBson:
            historyJson.append(i)
        return json_util.dumps(historyJson)
    else:
        response.status_code = 403
        return "Invalid Credentials"


@app.post("/login")
def login(user: User, response: Response):
    userBson = userDB.find_one(
        {"email": user.email, "password": sha512(user.password.encode()).hexdigest()}
    )
    if userBson is not None:
        return "OK"
    else:
        response.status_code = 403
        return "Not registered"


@app.post("/signup")
def signup(user: User, response: Response):
    userBson = userDB.find_one({"email": user.email})
    print(user)
    if userBson is None:
        userDB.insert_one(
            {
                "name": user.name,
                "email": user.email,
                "password": sha512(user.password.encode()).hexdigest(),
            }
        )
        return "OK"
    else:
        response.status_code = 403
        return "User already registered"


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
