import sys
import re

# 1. Update receivables.py (create_manual_receivable)
file1 = "/Users/orlando/python/FastAPI/brazcom_isp/backend/app/routes/receivables.py"
with open(file1, "r") as f:
    content1 = f.read()

# Add logic to assign nosso_numero in create_manual_receivable
patch1 = """
        if ba:
            recv.bank_account_id = ba.id
            recv.bank = ba.bank
            
            if recv.tipo == 'BOLETO' and ba.bank != 'MERCADO_PAGO':
                seq = ba.nosso_numero_sequence or 1
                recv.nosso_numero = str(seq)
                ba.nosso_numero_sequence = seq + 1
                db.add(ba)
"""
content1 = content1.replace("        if ba:\n            recv.bank_account_id = ba.id\n            recv.bank = ba.bank", patch1.strip("\n"))

with open(file1, "w") as f:
    f.write(content1)

# 2. Update receivable_service.py (generate_receivable_from_contract)
file2 = "/Users/orlando/python/FastAPI/brazcom_isp/backend/app/services/receivable_service.py"
with open(file2, "r") as f:
    content2 = f.read()

patch2 = """
        # Popular referência à conta e snapshot (sem credenciais)
        recv.bank_account_id = bank_account.id
        
        if recv.tipo == 'BOLETO' and bank_account.bank != 'MERCADO_PAGO':
            seq = bank_account.nosso_numero_sequence or 1
            recv.nosso_numero = str(seq)
            bank_account.nosso_numero_sequence = seq + 1
            db.add(bank_account)
"""
content2 = content2.replace("        # Popular referência à conta e snapshot (sem credenciais)\n        recv.bank_account_id = bank_account.id", patch2.strip("\n"))

with open(file2, "w") as f:
    f.write(content2)

# 3. Fix the db.commit() missing in bank_accounts.py (register_boletos_api)
file3 = "/Users/orlando/python/FastAPI/brazcom_isp/backend/app/routes/bank_accounts.py"
with open(file3, "r") as f:
    content3 = f.read()

patch3 = """
    results = []
    for r in receivables:
        try:
            success, error_msg = await BillingService._register_bb(db, r, ba)
            results.append({"id": r.id, "ok": success, "error": None if success else error_msg})
        except Exception as e:
            results.append({"id": r.id, "ok": False, "error": str(e)})
            
    db.commit()
    return {"results": results}
"""
content3 = content3.replace("""
    results = []
    for r in receivables:
        try:
            success, error_msg = await BillingService._register_bb(db, r, ba)
            results.append({"id": r.id, "ok": success, "error": None if success else error_msg})
        except Exception as e:
            results.append({"id": r.id, "ok": False, "error": str(e)})
            
    return {"results": results}
""".strip("\n"), patch3.strip("\n"))

with open(file3, "w") as f:
    f.write(content3)

