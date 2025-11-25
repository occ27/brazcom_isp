# 📡 Gerenciamento de Interfaces de Router MikroTik

## Visão Geral

O sistema Brazcom ISP agora oferece gerenciamento completo de interfaces de routers MikroTik, permitindo sincronização automática de interfaces, configuração de endereços IP e atribuição de classes IP sem necessidade de usar o Winbox.

## 🚀 Funcionalidades Implementadas

### 1. **Sincronização Automática de Interfaces**
- Busca automaticamente todas as interfaces do router MikroTik
- Cria/atualiza interfaces no banco de dados do sistema
- Sincroniza endereços IP configurados no router
- Mapeia tipos de interface (Ethernet, Wireless, VLAN, etc.)

### 2. **Gerenciamento de Classes IP**
- Criação de classes IP reutilizáveis
- Definição de rede, gateway e servidores DNS
- Atribuição de classes às interfaces dos routers
- Aplicação automática de configurações no router

### 3. **Configuração Automática de IP**
- Aplicação de endereços IP nas interfaces via API
- Configuração de servidores DNS
- Suporte a comentários nas configurações
- Validação de conflitos de IP

## 📋 Como Usar

### **Passo 1: Adicionar um Router**
1. Acesse o menu "Routers"
2. Clique em "Novo Router"
3. Preencha os dados de conexão (IP, usuário, senha, porta)
4. Salve o router

### **Passo 2: Criar Classes IP**
1. Acesse o menu "Classes de IP"
2. Clique em "Nova Classe IP"
3. Defina:
   - **Nome**: Identificação da classe
   - **Rede**: Ex: `192.168.1.0/24`
   - **Gateway**: Ex: `192.168.1.1`
   - **DNS Primário/Secundário**: Servidores DNS

### **Passo 3: Gerenciar Interfaces**
1. No menu "Routers", clique no ícone de interface (🔗) do router
2. **Sincronizar Interfaces**: Clique em "Sincronizar" para buscar interfaces do router
3. **Atribuir Classes IP**: Clique no ícone de rede (📡) em uma interface
4. Selecione a classe IP desejada e confirme

### **Passo 4: Aplicar Configurações**
1. Para cada interface com classe IP atribuída
2. Clique no ícone "Aplicar" (▶️)
3. O sistema configurará automaticamente:
   - Endereço IP na interface
   - Servidores DNS no router
   - Comentários identificadores

## 🔧 Funcionalidades Técnicas

### **API Endpoints**

#### Interfaces de Router
```
GET    /network/routers/{router_id}/interfaces/          # Listar interfaces
POST   /network/routers/{router_id}/interfaces/          # Criar interface
PUT    /network/interfaces/{interface_id}                # Atualizar interface
DELETE /network/interfaces/{interface_id}                # Excluir interface
```

#### Endereços IP
```
GET    /network/interfaces/{interface_id}/ip-addresses/  # Listar IPs
POST   /network/interfaces/{interface_id}/ip-addresses/  # Adicionar IP
```

#### Classes IP
```
GET    /network/ip-classes/                              # Listar classes
POST   /network/ip-classes/                              # Criar classe
PUT    /network/ip-classes/{class_id}                    # Atualizar classe
DELETE /network/ip-classes/{class_id}                    # Excluir classe
```

#### Operações Especiais
```
POST   /network/routers/{router_id}/sync-interfaces/     # Sincronizar interfaces
POST   /network/interfaces/{interface_id}/apply-ip-config/ # Aplicar config IP
POST   /network/interface-ip-assignments/                # Atribuir classe IP
DELETE /network/interface-ip-assignments/{interface_id}/{ip_class_id} # Remover atribuição
```

### **Modelo de Dados**

#### RouterInterface
```typescript
{
  id: number;
  router_id: number;
  nome: string;           // ether1, wlan1, etc.
  tipo: string;           // ethernet, wireless, vlan
  mac_address?: string;
  comentario?: string;
  is_active: boolean;
  ip_classes: IPClass[];  // Classes atribuídas
}
```

#### IPClass
```typescript
{
  id: number;
  empresa_id: number;
  nome: string;
  rede: string;           // 192.168.1.0/24
  gateway?: string;
  dns1?: string;
  dns2?: string;
}
```

### **Integração MikroTik**

O sistema utiliza a biblioteca `routeros-api` para comunicação com routers MikroTik:

```python
from app.mikrotik.controller import MikrotikController

# Conectar ao router
mk = MikrotikController(host="192.168.88.1", username="admin", password="senha")

# Buscar interfaces
interfaces = mk.get_interfaces()

# Configurar IP
mk.set_ip_address("192.168.1.1/24", "ether1", "Rede Interna")

# Configurar DNS
mk.set_dns_servers(["8.8.8.8", "8.8.4.4"])
```

## 🔒 Segurança

- **Criptografia de Senhas**: Senhas dos routers são criptografadas no banco
- **Controle de Acesso**: Apenas usuários da empresa podem gerenciar seus routers
- **Validação de IP**: Verificação de conflitos e formato válido
- **Logs de Auditoria**: Registro de todas as operações realizadas

## 📊 Monitoramento

### **Status das Interfaces**
- **Ativa/Inativa**: Status operacional da interface
- **Configurada**: Se possui endereço IP válido
- **Sincronizada**: Última sincronização com o router

### **Classes IP Atribuídas**
- Visualização clara das classes atribuídas
- Possibilidade de remover atribuições
- Status de aplicação da configuração

## 🛠️ Troubleshooting

### **Problemas Comuns**

#### **Timeout de Conexão**
- Verifique se o router está acessível na rede
- Confirme IP, porta (padrão 8728) e credenciais
- Verifique firewall do router

#### **Erro de Permissões**
- Certifique-se de que o usuário tem permissões administrativas
- Verifique se a API está habilitada no router

#### **Interface Não Encontrada**
- Execute sincronização para atualizar lista de interfaces
- Verifique se a interface existe fisicamente no router

### **Logs e Debug**
- Verifique logs do backend para detalhes de erro
- Use o script `demonstrate_mikrotik_interfaces.py` para testes
- Monitore conectividade de rede

## 🎯 Benefícios

1. **Automação Completa**: Eliminação do uso manual do Winbox
2. **Centralização**: Todas as configurações em um local
3. **Rapidez**: Aplicação instantânea de configurações
4. **Consistência**: Padrões aplicados automaticamente
5. **Auditoria**: Histórico completo de mudanças
6. **Escalabilidade**: Suporte a múltiplos routers e interfaces

## 📈 Próximos Passos

- **Monitoramento em Tempo Real**: Status das interfaces
- **Alertas Automáticos**: Notificações de problemas
- **Backup de Configurações**: Versionamento de configs
- **Integração com DHCP**: Servidores DHCP automáticos
- **Relatórios**: Análises de uso e performance