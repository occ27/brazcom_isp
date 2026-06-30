import sys

file_path = "/Users/orlando/python/FastAPI/brazcom_isp/frontend/src/pages/Dashboard.tsx"
with open(file_path, "r") as f:
    lines = f.readlines()

new_lines = []
skip = False
for i, line in enumerate(lines):
    if "import { useCompany } from '../contexts/CompanyContext';" in line:
        new_lines.append(line)
        new_lines.append("import { useAuth } from '../contexts/AuthContext';\n")
        continue

    if "const { activeCompany } = useCompany();" in line:
        new_lines.append(line)
        new_lines.append("  const { hasPermission } = useAuth();\n")
        new_lines.append("  const canViewFinancials = hasPermission('company_manage');\n")
        continue
        
    if "  ];" in line and i > 120 and i < 140:
        new_lines.append(line)
        new_lines.append("\n  const visibleMetrics = canViewFinancials \n    ? mainMetrics \n    : mainMetrics.slice(0, 2); // Somente Clientes e Contratos\n\n")
        continue

    if "        {mainMetrics.map((metric, idx) => (" in line:
        new_lines.append("        {visibleMetrics.map((metric, idx) => (\n")
        continue

    if "<Grid item xs={12} md={4} sx={{ display: 'flex', justifyContent: { xs: 'flex-start', md: 'flex-end' } }}>" in line and "Meta do Mês" in "".join(lines[i:i+10]):
        new_lines.append("          {canViewFinancials && (\n")
        new_lines.append(line)
        continue

    if "</Box>" in line and "Meta do Mês" in "".join(lines[i-10:i]):
        if "             </Box>" in line and "          </Grid>" in lines[i+1]:
            # Actually we just add it after Grid
            pass

    if "          </Grid>" in line and "Meta do Mês" in "".join(lines[i-15:i]):
        new_lines.append(line)
        new_lines.append("          )}\n")
        continue

    if "{/* Area Chart - Revenue */}" in line:
        new_lines.append(line)
        new_lines.append("        {canViewFinancials && (\n")
        continue

    if "</PremiumCard>" in line and "Evolução do Faturamento" in "".join(lines[i-35:i]):
        new_lines.append(line)
        # We know the Grid closes 2 lines after PremiumCard for this section
        pass

    if "          </Grid>" in line and "Evolução do Faturamento" in "".join(lines[i-35:i]):
        new_lines.append(line)
        new_lines.append("        )}\n")
        continue

    if "<Grid item xs={12} lg={4}>" in line and "Doughnut Chart - Status" in lines[i-1]:
        new_lines.append("        <Grid item xs={12} lg={canViewFinancials ? 4 : 12}>\n")
        continue
        
    if "{/* NFCom Metrics */}" in line:
        new_lines.append(line)
        new_lines.append("        {canViewFinancials && (\n")
        continue
        
    if "          </Grid>" in line and "Métricas de NFCom" in "".join(lines[i-30:i]):
        new_lines.append(line)
        new_lines.append("        )}\n")
        continue

    new_lines.append(line)

with open(file_path, "w") as f:
    f.writelines(new_lines)
