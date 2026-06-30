import sys

file_path = "/Users/orlando/python/FastAPI/brazcom_isp/frontend/src/pages/Dashboard.tsx"
with open(file_path, "r") as f:
    lines = f.readlines()

new_lines = []
for idx, line in enumerate(lines):
    if "import { useCompany } from '../contexts/CompanyContext';" in line:
        new_lines.append(line)
        new_lines.append("import { useAuth } from '../contexts/AuthContext';\n")
        continue

    if "const { activeCompany } = useCompany();" in line:
        new_lines.append(line)
        new_lines.append("  const { hasPermission } = useAuth();\n")
        new_lines.append("  const canViewFinancials = hasPermission('company_manage');\n")
        continue
    
    # Hide "Meta do Mês" box if not canViewFinancials
    if "Meta do Mês" in line:
        # The surrounding box starts a few lines earlier.
        pass

    # We will just conditionally render the entire Grid items.
    new_lines.append(line)

with open(file_path, "w") as f:
    f.writelines(new_lines)
