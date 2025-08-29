from fastapi.testclient import TestClient
from fastapi import FastAPI, Request, Form
from pydantic import BaseModel
import sys, os
from time import sleep
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from main import app

client = TestClient(app)

def test_payment_request():
    json={
        "name": "Thorsten",
        "account_number": "BE8425437531",
        "amount": 50,
        "currency": "USD"
        }
    data_form_urlencoded = "name=Thorsten&account_number=BE8425437531&amount=50&currency=USD"
    response = client.post("/payment_requests", json=json )
    
    assert response.status_code == 200
    data = response.json()[0]
    print(data)
    assert data["received"]["amount"] == 50
    assert data["received"]["name"] == "Thorsten"
    assert data["received"]["currency"] == "USD"
    assert data["received"]["status"] == "pending"
    assert "request_id" in data["received"]

def test_payment_attempts():
    data = "name=Thorsten&account_number=BE8425437531&amount=50&currency=USD"
    # First, create a payment request to get a valid request_id
    json={
        "name": "Thorsten",
        "account_number": "BE8425437531",
        "amount": 50,
        "currency": "USD"
        }
    response = client.post("/payment_requests", json=json)
    assert response.status_code == 200
    request_id = response.json()[0]["received"]["request_id"]

    # Now, attempt to pay the request
    sleep(1)  # Ensure a slight delay to avoid timing issues
    response = client.post("/payment_attempts", json={
        "payment_request_id": request_id,
        "name": "Marcel",
        "payed_amount": 50,
        "payer_account_number": "BE1234567890",
        "payment_currency": "USD"
    })
    assert response.status_code == 200
    data = response.json()[0]
    assert data["status"] == "Payment attempt succeeded"
    assert data["received"]["payment_request_id"] == request_id
    assert data["received"]["payed_amount"] == 50
    assert data["received"]["payer_account_number"] == "BE1234567890"
    assert data["received"]["payment_currency"] == "USD"

    # A second attempt should fail since the request is already paid
    sleep(5)
    response = client.post("/payment_attempts", json={
        "payment_request_id": request_id,
        "name": "Mattias",
        "payed_amount": 50,
        "payer_account_number": "BE1234567899",
        "payment_currency": "USD"
    })
    assert response.status_code == 400
    data = response.json()
    assert data["status"] == "Payment request not pending"

    response = client.post("/payment_attempts", json={
        "payment_request_id": request_id,
        "payed_amount": 50,
        "payer_account_number": "BE1234567890",
        "payment_currency": "USD"
    })
    assert response.status_code == 400
    data = response.json()
    assert data["status"] == "Payment request not pending"

def test_expired_payment_request():
    # Create a payment request
    json={
        "name": "Thorsten",
        "account_number": "BE8425437531",
        "amount": 50,
        "currency": "USD"
        }
    response = client.post("/payment_requests", json=json)
    assert response.status_code == 200
    request_id = response.json()[0]["received"]["request_id"]
    sleep(61)  
    response = client.post("/payment_attempts", json={
        "payment_request_id": request_id,
        "payed_amount": 50,
        "payer_account_number": "BE1234567890",
        "payment_currency": "USD"
    })
    assert response.status_code == 400
    data = response.json()
    assert data["status"] == "Payment request expired"

def test_different_currency_payment():
    # Create a payment request in USD
    json={
        "name": "Alice",
        "account_number": "BE9988776655",
        "amount": 100,
        "currency": "USD"   
        }
    response = client.post("/payment_requests", json=json)
    assert response.status_code == 200
    request_id = response.json()[0]["received"]["request_id"]
    # Attempt to pay the request in EUR
    response = client.post("/payment_attempts", json={
        "payment_request_id": request_id,
        "payed_amount": 85,  # 1 USD = 0.85 EUR
        "payer_account_number": "BE5544332211",
        "payment_currency": "EUR"
    })
    assert response.status_code == 200
    data = response.json()[0]
    assert data["status"] == "Payment attempt succeeded"
    assert data["received"]["payment_request_id"] == request_id
    assert data["received"]["payed_amount"] == 85
    assert data["received"]["payer_account_number"] == "BE5544332211"
    assert data["received"]["payment_currency"] == "EUR"

def test_incorrect_amount_payment():
    # Create a payment request in USD
    json={
        "name": "Bob",
        "account_number": "BE1122334455",
        "amount": 200,
        "currency": "USD"   
        }
    response = client.post("/payment_requests", json=json)
    assert response.status_code == 200
    request_id = response.json()[0]["received"]["request_id"]
    # Attempt to pay the request with an incorrect amount
    response = client.post("/payment_attempts", json={
        "payment_request_id": request_id,
        "payed_amount": 190,  # Incorrect amount
        "payer_account_number": "BE6677889900",
        "payment_currency": "USD"
    })
    assert response.status_code == 400
    data = response.json()
    assert data["status"] == "Incorrect payed amount"

def test_payment_request_not_found():
    response = client.post("/payment_attempts", json={
        "payment_request_id": 9999,  # Non-existent request_id
        "payed_amount": 50,
        "payer_account_number": "BE1234567890",
        "payment_currency": "USD"
    })
    assert response.status_code == 400
    data = response.json()
    assert data["status"] == "Payment request not found"
test_payment_request()