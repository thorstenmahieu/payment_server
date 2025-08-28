from fastapi.testclient import TestClient
from fastapi import FastAPI, Request, Form
from pydantic import BaseModel
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from main import app

client = TestClient(app)

def test_payment_request():
    response = client.post("/payment_request", json={
        "name": "Thorsten",
        "account_number": "BE8425437531",
        "amount": 50,
        "currency": "USD"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["received"]["amount"] == 50
    assert data["received"]["currency"] == "USD"
