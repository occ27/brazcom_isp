from app.mikrotik.controller import MikrotikController
import logging
import sys

logging.basicConfig(level=logging.DEBUG)

mk = MikrotikController('192.168.18.101', 'admin', 'gruta765')
mk.connect()
print("Connected")

try:
    if mk._api:
        resource = mk._api.get_resource('ip/firewall/address-list')
        print("Using routeros_api")
        try:
            res = resource.add(**{'list': 'pg_corte', 'address': '192.168.10.20'})
            print("Add result:", res)
        except Exception as e:
            print("Add error:", e)
    elif mk._librouteros_api:
        print("Using librouteros")
        resource = mk._librouteros_api.path('ip/firewall/address-list')
        res = resource.add(list='pg_corte', address='192.168.10.20')
        print("Add result:", res)

except Exception as e:
    print("General Error:", e)

mk.close()
