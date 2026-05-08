from app.mikrotik.controller import MikrotikController
import logging
logging.basicConfig(level=logging.DEBUG)

mk = MikrotikController('192.168.18.101', 'admin', 'gruta765')
mk.connect()
print("Connected")
try:
    res = mk.add_to_address_list('192.168.10.20', 'pg_corte', 'Teste bloqueio')
    print("Result:", res)
except Exception as e:
    print("Error:", e)
mk.close()
