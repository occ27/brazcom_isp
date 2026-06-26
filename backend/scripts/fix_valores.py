import sys
import os
from collections import Counter

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import SessionLocal
from app.models.models import ServicoContratado, Receivable, Cliente
from app.models.servico_model import Servico

def main():
    db = SessionLocal()
    try:
        # Step 1: Find the most common 'amount' in Receivable for each ServicoContratado or Cliente
        # Since Receivable in import_pronect is linked to ServicoContratado:
        # servico_contratado_id=contrato.id if contrato else None
        
        # We can just fetch all Receivables for EMPRESA_ID = 6
        receivables = db.query(Receivable).filter(Receivable.empresa_id == 6).all()
        
        # Map: servico_contratado_id -> list of amounts
        sc_amounts = {}
        for r in receivables:
            if r.servico_contratado_id and r.amount > 0:
                if r.servico_contratado_id not in sc_amounts:
                    sc_amounts[r.servico_contratado_id] = []
                sc_amounts[r.servico_contratado_id].append(r.amount)
                
        # Find mode amount for each ServicoContratado
        print(f"Calculando valores para {len(sc_amounts)} contratos com base no histórico financeiro...")
        count = 0
        
        for sc_id, amounts in sc_amounts.items():
            if not amounts:
                continue
            # Most common amount
            most_common_amount = Counter(amounts).most_common(1)[0][0]
            
            sc = db.query(ServicoContratado).filter(ServicoContratado.id == sc_id).first()
            if sc and sc.valor_unitario == 0.0:
                sc.valor_unitario = float(most_common_amount)
                count += 1
                
        db.commit()
        print(f"{count} Contratos atualizados com valores corretos.")
        
        # Step 2: Update base plans (Servico)
        servicos = db.query(Servico).filter(Servico.empresa_id == 6).all()
        count_planos = 0
        for s in servicos:
            # Find all ServicoContratado for this plan
            scs = db.query(ServicoContratado).filter(
                ServicoContratado.servico_id == s.id,
                ServicoContratado.valor_unitario > 0
            ).all()
            if scs:
                amounts = [sc.valor_unitario for sc in scs]
                most_common = Counter(amounts).most_common(1)[0][0]
                if s.valor_unitario == 0.0:
                    s.valor_unitario = most_common
                    count_planos += 1
                    
        db.commit()
        print(f"{count_planos} Planos base atualizados com valores corretos.")
        
    except Exception as e:
        db.rollback()
        print(f"Erro: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
