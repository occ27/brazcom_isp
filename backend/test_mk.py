import logging
import sys

logging.basicConfig(level=logging.DEBUG)

host = "138.122.54.235"
port = 8728
user = "admin"
password = ""

print(f"\nTesting routeros_api on port {port}...")
try:
    import routeros_api
    pool = routeros_api.RouterOsApiPool(host, username=user, password=password, port=port)
    api = pool.get_api()
    print("routeros_api connected!")
except Exception as e:
    print(f"routeros_api error: {type(e).__name__} - {e}")
