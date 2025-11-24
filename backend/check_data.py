#!/usr/bin/env python3
"""
Script para verificar se os dados necessários existem no banco de dados
para o endpoint que está falhando em produção.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import get_db
from app.models import models

def check_data_existence():
    """Verifica se cliente 2979 e empresa 25 existem no banco."""
    try:
        db = next(get_db())

        # Verificar se cliente existe
        cliente = db.query(models.Cliente).filter(models.Cliente.id == 2979).first()
        if cliente:
            print(f"✓ Cliente 2979 encontrado: {cliente.nome_razao_social}")
        else:
            print("✗ Cliente 2979 NÃO encontrado")

        # Verificar se empresa existe
        empresa = db.query(models.Empresa).filter(models.Empresa.id == 25).first()
        if empresa:
            print(f"✓ Empresa 25 encontrada: {empresa.razao_social}")
        else:
            print("✗ Empresa 25 NÃO encontrada")

        # Verificar se há servicos_contratados para este cliente/empresa
        contratos = db.query(models.ServicoContratado).filter(
            models.ServicoContratado.cliente_id == 2979,
            models.ServicoContratado.empresa_id == 25,
            models.ServicoContratado.is_active == True
        ).all()

        print(f"✓ Encontrados {len(contratos)} contratos ativos para cliente 2979 e empresa 25")

        # Verificar se os serviços referenciados existem
        for contrato in contratos:
            servico = db.query(models.Servico).filter(models.Servico.id == contrato.servico_id).first()
            if servico:
                print(f"✓ Serviço {contrato.servico_id} encontrado: {servico.descricao}")
            else:
                print(f"✗ Serviço {contrato.servico_id} NÃO encontrado")

        db.close()
        return True

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = check_data_existence()
    sys.exit(0 if success else 1)