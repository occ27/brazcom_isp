from app.mikrotik.controller import MikrotikController
import librouteros
import logging

logging.basicConfig(level=logging.DEBUG)

api = librouteros.connect('192.168.18.101', 'admin', 'gruta765')
print("Connected via librouteros")

try:
    path = api.path('ip', 'firewall', 'address-list')
    res = path.add(list='pg_corte', address='192.168.10.20')
    print("Add result:", res)
except Exception as e:
    print("Error:", e)
api.close()
