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
    parser.add_argument("--notifications-only", action="store_true", help="Executa apenas o envio de notificações pendentes")
    args, unknown = parser.parse_known_args()

    print("=============================================================")
    print("Starting daily processing: Auto-blocking/Unblocking clients...")
    print("=============================================================")
    
    session = SessionLocal()
    # Usar data e hora oficial do Brasil (America/Sao_Paulo - UTC-3) para evitar erros
    tz_br = timezone(timedelta(hours=-3))
    now = datetime.now(tz_br).replace(tzinfo=None)
    
    total_blocked = 0
    total_unblocked = 0
    total_generated = 0
    total_nfcom_emitted = 0
    db_changed = False
    company_summaries = []
    
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
            
            if args.notifications_only:
                # MODO 2: Apenas notificações pendentes (Horário comercial)
                print(f"  [AUTO-NOTIFICATIONS] Processing pending receivable notifications...")
                company_notified = 0
                try:
                    from app.services.receivable_service import send_receivable_notification
                    pending_receivables = session.query(Receivable).filter(
                        Receivable.empresa_id == company.id,
                        Receivable.status == 'PENDING',
                        Receivable.sent_at == None
                    ).all()

                    if pending_receivables:
                        print(f"  [AUTO-NOTIFICATIONS] Found {len(pending_receivables)} pending receivables to notify.")
                        for r in pending_receivables:
                            try:
                                session.flush()
                                if send_receivable_notification(session, r):
                                    company_notified += 1
                                    db_changed = True
                            except Exception as notif_err:
                                print(f"    [AUTO-NOTIFICATIONS] [WARNING] Failed to notify receivable #{r.id}: {notif_err}")
                        if company_notified > 0:
                            print(f"  [AUTO-NOTIFICATIONS] Sent {company_notified}/{len(pending_receivables)} notifications via configured channels.")
                    else:
                        print(f"  [AUTO-NOTIFICATIONS] No pending receivables to notify today.")
                except Exception as e:
                    print(f"  [AUTO-NOTIFICATIONS] [ERROR] Failed to process notifications: {e}")
                
                # Pula os demais passos do processamento diário no modo de notificação apenas
                company_summaries.append({
                    "name": company.nome_fantasia or company.razao_social,
                    "id": company.id,
                    "generated": 0,
                    "nfcom_emitted": 0,
                    "blocked": 0,
                    "unblocked": 0
                })
                continue

            # MODO 1: Processamento Diário Completo (Meia-noite) - Sem Notificações (Silencioso)
            # 1. Gerar cobranças automáticas para o dia de hoje
            print(f"  [AUTO-BILLING] Generating today's receivables...")
            company_generated = 0
            try:
                from app.services.receivable_service import generate_receivables_for_company
                today_date = now.date()
                created_recv = generate_receivables_for_company(session, company.id, today_date)
                if created_recv:
                    company_generated = len(created_recv)
                    print(f"  [AUTO-BILLING] Generated {company_generated} new receivables for today (notified later in morning run).")
                    total_generated += company_generated
                    db_changed = True
                else:
                    print(f"  [AUTO-BILLING] No new receivables to generate today.")
            except Exception as e:
                print(f"  [AUTO-BILLING] [ERROR] Failed to generate today's receivables: {e}")
            
            # 1.1 Gerar e transmitir NFComs automáticas para contratos marcados
            print(f"  [AUTO-NFCOM] Processing automatic NFCom emissions...")
            company_nfcom_emitted = 0
            try:
                from app.crud.crud_nfcom import bulk_emit_nfcom_from_contracts
                
                # Definir função local que ignora last_emission, evitando ser bloqueado 
                # pelo passo anterior de AUTO-BILLING que atualizou last_emission na memória do SQLAlchemy
                def should_generate_nfcom_for_contract(contrato, target_date):
                    ref_date = contrato.data_inicio_cobranca or contrato.d_contrato_ini
                    if not contrato.dia_emissao or not ref_date:
                        return False
                    if contrato.dia_emissao > target_date.day:
                        return False
                    months_diff = (target_date.year - ref_date.year) * 12 + (target_date.month - ref_date.month)
                    if contrato.periodicidade == 'MENSAL':
                        return True
                    elif contrato.periodicidade == 'BIMESTRAL':
                        return months_diff % 2 == 0
                    elif contrato.periodicidade == 'TRIMESTRAL':
                        return months_diff % 3 == 0
                    elif contrato.periodicidade == 'SEMESTRAL':
                        return months_diff % 6 == 0
                    elif contrato.periodicidade == 'ANUAL':
                        return months_diff % 12 == 0
                    return True
                
                today_date = now.date()
                eligible_contracts = session.query(ServicoContratado).filter(
                    ServicoContratado.empresa_id == company.id,
                    ServicoContratado.is_active == True,
                    ServicoContratado.auto_emit_nfcom == True
                ).all()
                
                nfcom_contract_ids = []
                for c in eligible_contracts:
                    # pular contratos que ainda não começaram
                    ref_date = c.data_inicio_cobranca or c.d_contrato_ini
                    if ref_date and ref_date > today_date:
                        continue
                    # pular contratos que já terminaram
                    if c.d_contrato_fim and c.d_contrato_fim < today_date:
                        continue
                    # verificar se deve gerar baseado na periodicidade e dia_emissao
                    if not should_generate_nfcom_for_contract(c, today_date):
                        continue
                    
                    nfcom_contract_ids.append(c.id)
                
                if nfcom_contract_ids:
                    print(f"  [AUTO-NFCOM] Found {len(nfcom_contract_ids)} contracts eligible for automatic NFCom today.")
                    # Executar e transmitir as NFComs!
                    result = bulk_emit_nfcom_from_contracts(
                        db=session,
                        contract_ids=nfcom_contract_ids,
                        empresa_id=company.id,
                        execute=True,
                        transmit=True
                    )
                    successes = result.get("successes", [])
                    failures = result.get("failures", [])
                    skipped = result.get("skipped", [])
                    
                    if successes:
                        print(f"  [AUTO-NFCOM] Successfully emitted and authorized {len(successes)} NFComs.")
                        for s in successes:
                            print(f"    -> Contract #{s['contract_id']} => NFCom #{s['numero_nf']} (Serie {s['serie']}) - Transmitted: {s['transmitted']}")
                            if s['transmitted']:
                                company_nfcom_emitted += 1
                        total_nfcom_emitted += company_nfcom_emitted
                        db_changed = True
                    if failures:
                        print(f"  [AUTO-NFCOM] [WARNING] Failed to emit {len(failures)} NFComs:")
                        for f in failures:
                            print(f"    -> Contract #{f['contract_id']} => Error: {f['error']}")
                    if skipped:
                        print(f"  [AUTO-NFCOM] Skipped {len(skipped)} contracts (already emitted today).")
                else:
                    print(f"  [AUTO-NFCOM] No contracts eligible for automatic NFCom today.")
            except Exception as e:
                import traceback
                print(f"  [AUTO-NFCOM] [ERROR] Failed to process automatic NFComs: {e}")
                traceback.print_exc()
            
            dias_limite = company.dias_bloqueio_inadimplentes
            if dias_limite is None or dias_limite < 0:
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
            company_summaries.append({
                "name": company.nome_fantasia or company.razao_social,
                "id": company.id,
                "generated": company_generated,
                "nfcom_emitted": company_nfcom_emitted,
                "blocked": company_blocked,
                "unblocked": company_unblocked
            })
            
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
        
    print("\n" + "="*60)
    print("                 DAILY PROCESSING SUMMARY")
    print("="*60)
    print(f" Date: {now.date()}")
    print(f" Total Companies Processed: {len(companies)}")
    print(f" Total Receivables Generated: {total_generated}")
    print(f" Total NFComs Emitted: {total_nfcom_emitted}")
    print(f" Total Contracts Suspended: {total_blocked}")
    print(f" Total Contracts Reactivated: {total_unblocked}")
    print("-"*60)
    print(" Breakdowns by Company:")
    for summary in company_summaries:
        print(f" * {summary['name']} (ID: {summary['id']}):")
        print(f"   - Receivables Generated: {summary['generated']}")
        print(f"   - NFComs Emitted       : {summary['nfcom_emitted']}")
        print(f"   - Contracts Suspended  : {summary['blocked']}")
        print(f"   - Contracts Reactivated: {summary['unblocked']}")
    print("="*60)
    print("Daily processing finished successfully.")

if __name__ == "__main__":
    run_auto_blocking()
