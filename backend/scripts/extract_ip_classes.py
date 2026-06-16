import sys
import os
import ipaddress

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import SessionLocal
from app.models.models import ServicoContratado, Empresa
from app.models.network import IPClass

EMPRESA_ID = 5

def main():
    db = SessionLocal()
    try:
        # Get all IPs from ServicoContratado
        servicos = db.query(ServicoContratado).filter(
            ServicoContratado.empresa_id == EMPRESA_ID,
            ServicoContratado.assigned_ip.isnot(None),
            ServicoContratado.assigned_ip != ''
        ).all()
        
        subnets = set()
        
        for servico in servicos:
            ip_str = servico.assigned_ip.strip()
            try:
                # Trata IPs como IPv4
                ip = ipaddress.IPv4Address(ip_str)
                # Pega a rede /24 do IP
                network = ipaddress.IPv4Network(f"{ip}/24", strict=False)
                subnets.add(str(network))
            except Exception as e:
                pass
                
        print(f"Encontradas {len(subnets)} classes de IP (/24):")
        
        count_inserted = 0
        for i, subnet in enumerate(sorted(subnets)):
            # Check se já existe na base
            ip_class = db.query(IPClass).filter(
                IPClass.empresa_id == EMPRESA_ID,
                IPClass.rede == subnet
            ).first()
            
            if not ip_class:
                # Gateway is typically the .1 or .254 of the network
                network_obj = ipaddress.IPv4Network(subnet)
                gateway = str(network_obj[1]) # ex: 192.168.1.1
                
                new_class = IPClass(
                    nome=f"Rede {network_obj.network_address}",
                    rede=subnet,
                    gateway=gateway,
                    dns1="8.8.8.8",
                    dns2="1.1.1.1",
                    empresa_id=EMPRESA_ID
                )
                db.add(new_class)
                count_inserted += 1
                print(f" - {subnet} (Criada)")
            else:
                print(f" - {subnet} (Já existente)")
                
        if count_inserted > 0:
            db.commit()
            
        print(f"\n{count_inserted} novas classes inseridas no banco.")
            
    finally:
        db.close()

if __name__ == "__main__":
    main()
