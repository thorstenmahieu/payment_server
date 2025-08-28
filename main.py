from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, Annotated
import sqlite3
from datetime import datetime, timedelta

app = FastAPI()
templates = Jinja2Templates(directory="templates")
EXPIRY_TIME_MINUTES = 30
class PaymentForm(BaseModel):
    name: str
    account_number: str
    amount: float
    currency: str

class PaymentAttemptForm(BaseModel):
    payment_id: int
    status: str
    attempt_time: Optional[datetime] = None

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

@app.post("/payment_request")
async def payment_request(data: Annotated[PaymentForm, Form()]):
    conn = sqlite3.connect('payments.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
        INSERT INTO payment_requests (requester_account_number, request_amount, currency, request_time, status)
        VALUES (?, ?, ?, ?, ?)
        ''', (data.name, data.account_number, data.amount, data.currency, datetime.now(), 'pending'))
        cursor.execute('INSERT INTO persons (name, account_number) VALUES (?, ?)', (data.name, data.account_number))
        conn.commit()
        return {"status": "Payment request received", "received": data
        }, 200
    except sqlite3.Error as e:
        return {"status": "Error", "error": str(e)}, 500    
    finally: 
        conn.close()



@app.post("/payment_attempts")
async def payment_attempts(payment_request_id: int, payed_amount:float, payer_account_number: str, payment_currency: str ):
    conn = sqlite3.connect('payments.db')
    cursor = conn.cursor()
    cursor.execute('SELECT requester_account_number,request_amount,currency,request_time,status FROM payment_requests WHERE request_id = ?', (payment_request_id,))
    requester_account_number,request_amount,request_currency,request_time,status = cursor.fetchall()
    if status != 'pending':
        return {"status": "Payment request not pending"}, 400
    elif datetime.now() > request_time + timedelta(minutes=EXPIRY_TIME_MINUTES):
        cursor.execute('UPDATE payment_requests SET status = ? WHERE request_id = ?', ('expired', payment_request_id))
        conn.commit()
        return {"status": "Payment request expired"}, 400
    else:
        request_amount = float(request_amount)
        cursor.execute('SELECT conversion_rate FROM currency WHERE currency = ? ', (request_currency,)) 
        conversion_rate_request = float(cursor.fetchone()) # usd to request_currency
        amount_in_usd = request_amount / conversion_rate_request

        cursor.execute('SELECT conversion_rate FROM currency WHERE currency = ? ', (payment_currency,)) 
        conversion_rate_payment = float(cursor.fetchone()) # usd to payment_currency
        amount_in_payment_currency = amount_in_usd * conversion_rate_payment
        payed_amount = float(payed_amount)
        if abs(payed_amount) - abs(amount_in_payment_currency) > 0.01: # allow small rounding differences
            return {"status": "Incorrect payed amount"}, 400
        else:
            cursor.execute('''
            INSERT INTO payments (payment_amount, payment_time, payment_request_id, payer_account_number, currency, status)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (payed_amount, datetime.now(), payment_request_id, payer_account_number, payment_currency, 'executed'))
            conn.commit()
        
    
    return {"status": "Payment attempt recorded"}

