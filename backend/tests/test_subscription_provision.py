import pytest

from app.routes.subscriptions import router as subscriptions_router
from app.routes.subscriptions import MikrotikController


class DummyMK:
    def __init__(self, *args, **kwargs):
        self.calls = []

    def set_arp_entry(self, ip, mac, interface=None):
        self.calls.append(('arp', ip, mac, interface))
        return True

    def set_queue_simple(self, name, target, max_limit, burst=None):
        self.calls.append(('queue', name, target, max_limit))
        return True

    def remove_arp_entry(self, ip, mac=None):
        self.calls.append(('remove_arp', ip, mac))
        return True

    def close(self):
        pass


def test_dummy_mikrotik_calls(monkeypatch):
    # monkeypatch MikrotikController in the module to use DummyMK
    class FakeMKFactory:
        def __init__(self, *a, **k):
            self._inst = DummyMK()

        def __getattr__(self, item):
            return getattr(self._inst, item)

    monkeypatch.setattr('app.routes.subscriptions.MikrotikController', FakeMKFactory)

    # Basic smoke: instantiate factory and call methods
    mk = FakeMKFactory()
    assert mk.set_arp_entry('192.0.2.1', 'AA:BB:CC:DD:EE:FF') is True
    assert mk.set_queue_simple('name', '192.0.2.1/32', '10M/2M') is True
