#!/usr/bin/env python3
from app.mikrotik.controller import MikrotikController
mc = MikrotikController('127.0.0.1','admin','password')
print('has get_connection_status:', hasattr(mc, 'get_connection_status'))
print('status before connect:', mc.get_connection_status())
try:
    mc.connect()
    print('status after connect:', mc.get_connection_status())
except Exception as e:
    print('connect() raised:', e)
