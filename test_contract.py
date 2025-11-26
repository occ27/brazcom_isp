import requests

# Login
login_url = 'http://localhost:8000/auth/login'
login_data = {'username': 'orlandobrz@gmail.com', 'password': 'android'}

login_response = requests.post(login_url, data=login_data)
if login_response.status_code == 200:
    token = login_response.json().get('access_token')
    print('Token obtido')

    # Listar serviços
    url = 'http://localhost:8000/servicos/empresa/1'
    headers = {'Authorization': f'Bearer {token}'}

    response = requests.get(url, headers=headers)
    print(f'Status: {response.status_code}')
    if response.status_code == 200:
        services = response.json()
        print(f'Serviços encontrados: {len(services)}')
        if services:
            print(f'Primeiro: ID {services[0]["id"]} - {services[0]["descricao"]}')

    # Testar criação de contrato
    if services:
        contract_url = 'http://localhost:8000/servicos-contratados/empresa/1'
        headers['Content-Type'] = 'application/json'

        contract_data = {
            'cliente_id': 1,
            'servico_id': services[0]['id'],
            'valor_unitario': 100.0,
            'quantidade': 1,
            'dia_emissao': 5
        }

        response = requests.post(contract_url, headers=headers, json=contract_data)
        print(f'Contract creation status: {response.status_code}')
        print(f'Response: {response.text}')
else:
    print('Erro no login:', login_response.text)