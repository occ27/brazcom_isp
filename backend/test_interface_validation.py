#!/usr/bin/env python3
"""
Small test harness for is_wan_interface and setup_pppoe_server validation.
This script doesn't require a real router -- it will simulate using stubbed methods
by monkeypatching MikrotikController methods.
"""

from app.mikrotik.controller import MikrotikController

class FakeMC(MikrotikController):
    def __init__(self):
        super().__init__('127.0.0.1','admin','password')
        self._api = None
        self._librouteros_api = None

    def is_wan_interface(self, interface: str) -> bool:
        # Simulate that ether1 is WAN, others not
        return interface == 'ether1'

    def connect(self):
        # Do nothing
        pass

    def add_dhcp_pool(self, *args, **kwargs):
        print('add_dhcp_pool called', args, kwargs)

    def add_pppoe_profile(self, *args, **kwargs):
        print('add_pppoe_profile called', args, kwargs)

    def add_pppoe_server(self, *args, **kwargs):
        print('add_pppoe_server called', args, kwargs)

    def setup_pppoe_firewall_rules(self):
        print('setup_pppoe_firewall_rules called')


if __name__ == '__main__':
    mc = FakeMC()
    # Should raise on ether1
    try:
        mc.setup_pppoe_server('ether1')
        print('Unexpected: did not raise for ether1')
    except Exception as e:
        print('Correctly raised for ether1:', e)

    # Should not raise if explicit override
    try:
        mc.setup_pppoe_server('ether1', allow_wan_interface=True)
        print('Allowed override passed for ether1')
    except Exception as e:
        print('Unexpected: override raised', e)

    # Should succeed for a LAN interface
    try:
        mc.setup_pppoe_server('lan1')
        print('OK for lan1')
    except Exception as e:
        print('Unexpected:', e)
