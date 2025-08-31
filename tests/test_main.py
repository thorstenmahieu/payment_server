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
        "account_number": "BE84 2543 7531 1863",
        "amount": 50,
        "currency": "USD"
        }
    data_form_urlencoded = "name=Thorsten&account_number=BE842 5437 5312 7345&amount=50&currency=USD"
    response = client.post("/payment_requests", json=json )
    assert response.status_code == 200
    data = response.json()
    assert data["received"]["amount"] == 50
    assert data["received"]["name"] == "Thorsten"
    assert data["received"]["currency"] == "USD"
    assert data["received"]["status"] == "pending"    
    assert "request_id" in data["received"]



def test_type_checking_payment_request():
    json={
        "name": "Thorsten",
        "account_number": "BE84 2543 7531 1863",
        "amount": "vijftig", # foutief, moet float zijn
        "currency": "USD"
        }
    response = client.post("/payment_requests", json=json )
    assert response.status_code == 400
    response = client.post("/payment_requests", json={
        "name": 15, # foutief, moet string zijn
        "account_number": "BE84 2543 7531 1863",
        "amount": 50,
        "currency": "USD"
        } )
    assert response.status_code == 400
    response = client.post("/payment_requests", json={
        "name": "Thorsten",
        "account_number": 257.1, # foutief, moet string zijn
        "amount": 50,
        "currency": "USD"
        } )
    assert response.status_code == 400
    response = client.post("/payment_requests", json={
        "name": "Thorsten",
        "account_number": "BE84 2543 7531 1863",
        "amount": 50,
        "currency": 123
        } )
    assert response.status_code == 400
    response = client.post("/payment_requests", json={
        # name ontbreekt, is optioneel
        # account_number ontbreekt, is verplicht
        "amount": 50,
        "currency": 123
        } )
    assert response.status_code == 400

