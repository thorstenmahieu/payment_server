# Payment server

## Installatie

```git clone https://github.com/thorstenmahieu/payment_server.git```
```bash
cd payment_server
```
### Maak een virtual environment
```bash
python -m venv myvenv
```
### Activeer environment
macOS/Linux:
```bash
source myvenv/bin/activate
```
Windows:
```bash
myvenv\Scripts\activate
```

 ### Installeer de nodige packages
```bash
pip install -r requirements.txt
```

 ### Om te testen
Run het programma met
```bash
fastapi dev main.py
```
unit-tests uitvoeren met
```bash
pytest
```

