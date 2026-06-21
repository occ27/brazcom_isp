import json

files = [
    "/Users/orlando/python/FastAPI/brazcom_isp/backend/app/schemas/caixa.py",
    "/Users/orlando/python/FastAPI/brazcom_isp/backend/app/crud/crud_caixa.py",
    "/Users/orlando/python/FastAPI/brazcom_isp/backend/app/routes/caixa.py",
    "/Users/orlando/python/FastAPI/brazcom_isp/frontend/src/pages/CaixaPDV.tsx",
    "/Users/orlando/python/FastAPI/brazcom_isp/frontend/src/services/caixaService.ts"
]

for filepath in files:
    try:
        with open(filepath, "r") as f:
            content = f.read()
            
        if content.startswith('"') and content.endswith('"'):
            real_content = json.loads(content)
            with open(filepath, "w") as f:
                f.write(real_content)
            print(f"Fixed {filepath}")
        elif content.startswith('"') and content.endswith('"\n'):
            real_content = json.loads(content.strip())
            with open(filepath, "w") as f:
                f.write(real_content)
            print(f"Fixed {filepath}")
    except Exception as e:
        print(f"Error on {filepath}: {e}")
