from app.core.database import SessionLocal
from app.models.models import ServicoContratado, Cliente
from app.models.models import StatusContrato

db = SessionLocal()
try:
    empresa_id = 3
    # 1. Total active contracts with onu_serial or FIBRA connection
    all_contracts = db.query(ServicoContratado).filter(
        ServicoContratado.empresa_id == empresa_id,
        ServicoContratado.is_active == True,
        (ServicoContratado.onu_serial.isnot(None)) | (ServicoContratado.tipo_conexao == "FIBRA")
    ).all()
    print(f"Total active/serial/FIBRA contracts: {len(all_contracts)}")

    # 2. Break down by status
    status_counts = {}
    for c in all_contracts:
        status_counts[c.status] = status_counts.get(c.status, 0) + 1
    print(f"Status breakdown: {status_counts}")

    # 3. Check client joins
    has_client = 0
    no_client = 0
    for c in all_contracts:
        client = db.query(Cliente).filter(Cliente.id == c.cliente_id).first()
        if client:
            has_client += 1
        else:
            no_client += 1
    print(f"Join breakdown: With Client={has_client}, Without Client={no_client}")

    # 4. Check if we filter status != CANCELADO
    not_cancelled = [c for c in all_contracts if c.status != StatusContrato.CANCELADO]
    print(f"Not cancelled count: {len(not_cancelled)}")
    
    # 5. Let's run the exact get_onus_status query
    query = db.query(ServicoContratado, Cliente).join(
        Cliente, ServicoContratado.cliente_id == Cliente.id
    ).filter(
        ServicoContratado.empresa_id == empresa_id,
        ServicoContratado.is_active == True,
        ServicoContratado.status != StatusContrato.CANCELADO,
    ).filter(
        (ServicoContratado.onu_serial.isnot(None)) |
        (ServicoContratado.tipo_conexao == "FIBRA")
    )
    print(f"Exact query count: {query.count()}")
    for c, cl in query.all():
        print(f"  Contrato: id={c.id}, cliente={cl.nome_razao_social}, status={c.status}, gps={c.coordenadas_gps}")
        
finally:
    db.close()
