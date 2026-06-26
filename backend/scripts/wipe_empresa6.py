import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import SessionLocal
from app.models.models import Receivable, Ticket, ServicoContratado, EmpresaClienteEndereco, EmpresaCliente, Cliente
from app.models.servico_model import Servico

db = SessionLocal()
try:
    print("Deletando Receivables...")
    db.query(Receivable).filter(Receivable.empresa_id == 6).delete()
    print("Deletando Tickets...")
    db.query(Ticket).filter(Ticket.empresa_id == 6).delete()
    print("Deletando ServicoContratado...")
    db.query(ServicoContratado).filter(ServicoContratado.empresa_id == 6).delete()
    
    print("Deletando Enderecos...")
    emp_clientes = db.query(EmpresaCliente).filter(EmpresaCliente.empresa_id == 6).all()
    emp_ids = [e.id for e in emp_clientes]
    if emp_ids:
        db.query(EmpresaClienteEndereco).filter(EmpresaClienteEndereco.empresa_cliente_id.in_(emp_ids)).delete(synchronize_session=False)
        
    print("Deletando EmpresaCliente...")
    db.query(EmpresaCliente).filter(EmpresaCliente.empresa_id == 6).delete()
    
    print("Deletando Cliente...")
    db.query(Cliente).filter(Cliente.empresa_id == 6).delete()
    
    print("Deletando Servicos (planos)...")
    db.query(Servico).filter(Servico.empresa_id == 6).delete()

    db.commit()
    print("Limpeza concluída com sucesso!")
except Exception as e:
    db.rollback()
    print(f"Erro: {e}")
finally:
    db.close()
