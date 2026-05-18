import sys
import os
from datetime import datetime, timezone, timedelta

# Add the project root to the python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import SessionLocal
from app.models.models import Empresa, Cliente, Receivable, ServicoContratado, StatusContrato
from app.services.isp_service import process_block_if_needed, process_unblock_if_needed

def run_auto_blocking():
    import argparse
    parser = argparse.ArgumentParser(description="Script de bloqueio automático de clientes inadimplentes.")
    parser.add_argument("--company", type=int, help="ID da empresa para processar especificamente")
    parser.add_argument("--force-days", type=int, help="Força a quantidade de dias limite de atraso para teste")
    args, unknown = parser.parse_known_args()

    print("=============================================================")
    print("Starting daily processing: Auto-blocking/Unblocking clients...")
    print("=============================================================")
    
    session = SessionLocal()
    now = datetime.now(timezone.utc)
    
    total_blocked = 0
    total_unblocked = 0
    db_changed = False
    
    try:
        # Get active companies (with optional company filter)
        query = session.query(Empresa).filter(Empresa.is_active == True)
        if args.company is not None:
            query = query.filter(Empresa.id == args.company)
        companies = query.all()
        
        if not companies:
            print("No active companies found matching filters. Exiting.")
            return
            
        for company in companies:
            print(f"\n>>> Processing company: {company.razao_social or company.nome_fantasia} (ID: {company.id})")
            
            dias_limite = args.force_days if args.force_days is not None else company.dias_bloqueio_inadimplentes
            if dias_limite is None or dias_limite <= 0:
                print(f"  [AUTO-BLOCK] Disabled or not configured (dias_bloqueio_inadimplentes is {company.dias_bloqueio_inadimplentes}).")
                continue
                
            print(f"  [AUTO-BLOCK] Enabled with limit: {dias_limite} days.")
            
            # Fetch all active clients of this company
            clients = session.query(Cliente).filter(
                Cliente.empresa_id == company.id,
                Cliente.is_active == True
            ).all()
            
            limit_date = now - timedelta(days=dias_limite)
            
            company_blocked = 0
            company_unblocked = 0
            
            for client in clients:
                # Find any unpaid/pending receivable overdue by more than dias_limite days
                overdue_receivables = session.query(Receivable).filter(
                    Receivable.cliente_id == client.id,
                    Receivable.empresa_id == company.id,
                    Receivable.status == 'PENDING',
                    Receivable.due_date <= limit_date
                ).all()
                
                should_be_blocked = len(overdue_receivables) > 0
                
                if should_be_blocked:
                    # Find all active or non-suspended/non-cancelled contracts for the client
                    contracts = session.query(ServicoContratado).filter(
                        ServicoContratado.cliente_id == client.id,
                        ServicoContratado.empresa_id == company.id,
                        ServicoContratado.status != StatusContrato.SUSPENSO,
                        ServicoContratado.status != StatusContrato.CANCELADO
                    ).all()
                    
                    if contracts:
                        print(f"    -> Client '{client.nome_razao_social}' (ID: {client.id}) has {len(overdue_receivables)} overdue receivables.")
                        for contract in contracts:
                            print(f"       Suspending contract #{contract.id} (Current status: {contract.status})...")
                            success = process_block_if_needed(session, contract.id)
                            if success:
                                print(f"       [SUCCESS] Contract #{contract.id} suspended successfully.")
                                company_blocked += 1
                                total_blocked += 1
                                db_changed = True
                            else:
                                print(f"       [FAILED] Could not suspend contract #{contract.id}.")
                                
                else:
                    # Client is up-to-date. Check if they have any suspended contracts that need to be unblocked
                    suspended_contracts = session.query(ServicoContratado).filter(
                        ServicoContratado.cliente_id == client.id,
                        ServicoContratado.empresa_id == company.id,
                        ServicoContratado.status == StatusContrato.SUSPENSO
                    ).all()
                    
                    if suspended_contracts:
                        print(f"    -> Client '{client.nome_razao_social}' (ID: {client.id}) is up-to-date.")
                        for contract in suspended_contracts:
                            print(f"       Activating contract #{contract.id} (Current status: {contract.status})...")
                            success = process_unblock_if_needed(session, contract.id)
                            if success:
                                print(f"       [SUCCESS] Contract #{contract.id} reactivated successfully.")
                                company_unblocked += 1
                                total_unblocked += 1
                                db_changed = True
                            else:
                                print(f"       [FAILED] Could not reactivate contract #{contract.id}.")
            
            print(f"  [AUTO-BLOCK] Summary for {company.nome_fantasia or company.razao_social}: {company_blocked} contracts suspended, {company_unblocked} contracts reactivated.")
            
        if db_changed:
            print("\nCommitting changes to the database...")
            session.commit()
            print("Changes committed successfully.")
        else:
            print("\nNo database changes to save.")
            
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        print("Rolling back changes.")
        session.rollback()
    finally:
        print("\nClosing database session.")
        session.close()
        
    print("\n" + "="*40)
    print("   DAILY PROCESSING SUMMARY")
    print("="*40)
    print(f"Date: {now.date()}")
    print(f"Active companies processed: {len(companies)}")
    print(f"Contracts automatically suspended: {total_blocked}")
    print(f"Contracts automatically reactivated: {total_unblocked}")
    print("="*40)
    print("Daily processing finished successfully.")

if __name__ == "__main__":
    run_auto_blocking()
