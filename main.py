from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional
import sqlite3
from datetime import datetime
import re

app = FastAPI()
templates = Jinja2Templates(directory="templates")
EXPIRY_TIME_MINUTES = 1
iban_regex = r"^([A-Z]{2}[ \-]?[0-9]{2})(?=(?:[ \-]?[A-Z0-9]){9,30}$)((?:[ \-]?[A-Z0-9]{3,5}){2,7})([ \-]?[A-Z0-9]{1,3})?$"

class PaymentForm(BaseModel):
    name: Optional[str] = None
    account_number: str
    amount: float
    currency: str

class PaymentAttemptForm(BaseModel):
    payment_request_id: int
    name: Optional[str] = None
    payed_amount: float
    payer_account_number: str
    payment_currency: str 

def read_sql_file(file_path):
    with open(file_path, 'r') as file:
        sql = file.read()
        sql_commands = sql.split(';')
    return sql_commands

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    conn = sqlite3.connect('payments.db')
    cursor = conn.cursor()
    sql_statements = read_sql_file('payments.sql')
    for command in sql_statements:
        cursor.execute(command)
    conn.commit()
    conn.close()
    
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/payment_requests")

async def payment_request(data: Request):
    try:
        if data.headers.get("content-type") == "application/x-www-form-urlencoded":
            form_data = await data.form()
        elif data.headers.get("content-type") == "application/json":
            form_data = await data.json()
        else:
            return JSONResponse(content={"status": "Unsupported Media Type"}, status_code=415)
        data = PaymentForm(**form_data)
        if not re.match(iban_regex, data.account_number):
            return JSONResponse(content={"status": "Invalid IBAN format"}, status_code=400)
    except Exception as e:
        return JSONResponse(content={"status": "Invalid input", "error": str(e)}, status_code=400)
    try:
        
        conn = sqlite3.connect('payments.db')
        cursor = conn.cursor()
    
        request_time = datetime.now().timestamp()
        cursor.execute('''
        INSERT INTO payment_requests (requester_account_number, request_amount, currency, request_time, status)
        VALUES (?, ?, ?, ?, ?)
        ''', (data.account_number, data.amount, data.currency, request_time, 'pending'))
        try:
            cursor.execute('INSERT INTO persons (name, account_number) VALUES (?, ?)', (data.name, data.account_number))
        except: 
            cursor.execute('UPDATE persons SET name = ? WHERE account_number = ?', (data.name, data.account_number))
            
        cursor.execute('SELECT request_id FROM payment_requests WHERE requester_account_number = ? AND request_time = ?', (data.account_number, request_time))
        request_id = cursor.fetchone()[0]
        conn.commit()
        received = {"request_id": request_id, "name": data.name, "account_number": data.account_number , "amount": data.amount, "currency": data.currency,  "request_time" : request_time, "status": "pending"}
        return JSONResponse(content={"status": "Payment request received", "received": received
        }, status_code=200)
    except sqlite3.Error as e:
        return JSONResponse(content={"status": "Error", "error": str(e)}, status_code=500)    
    finally: 
        conn.close()


@app.post("/payment_attempts")
async def payment_attempts(data: Request):
    try:
        if data.headers.get("content-type") == "application/x-www-form-urlencoded":
            form_data = await data.form()
        elif data.headers.get("content-type") == "application/json":
            form_data = await data.json()
        else:
            return JSONResponse(content={"status": "Unsupported Media Type"}, status_code=415)
        
        data = PaymentAttemptForm(**form_data)
        if not re.match(iban_regex, data.payer_account_number):
            return JSONResponse(content={"status": "Invalid IBAN format"}, status_code=400)
    except Exception as e:
        return JSONResponse(content={"status": "Invalid input", "error": str(e)}, status_code=400)
    try:
        conn = sqlite3.connect('payments.db')
        cursor = conn.cursor()
        try:
                cursor.execute('INSERT INTO persons (name, account_number) VALUES (?, ?)', (data.name, data.payer_account_number))
        except: 
                cursor.execute('UPDATE persons SET name = ? WHERE account_number = ?', (data.name, data.payer_account_number))
        try: 
            cursor.execute('SELECT requester_account_number, request_amount,currency, request_time, status FROM payment_requests WHERE request_id = ?', (data.payment_request_id,))
            requester_account_number, request_amount, request_currency, request_time, status = cursor.fetchall()[0]
        except:
            return JSONResponse(content={"status": "Payment request not found"}, status_code=400)
        if status != 'pending':
            return JSONResponse(content={"status": "Payment request not pending"}, status_code=400)
        elif datetime.now().timestamp() > request_time + EXPIRY_TIME_MINUTES*60:
            cursor.execute('UPDATE payment_requests SET status = ? WHERE request_id = ?', ('expired', data.payment_request_id))
            conn.commit()
            return JSONResponse(content={"status": "Payment request expired"}, status_code=400)
        else:
            payment_time = datetime.now().timestamp()
            request_amount = float(request_amount)
            cursor.execute('SELECT conversion_rate FROM currency WHERE currency_name = ? ', (request_currency,)) 
            conversion_rate_request = float(cursor.fetchone()[0]) # usd to request_currency
            amount_in_usd = request_amount / conversion_rate_request

            cursor.execute('SELECT conversion_rate FROM currency WHERE currency_name = ? ', (data.payment_currency,)) 
            conversion_rate_payment = float(cursor.fetchone()[0]) # usd to payment_currency
            amount_in_payment_currency = amount_in_usd * conversion_rate_payment
            payed_amount = float(data.payed_amount)
            if (abs(payed_amount - amount_in_payment_currency)) > 0.01: # allow small rounding differences
                cursor.execute('UPDATE payment_requests SET status = ? WHERE request_id = ?', ('failed', data.payment_request_id))
                conn.commit()
                return JSONResponse(content={"status": "Incorrect payed amount"}, status_code=400)
            else:
                cursor.execute('UPDATE payment_requests SET status = ? WHERE request_id = ?', ('executed', data.payment_request_id))
                cursor.execute('''
                INSERT INTO payments (payment_amount, payment_time, payment_request_id, payer_account_number, currency)
                VALUES (?, ?, ?, ?, ?)
                ''', (payed_amount, payment_time, data.payment_request_id, data.payer_account_number, data.payment_currency))
                cursor.execute('SELECT name FROM persons WHERE account_number = ?', (data.payer_account_number,))
                requester_name = cursor.fetchone()[0]
                cursor.execute('SELECT payment_id FROM payments WHERE payment_request_id = ? AND payment_time = ?', (data.payment_request_id, payment_time))
                payment_id = cursor.fetchone()[0]
                received = {"payment_id": payment_id, "payer_name": data.name, "payed_amount": payed_amount, "payer_account_number": data.payer_account_number, "payment_currency": data.payment_currency, "payment_time": payment_time, "payment_request_id": data.payment_request_id, "requester_name": requester_name, "requester_account_number": requester_account_number, "request_amount": request_amount, "request_currency": request_currency, "request_time": request_time, "status": "executed"}
                conn.commit()
                return JSONResponse(content={"status": "Payment attempt succeeded", "received": received}, status_code=200)
                
    except sqlite3.Error as e:
        return JSONResponse(content={"status": "Error", "error": str(e)}, status_code=500)
    finally: 
        conn.close()

        
    
    

