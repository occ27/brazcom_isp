"""
Serviço de sincronização entre o Brazcom ISP e as tabelas nativas do FreeRadius.

Este serviço escreve diretamente nas tabelas radcheck, radreply e lê da radacct,
garantindo que qualquer operação feita no Brazcom (criar, suspender, remover cliente)
reflita imediatamente no FreeRadius — sem intervenção manual.

Tabelas do FreeRadius gerenciadas:
    - radcheck   → credenciais de autenticação (usuário + senha + Auth-Type)
    - radreply   → atributos enviados ao NAS após autenticação (rate-limit, IP fixo)
    - radacct    → sessões ativas (somente leitura)
    - radpostauth → log de autenticações (somente leitura)
    - nas        → clientes NAS (Mikrotik/roteadores autorizados a usar o RADIUS)
                   Substitui o arquivo /etc/freeradius/3.0/clients.conf — sem root!
"""
import logging
from typing import Optional, List, Dict, Any
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session
# pyrefly: ignore [missing-import]
from sqlalchemy import text
from datetime import datetime

logger = logging.getLogger(__name__)


class RadiusSyncService:
    """
    Serviço que sincroniza dados entre o Brazcom ISP e o banco do FreeRadius.
    Recebe uma sessão do banco `radius` (porta 3315) como dependência.
    """

    def __init__(self, radius_db: Session):
        self.db = radius_db

    # ─────────────────────────────────────────────
    # ESCRITA: radcheck + radreply
    # ─────────────────────────────────────────────

    def sync_user(
        self,
        username: str,
        password: str,
        rate_limit: Optional[str] = None,
        ip_fixo: Optional[str] = None,
    ) -> bool:
        """
        Cria ou atualiza um usuário no FreeRadius.

        - Garante que o usuário existe em radcheck com Cleartext-Password.
        - Remove o atributo Auth-Type = Reject (se havia suspensão anterior).
        - Atualiza radreply com Mikrotik-Rate-Limit e Framed-IP-Address.

        Args:
            username:   Login PPPoE do cliente.
            password:   Senha em texto claro (o FreeRadius compara internamente).
            rate_limit: Velocidade no formato "10M/40M" (upload/download). Opcional.
            ip_fixo:    IP fixo a atribuir. Opcional.

        Returns:
            True se sucesso, False se houve erro.
        """
        try:
            # 1. Remove entradas antigas para reescrever limpo
            self._delete_radcheck_attribute(username, "Cleartext-Password")
            self._delete_radcheck_attribute(username, "Auth-Type")

            # 2. Insere a senha
            self._upsert_radcheck(username, "Cleartext-Password", ":=", password)

            # 3. Atualiza atributos de resposta (radreply)
            if rate_limit:
                self._upsert_radreply(username, "Mikrotik-Rate-Limit", "=", rate_limit)
            else:
                self._delete_radreply_attribute(username, "Mikrotik-Rate-Limit")

            if ip_fixo:
                self._upsert_radreply(username, "Framed-IP-Address", "=", ip_fixo)
            else:
                self._delete_radreply_attribute(username, "Framed-IP-Address")

            self.db.commit()
            logger.info(f"[RadiusSync] Usuário '{username}' sincronizado com sucesso.")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"[RadiusSync] Erro ao sincronizar usuário '{username}': {e}")
            return False

    def disable_user(self, username: str) -> bool:
        """
        Suspende um usuário no FreeRadius adicionando Auth-Type = Reject.
        O cliente PPPoE será desconectado na próxima tentativa de reautenticação.

        Args:
            username: Login PPPoE do cliente.

        Returns:
            True se sucesso, False se houve erro.
        """
        try:
            # Adiciona/sobrescreve Auth-Type = Reject — o FreeRadius rejeita sem consultar a senha
            self._upsert_radcheck(username, "Auth-Type", ":=", "Reject")
            self.db.commit()
            logger.info(f"[RadiusSync] Usuário '{username}' SUSPENSO no FreeRadius.")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"[RadiusSync] Erro ao suspender usuário '{username}': {e}")
            return False

    def enable_user(self, username: str) -> bool:
        """
        Reativa um usuário suspenso removendo o atributo Auth-Type = Reject.

        Args:
            username: Login PPPoE do cliente.

        Returns:
            True se sucesso, False se houve erro.
        """
        try:
            self._delete_radcheck_attribute(username, "Auth-Type")
            self.db.commit()
            logger.info(f"[RadiusSync] Usuário '{username}' REATIVADO no FreeRadius.")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"[RadiusSync] Erro ao reativar usuário '{username}': {e}")
            return False

    def delete_user(self, username: str) -> bool:
        """
        Remove completamente um usuário do FreeRadius.
        Usado quando o cliente é cancelado ou excluído do Brazcom.

        Args:
            username: Login PPPoE do cliente.

        Returns:
            True se sucesso, False se houve erro.
        """
        try:
            self.db.execute(
                text("DELETE FROM radcheck WHERE username = :username"),
                {"username": username}
            )
            self.db.execute(
                text("DELETE FROM radreply WHERE username = :username"),
                {"username": username}
            )
            self.db.execute(
                text("DELETE FROM radusergroup WHERE username = :username"),
                {"username": username}
            )
            self.db.commit()
            logger.info(f"[RadiusSync] Usuário '{username}' REMOVIDO do FreeRadius.")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"[RadiusSync] Erro ao remover usuário '{username}': {e}")
            return False

    def update_rate_limit(self, username: str, rate_limit: str) -> bool:
        """
        Atualiza somente o limite de velocidade de um usuário (troca de plano).

        Args:
            username:   Login PPPoE do cliente.
            rate_limit: Novo limite no formato "10M/40M".

        Returns:
            True se sucesso, False se houve erro.
        """
        try:
            self._upsert_radreply(username, "Mikrotik-Rate-Limit", "=", rate_limit)
            self.db.commit()
            logger.info(f"[RadiusSync] Rate-limit de '{username}' atualizado para '{rate_limit}'.")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"[RadiusSync] Erro ao atualizar rate-limit de '{username}': {e}")
            return False

    # ─────────────────────────────────────────────
    # LEITURA: radacct (sessões ativas)
    # ─────────────────────────────────────────────

    def get_active_sessions(self, username: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retorna sessões PPPoE ativas lendo diretamente da tabela radacct.

        Args:
            username: Filtrar por usuário específico. Se None, retorna todas.

        Returns:
            Lista de dicionários com dados da sessão.
        """
        try:
            if username:
                result = self.db.execute(
                    text("""
                        SELECT acctsessionid, username, nasipaddress, framedipaddress,
                               callingstationid, acctstarttime, acctsessiontime,
                               acctinputoctets, acctoutputoctets
                        FROM radacct
                        WHERE acctstoptime IS NULL AND username = :username
                        ORDER BY acctstarttime DESC
                    """),
                    {"username": username}
                )
            else:
                result = self.db.execute(
                    text("""
                        SELECT acctsessionid, username, nasipaddress, framedipaddress,
                               callingstationid, acctstarttime, acctsessiontime,
                               acctinputoctets, acctoutputoctets
                        FROM radacct
                        WHERE acctstoptime IS NULL
                        ORDER BY acctstarttime DESC
                        LIMIT 500
                    """)
                )

            rows = result.fetchall()
            sessions = []
            for row in rows:
                sessions.append({
                    "session_id": row.acctsessionid,
                    "username": row.username,
                    "nas_ip": row.nasipaddress,
                    "ip_address": row.framedipaddress,
                    "mac_address": row.callingstationid,
                    "start_time": row.acctstarttime.isoformat() if row.acctstarttime else None,
                    "duration_seconds": row.acctsessiontime,
                    "bytes_in": row.acctinputoctets,
                    "bytes_out": row.acctoutputoctets,
                })
            return sessions

        except Exception as e:
            logger.error(f"[RadiusSync] Erro ao buscar sessões ativas: {e}")
            return []

    def get_auth_history(self, username: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Retorna o histórico de autenticações de um usuário (tabela radpostauth).

        Args:
            username: Login PPPoE do cliente.
            limit:    Quantidade máxima de registros a retornar.

        Returns:
            Lista de dicionários com histórico de autenticações.
        """
        try:
            result = self.db.execute(
                text("""
                    SELECT username, pass, reply, authdate
                    FROM radpostauth
                    WHERE username = :username
                    ORDER BY authdate DESC
                    LIMIT :limit
                """),
                {"username": username, "limit": limit}
            )
            rows = result.fetchall()
            return [
                {
                    "username": row.username,
                    "reply": row.reply,
                    "authdate": row.authdate.isoformat() if row.authdate else None,
                }
                for row in rows
            ]
        except Exception as e:
            logger.error(f"[RadiusSync] Erro ao buscar histórico de auth de '{username}': {e}")
            return []

    # ─────────────────────────────────────────────
    # HELPERS INTERNOS
    # ─────────────────────────────────────────────

    def _upsert_radcheck(self, username: str, attribute: str, op: str, value: str):
        """Insere ou atualiza um atributo na tabela radcheck."""
        existing = self.db.execute(
            text("SELECT id FROM radcheck WHERE username = :u AND attribute = :a"),
            {"u": username, "a": attribute}
        ).fetchone()

        if existing:
            self.db.execute(
                text("UPDATE radcheck SET op = :op, value = :v WHERE username = :u AND attribute = :a"),
                {"op": op, "v": value, "u": username, "a": attribute}
            )
        else:
            self.db.execute(
                text("INSERT INTO radcheck (username, attribute, op, value) VALUES (:u, :a, :op, :v)"),
                {"u": username, "a": attribute, "op": op, "v": value}
            )

    def _upsert_radreply(self, username: str, attribute: str, op: str, value: str):
        """Insere ou atualiza um atributo na tabela radreply."""
        existing = self.db.execute(
            text("SELECT id FROM radreply WHERE username = :u AND attribute = :a"),
            {"u": username, "a": attribute}
        ).fetchone()

        if existing:
            self.db.execute(
                text("UPDATE radreply SET op = :op, value = :v WHERE username = :u AND attribute = :a"),
                {"op": op, "v": value, "u": username, "a": attribute}
            )
        else:
            self.db.execute(
                text("INSERT INTO radreply (username, attribute, op, value) VALUES (:u, :a, :op, :v)"),
                {"u": username, "a": attribute, "op": op, "v": value}
            )

    def _delete_radcheck_attribute(self, username: str, attribute: str):
        """Remove um atributo específico da tabela radcheck."""
        self.db.execute(
            text("DELETE FROM radcheck WHERE username = :u AND attribute = :a"),
            {"u": username, "a": attribute}
        )

    def _delete_radreply_attribute(self, username: str, attribute: str):
        """Remove um atributo específico da tabela radreply."""
        self.db.execute(
            text("DELETE FROM radreply WHERE username = :u AND attribute = :a"),
            {"u": username, "a": attribute}
        )

    # ─────────────────────────────────────────────
    # GERENCIAMENTO DE CLIENTES NAS (tabela `nas`)
    # Substitui o arquivo /etc/freeradius/3.0/clients.conf
    # Não precisa de root — basta acesso ao banco MySQL do FreeRadius
    # ─────────────────────────────────────────────

    def list_nas_clients(self) -> List[Dict[str, Any]]:
        """
        Lista todos os clientes NAS registrados no FreeRadius.

        Equivalente ao conteúdo do arquivo clients.conf, mas gerenciado
        pelo banco de dados. Inclui todos os roteadores/Mikrotik autorizados
        a enviar requisições RADIUS.

        Returns:
            Lista de dicionários com dados de cada NAS.
        """
        try:
            result = self.db.execute(
                text("SELECT id, nasname, shortname, type, ports, secret, server, community, description FROM nas ORDER BY id")
            ).fetchall()
            return [
                {
                    "id": row.id,
                    "nasname": row.nasname,
                    "shortname": row.shortname,
                    "type": row.type or "other",
                    "ports": row.ports,
                    "secret": row.secret,
                    "server": row.server,
                    "community": row.community,
                    "description": row.description,
                }
                for row in result
            ]
        except Exception as e:
            logger.error(f"[NAS] Erro ao listar clientes NAS: {e}")
            return []

    def get_nas_client(self, nas_id: int) -> Optional[Dict[str, Any]]:
        """
        Busca um cliente NAS pelo ID.

        Args:
            nas_id: ID do cliente NAS na tabela.

        Returns:
            Dicionário com dados do NAS ou None se não encontrado.
        """
        try:
            row = self.db.execute(
                text("SELECT id, nasname, shortname, type, ports, secret, server, community, description FROM nas WHERE id = :id"),
                {"id": nas_id}
            ).fetchone()
            if not row:
                return None
            return {
                "id": row.id,
                "nasname": row.nasname,
                "shortname": row.shortname,
                "type": row.type or "other",
                "ports": row.ports,
                "secret": row.secret,
                "server": row.server,
                "community": row.community,
                "description": row.description,
            }
        except Exception as e:
            logger.error(f"[NAS] Erro ao buscar NAS id={nas_id}: {e}")
            return None

    def get_nas_client_by_ip(self, ip: str) -> Optional[Dict[str, Any]]:
        """
        Busca um cliente NAS pelo seu endereço IP (nasname).

        Args:
            ip: Endereço IP do roteador (nasname).

        Returns:
            Dicionário com dados do NAS ou None se não encontrado.
        """
        try:
            row = self.db.execute(
                text("SELECT id, nasname, shortname, type, ports, secret, server, community, description FROM nas WHERE nasname = :ip"),
                {"ip": ip}
            ).fetchone()
            if not row:
                return None
            return {
                "id": row.id,
                "nasname": row.nasname,
                "shortname": row.shortname,
                "type": row.type or "other",
                "ports": row.ports,
                "secret": row.secret,
                "server": row.server,
                "community": row.community,
                "description": row.description,
            }
        except Exception as e:
            logger.error(f"[NAS] Erro ao buscar NAS pelo IP {ip}: {e}")
            return None


    def create_nas_client(
        self,
        nasname: str,
        secret: str,
        shortname: str = "",
        nas_type: str = "other",
        description: str = "",
        ports: Optional[int] = None,
        server: Optional[str] = None,
        community: Optional[str] = None,
    ) -> Optional[int]:
        """
        Registra um novo cliente NAS (roteador/Mikrotik) no FreeRadius.

        Após a inserção, o FreeRadius aceita requisições RADIUS vindas deste
        endereço IP com o segredo compartilhado informado. Equivalente a
        adicionar um bloco `client { ... }` no clients.conf, sem necessidade
        de root ou restart do serviço.

        Args:
            nasname:     IP ou hostname do roteador (ex: '192.168.100.1').
            secret:      Segredo compartilhado RADIUS (deve coincidir com o
                         configurado na Mikrotik em /radius add).
            shortname:   Nome curto para identificação (ex: 'rb-sede').
            nas_type:    Tipo do NAS. Use 'other' para Mikrotik.
            description: Descrição livre (ex: 'Mikrotik - Torre Sede').
            ports:       Porta RADIUS (normalmente None = padrão 1812).
            server:      Servidor RADIUS virtual (normalmente None).
            community:   Community SNMP (normalmente None).

        Returns:
            ID da linha inserida ou None em caso de erro.
        """
        try:
            result = self.db.execute(
                text("""
                    INSERT INTO nas (nasname, shortname, type, ports, secret, server, community, description)
                    VALUES (:nasname, :shortname, :type, :ports, :secret, :server, :community, :description)
                """),
                {
                    "nasname": nasname,
                    "shortname": shortname or nasname,
                    "type": nas_type,
                    "ports": ports,
                    "secret": secret,
                    "server": server,
                    "community": community,
                    "description": description,
                }
            )
            self.db.commit()
            nas_id = result.lastrowid
            logger.info(f"[NAS] Cliente NAS '{nasname}' (id={nas_id}) registrado no FreeRadius.")
            return nas_id
        except Exception as e:
            self.db.rollback()
            logger.error(f"[NAS] Erro ao criar cliente NAS '{nasname}': {e}")
            return None

    def update_nas_client(
        self,
        nas_id: int,
        nasname: Optional[str] = None,
        secret: Optional[str] = None,
        shortname: Optional[str] = None,
        nas_type: Optional[str] = None,
        description: Optional[str] = None,
        ports: Optional[int] = None,
        server: Optional[str] = None,
        community: Optional[str] = None,
    ) -> bool:
        """
        Atualiza os dados de um cliente NAS existente.

        Permite alterar IP, segredo, nome ou descrição de um roteador
        já registrado, sem precisar editar qualquer arquivo no servidor.

        Args:
            nas_id: ID do NAS a atualizar.
            (demais parâmetros são opcionais — apenas os fornecidos são alterados)

        Returns:
            True se atualizado com sucesso, False em caso de erro.
        """
        try:
            # Monta apenas as colunas que foram fornecidas
            fields = []
            params: Dict[str, Any] = {"id": nas_id}

            if nasname is not None:
                fields.append("nasname = :nasname")
                params["nasname"] = nasname
            if shortname is not None:
                fields.append("shortname = :shortname")
                params["shortname"] = shortname
            if secret is not None:
                fields.append("secret = :secret")
                params["secret"] = secret
            if nas_type is not None:
                fields.append("type = :type")
                params["type"] = nas_type
            if description is not None:
                fields.append("description = :description")
                params["description"] = description
            if ports is not None:
                fields.append("ports = :ports")
                params["ports"] = ports
            if server is not None:
                fields.append("server = :server")
                params["server"] = server
            if community is not None:
                fields.append("community = :community")
                params["community"] = community

            if not fields:
                return True  # Nada a atualizar

            sql = f"UPDATE nas SET {', '.join(fields)} WHERE id = :id"
            self.db.execute(text(sql), params)
            self.db.commit()
            logger.info(f"[NAS] Cliente NAS id={nas_id} atualizado.")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"[NAS] Erro ao atualizar NAS id={nas_id}: {e}")
            return False

    def delete_nas_client(self, nas_id: int) -> bool:
        """
        Remove um cliente NAS do FreeRadius.

        Após a remoção, o roteador não poderá mais enviar requisições RADIUS.
        Equivalente a remover o bloco `client { }` do clients.conf.

        Args:
            nas_id: ID do NAS a remover.

        Returns:
            True se removido com sucesso, False em caso de erro.
        """
        try:
            self.db.execute(text("DELETE FROM nas WHERE id = :id"), {"id": nas_id})
            self.db.commit()
            logger.info(f"[NAS] Cliente NAS id={nas_id} removido do FreeRadius.")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"[NAS] Erro ao remover NAS id={nas_id}: {e}")
            return False

