#!/usr/bin/env python3
"""
Testando o fluxo de fallback do add_pppoe_server:
- Simula falha em routeros_api
- Verifica se librouteros é usado quando disponível
"""

import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.mikrotik.controller import MikrotikController

class FakePath:
    def __init__(self):
        pass
    def select(self, **kwargs):
        return ()
    def add(self, **kwargs):
        print('Fake add called with', kwargs)
        return {'success': True}
    def update(self, **kwargs):
        print('Fake update called with', kwargs)
        return {'success': True}

class FakeLibApi:
    def path(self, path):
        return FakePath()

if __name__ == '__main__':
    mc = MikrotikController('127.0.0.1', 'admin', 'password')

    # Ensure routeros_api exists in this environment, stub behavior
    mc._api = object()  # truthy

    # Monkeypatch routeros API method to raise
    def fake_routeros_failure(name, interface, profile):
        raise Exception('simulated routeros_api failure')

    mc._add_pppoe_server_routeros_api = fake_routeros_failure

    # Ensure librouteros fallback is present and set
    mc._librouteros_api = FakeLibApi()

    print('Calling add_pppoe_server to verify fallback...')
    result = mc.add_pppoe_server('pppoe-server', 'ether1', 'pppoe-default')
    print('Result:', result)
