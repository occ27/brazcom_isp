import requests
import os

# URL da página de documentos
url = "https://dfe-portal.svrs.rs.gov.br/Nfcom/Documentos"

print("Baixando página de documentos...")
response = requests.get(url)
if response.status_code != 200:
    print(f"Erro ao baixar página: {response.status_code}")
    exit(1)

# Procurar por links de download dos schemas NT 2025.001
content = response.text
print("Procurando links de schemas...")

# Procurar por padrões de links de schemas
import re
schema_links = re.findall(r'href="([^"]*schemas[^"]*2025[^"]*\.zip[^"]*)"', content, re.IGNORECASE)

if schema_links:
    print(f"Encontrados {len(schema_links)} links de schemas")
    for link in schema_links[:3]:  # Baixar apenas os primeiros 3
        if not link.startswith('http'):
            link = "https://dfe-portal.svrs.rs.gov.br" + link

        filename = os.path.basename(link)
        print(f"Baixando {filename}...")

        try:
            schema_response = requests.get(link)
            if schema_response.status_code == 200:
                with open(filename, 'wb') as f:
                    f.write(schema_response.content)
                print(f"✅ {filename} baixado com sucesso")
            else:
                print(f"❌ Erro ao baixar {filename}: {schema_response.status_code}")
        except Exception as e:
            print(f"❌ Erro: {e}")
else:
    print("Nenhum link de schema encontrado")
    # Salvar a página para análise manual
    with open('pagina_documentos.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Página salva como pagina_documentos.html para análise manual")