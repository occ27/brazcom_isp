#!/usr/bin/env python3
"""
Fallback: conecta via SSH ao RouterOS e executa comando para remover ARP
"""
import sys
import os
import time
import paramiko
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))
from app.models.network import Router
from app.core.config import settings


def get_router_from_db():
    database_url = settings.DATABASE_URL
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        router = db.query(Router).filter(Router.is_active == True).first()
        if router:
            return {
                'id': router.id,
                'nome': router.nome,
                'ip': router.ip,
                'usuario': router.usuario,
                'senha': router.senha,
                'porta': router.porta or 8728,
                'tipo': router.tipo
            }
    finally:
        db.close()
    return None


def ssh_remove(target_ip: str):
    router = get_router_from_db()
    if not router:
        print("❌ Router não encontrado")
        return False

    host = router['ip']
    user = router['usuario']
    pwd = router['senha']

    print(f"🔐 Tentando conexão SSH em {host} como {user}")

    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname=host, username=user, password=pwd, timeout=10)

        # Comando RouterOS para remover entradas ARP para o IP
        cmd = f"/ip arp remove [find address={target_ip}]"
        print(f"🖥️  Executando comando: {cmd}")
        stdin, stdout, stderr = client.exec_command(cmd)
        out = stdout.read().decode('utf-8', errors='ignore')
        err = stderr.read().decode('utf-8', errors='ignore')

        print("--- STDOUT ---")
        print(out)
        print("--- STDERR ---")
        print(err)

        # Aguardar e verificar via API
        time.sleep(1)
        client.close()
        return True

    except Exception as e:
        print(f"❌ Erro na conexão SSH/execução: {e}")
        return False


if __name__ == '__main__':
    target = '192.168.18.199'
    ok = ssh_remove(target)
    if ok:
        print(f"\n✅ Comando SSH enviado para remoção do IP {target}")
    else:
        print(f"\n❌ Falha ao enviar comando SSH para {target}")