def test_payment_attempts():
    # Eerst een betalingsverzoek maken om aan een geldige request_id te komen
    json={
        "name": "Thorsten",
        "account_number": "BE84 2543 7531 8634",
        "amount": 50,
        "currency": "USD"
        }
    response = client.post("/payment_requests", json=json)
    assert response.status_code == 200
    request_id = response.json()["received"]["request_id"]

    # Betaling uitvoeren
    sleep(0.1)
    response = client.post("/payment_attempts", json={
        "payment_request_id": request_id,
        "name": "Marcel",
        "payed_amount": 50,
        "payer_account_number": "BE81 2345 6789 0011",
        "payment_currency": "USD"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Payment attempt succeeded"
    assert data["received"]["payment_request_id"] == request_id
    assert data["received"]["payed_amount"] == 50
    assert data["received"]["payer_account_number"] == "BE81 2345 6789 0011"
    assert data["received"]["payment_currency"] == "USD"

    # Proberen om nog een keer te betalen op hetzelfde verzoek
    sleep(1)
    response = client.post("/payment_attempts", json={
        "payment_request_id": request_id,
        "name": "Mattias",
        "payed_amount": 50,
        "payer_account_number": "BE84 1234 56789 9876",
        "payment_currency": "USD"
    })
    assert response.status_code == 400
    data = response.json()
    assert data["status"] == "Payment request expired"

def test_unsupported_currency_payment_attempt():
    json={
        "name": "Thorsten",
        "account_number": "BE84 2543 7531 4567",
        "amount": 50,
        "currency": "EUR" 
        }
    response = client.post("/payment_requests", json=json)
    assert response.status_code == 200
    request_id = response.json()["received"]["request_id"]

    # Betaling uitvoeren
    sleep(0.1)
    response = client.post("/payment_attempts", json={
        "payment_request_id": request_id,
        "name": "Marcel",
        "payed_amount": 50,
        "payer_account_number": "BE81 2345 6789 0011",
        "payment_currency": "HHR"
    })
    assert response.status_code == 422
    data = response.json()
    assert data["status"] == "Unsupported currency"

def test_type_checking_payment_attempt():
    # Eerst een betalingsverzoek maken om aan een geldige request_id te komen
    json={
        "name": "Thorsten",
        "account_number": "BE84 2543 7531 1863",
        "amount": 50,
        "currency": "USD"
        }
    response = client.post("/payment_requests", json=json)
    assert response.status_code == 200
    request_id = response.json()["received"]["request_id"]
   
    response = client.post("/payment_attempts", json={
        "payment_request_id": request_id,
        "name": "Marcel",
        "payed_amount": "vijftig", # string in plaats van float
        "payer_account_number": "BE81 2345 6789 0011",
        "payment_currency": "USD"
    })
    assert response.status_code == 400
    data = response.json()
    assert data["status"] == "Invalid input"
    response = client.post("/payment_attempts", json={
        "payment_request_id": "een", # string in plaats van int
        "name": "Marcel",
        "payed_amount": 50,
        "payer_account_number": "BE81 2345 6789 0011",
        "payment_currency": "USD"
    })
    assert response.status_code == 400
    data = response.json()
    assert data["status"] == "Invalid input"
    response = client.post("/payment_attempts", json={
        "payment_request_id": request_id,
        "name": 15, # int in plaats van string
        "payed_amount": 50,
        "payer_account_number": "BE81 2345 6789 0011",
        "payment_currency": "USD"
    })
    assert response.status_code == 400
    data = response.json()
    assert data["status"] == "Invalid input"
    response = client.post("/payment_attempts", json={
        "payment_request_id": request_id,
        "name": "Marcel",
        "payed_amount": 50,
        "payer_account_number": 257.1, # float in plaats van string
        "payment_currency": "USD"
    })
    assert response.status_code == 400
    data = response.json()
    assert data["status"] == "Invalid input"
    response = client.post("/payment_attempts", json={
        "payment_request_id": request_id,
        "name": "Marcel",
        "payed_amount": 50,
        "payer_account_number": "BE81 2345 6789 0011",
        "payment_currency": 123 # int in plaats van string
    })
    assert response.status_code == 400
    data = response.json()
    assert data["status"] == "Invalid input"

    response = client.post("/payment_attempts", json={
        # payment_request_id ontbreekt, is verplicht
        "name": "Marcel",
        "payed_amount": 50,
        "payer_account_number": "BE81 2345 6789 0011",
        "payment_currency": "USD"
    })
    assert response.status_code == 400
    data = response.json()
    assert data["status"] == "Invalid input"

def test_expired_payment_request():
    # Maak een betalingsverzoek
    json={
        "name": "Thorsten",
        "account_number": "BE84 2543 7531 4567",
        "amount": 50,
        "currency": "USD"
        }
    response = client.post("/payment_requests", json=json)
    assert response.status_code == 200

    request_id = response.json()["received"]["request_id"]
    #sleep(61)  # Wacht tot het verzoek is verlopen (EXPIRY_TIME_MINUTES is 1 minuut)
    response = client.post("/payment_attempts", json={
        "payment_request_id": 1,
        "payed_amount": 50,
        "payer_account_number": "BE12 3456 7890 1234",
        "payment_currency": "USD"
    })
    assert response.status_code == 400
    data = response.json()
    assert data["status"] == "Payment request expired"

def test_different_currency_payment():
    # Maak een betalingsverzoek in USD
    json={
        "name": "Maarten",
        "account_number": "BE99 8877 6655 4433",
        "amount": 100,
        "currency": "USD"   
        }
    response = client.post("/payment_requests", json=json)
    assert response.status_code == 200
    request_id = response.json()["received"]["request_id"]
    # Probeer in EUR te betalen
    response = client.post("/payment_attempts", json={
        "payment_request_id": request_id,
        "payed_amount": 85,  # 1 USD = 0.85 EUR
        "payer_account_number": "BE55 4433 2211 0011",
        "payment_currency": "EUR"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Payment attempt succeeded"
    assert data["received"]["payment_request_id"] == request_id
    assert data["received"]["payed_amount"] == 85
    assert data["received"]["payer_account_number"] == "BE55 4433 2211 0011"
    assert data["received"]["payment_currency"] == "EUR"

def test_incorrect_amount_payment():
    # maak een betalingsverzoek
    json={
        "name": "Jan",
        "account_number": "BE11 2233 4455 6677",
        "amount": 200,
        "currency": "USD"   
        }
    response = client.post("/payment_requests", json=json)
    assert response.status_code == 200
    request_id = response.json()["received"]["request_id"]
    # Probeer een verkeerd bedrag te betalen
    response = client.post("/payment_attempts", json={
        "payment_request_id": request_id,
        "payed_amount": 190,  # Incorrect
        "payer_account_number": "BE66 7788 9900 1122",
        "payment_currency": "USD"
    })
    assert response.status_code == 400
    data = response.json()
    assert data["status"] == "Incorrect payed amount"

def test_payment_request_not_found():
    response = client.post("/payment_attempts", json={
        "payment_request_id": 9999,  # onbekend ID
        "payed_amount": 50,
        "payer_account_number": "BE12 3456 7890 1234",
        "payment_currency": "USD"
    })
    assert response.status_code == 400
    data = response.json()
    assert data["status"] == "Payment request not found"

def test_invalid_iban_format():
    json={
        "name": "Dirk",
        "account_number": "vdiydytk575", # ongeldig IBAN
        "amount": 50,
        "currency": "USD"
        }
    response = client.post("/payment_requests", json=json)
    assert response.status_code == 422
    data = response.json()
    assert data["status"] == "Invalid IBAN format"    

    # Eerst een geldig betalingsverzoek aanmaken
    json={
        "name": "Thorsten",
        "account_number": "BE84 2543 7531 8634",
        "amount": 50,
        "currency": "USD"
        }
    response = client.post("/payment_requests", json=json)
    assert response.status_code == 200
    request_id = response.json()["received"]["request_id"]

    # Betaling uitvoeren met ongeldig IBAN
    sleep(0.1)
    response = client.post("/payment_attempts", json={
        "payment_request_id": request_id,
        "name": "Marcel",
        "payed_amount": 50,
        "payer_account_number": "1B45428",
        "payment_currency": "USD"
    })
    assert response.status_code == 422
    data = response.json()
    assert data["status"] == "Invalid IBAN format"    