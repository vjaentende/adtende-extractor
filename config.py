import os
from dotenv import load_dotenv

# En builds compilats (PyInstaller), les credencials van embegudes via _baked_creds.py
# que es genera en CI i mai es commiteja al repo.
try:
    from _baked_creds import BAKED_USERNAME, BAKED_PASSWORD
except ImportError:
    BAKED_USERNAME = BAKED_PASSWORD = None

load_dotenv()

BASE_URL = "https://intelek-api-pro-app.prenomics.com"
LOGIN_URL = f"{BASE_URL}/rest-auth/login/"

USERNAME = BAKED_USERNAME or os.getenv("ADTENDE_USERNAME")
PASSWORD = BAKED_PASSWORD or os.getenv("ADTENDE_PASSWORD")

ENDPOINTS = {
    "tickets_enriquits": "70c7001b-ba8a-413c-b5e8-4724e6d803bb",
    "tickets_oac360": "86503719-fb84-4daa-a12e-8c6322f19232",
    "tickets_oac360_social": "494167b6-7be0-41de-b7ae-2e09fc0c7b0f",
    "tickets_diba": "ec579db2-e6b9-4ae6-9a1c-f443199adae6",
    "tickets_centraleta": "6837932c-45d8-4e92-ada7-be306d942f79",
    "informe_clients_o360_social": "c6e06b86-0ae4-43d8-abb1-5db3653bb8ff",
    "informe_clients_o360": "d80ab1e1-3e51-46d9-9877-dad46bb94948",
}
