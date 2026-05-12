# Guia de Ativação de Novo Provedor (VPN Radius)

Este guia descreve o processo passo a passo para conectar uma nova MikroTik (RB) de um provedor ao servidor central via WireGuard isolado.

---

### 1. Requisitos Prévios
* O provedor deve ter uma RB com **RouterOS v7+**.
* Você deve ter o IP Público do Servidor Central e a **Chave Pública** da interface `wg-radius` do servidor.

---

### 2. Configuração na MikroTik do Provedor (Cliente)

Execute os comandos abaixo no terminal da RB do cliente. 
> [!TIP]
> Cada provedor deve usar um IP único na rede `10.20.0.x`. Exemplo: Provedor 2 = `10.20.0.3`.

```routeros
# 1. Criar a interface
/interface wireguard add name=wg-brazcom comment="VPN SaaS Radius"

# 2. Pegar a Chave Pública (Anote este valor para o passo 3)
/interface wireguard print

# 3. Adicionar o IP da VPN (Use o próximo IP disponível, ex: .3, .4, .5...)
/ip address add address=10.20.0.3/24 interface=wg-brazcom

# 4. Configurar o Peer (Conexão com o Servidor Central)
/interface wireguard peers add interface=wg-brazcom \
    public-key="mRPq+3XrRLM0mASj8oRvG+jzhOPscjWaBssu9mKf0lg=" \
    endpoint-address=186.237.156.134 \
    endpoint-port=51821 \
    allowed-address=10.20.0.1/32 \
    persistent-keepalive=25s
```

---

### 3. Configuração no Servidor Central (Debian)

Agora você precisa autorizar essa nova RB a entrar no servidor.

1. Abra o arquivo de configuração:
   ```bash
   sudo nano /etc/wireguard/wg-radius.conf
   ```

2. Adicione um novo bloco `[Peer]` ao final do arquivo:
   ```ini
   # PROVEDOR X - Nome do Cliente
   [Peer]
   PublicKey = CHAVE_PUBLICA_QUE_VOCE_PEGOU_NA_RB_NO_PASSO_2
   AllowedIPs = 10.20.0.3/32
   ```

3. Aplique a nova configuração sem derrubar quem já está conectado:
   ```bash
   sudo wg addconf wg-radius <(wg-quick strip wg-radius)
   ```

---

### 4. Validação Técnica

No terminal da MikroTik do provedor, execute:
```routeros
/ping 10.20.0.1 count=5
```
* Se houver resposta, o túnel está operacional.
* Se não houver, verifique se a porta `51821 UDP` está liberada no firewall e se as chaves públicas coincidem.

---

### 5. Segurança e Isolamento
Graças às regras que configuramos no `PostUp` do servidor:
* **Isolamento de Clientes:** O Provedor 2 (`10.20.0.3`) **não consegue** acessar o Provedor 1 (`10.20.0.2`).
* **Acesso Restrito:** O Provedor só consegue acessar as portas do Radius (`1812`, `1813`) e `Ping` no servidor central. Todo o restante do servidor (SSH, Banco de Dados, etc) está bloqueado para ele.
