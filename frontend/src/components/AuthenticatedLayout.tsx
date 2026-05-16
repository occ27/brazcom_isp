import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  HomeIcon,
  DocumentTextIcon,
  UserIcon,
  UsersIcon,
  ShieldCheckIcon,
  BuildingOfficeIcon,
  ChartBarIcon,
  ArrowRightOnRectangleIcon,
  ChevronLeftIcon,
  Bars3Icon,
  ServerIcon,
  WifiIcon,
  CloudIcon,
  CogIcon,
  DocumentCheckIcon,
  GlobeAltIcon,
  ServerStackIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  LockClosedIcon,
  BanknotesIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
  ShieldExclamationIcon
} from '@heroicons/react/24/outline';
import { licenseService } from '../services/licenseService';
import { PageType } from '../types';
import { useAuth } from '../contexts/AuthContext';
import { useCompany } from '../contexts/CompanyContext';
import CompanySelector from './CompanySelector';

interface MenuItemType {
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  path: PageType;
  group: string;
}

interface MenuGroupType {
  name: string;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
  items: MenuItemType[];
}

interface Props {
  children: React.ReactNode;
  currentPage: PageType;
  onNavigate: (page: PageType) => void;
}

const AuthenticatedLayout: React.FC<Props> = ({ children, currentPage, onNavigate }) => {
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [drawerCollapsed, setDrawerCollapsed] = useState(false);
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({
    'NFCom': true,
    'Cadastros': true,
    'Administração': false,
    'Rede': false,
    'Relatórios': false
  });
  const [licenseInfo, setLicenseInfo] = useState<{ is_active: boolean, license: any } | null>(null);
  const { user, logout, hasPermission, isClientUser } = useAuth();
  const { activeCompany } = useCompany();

  // Ouvir evento de licença requerida (erro 402 do backend)
  React.useEffect(() => {
    const handler = () => {
      onNavigate('licenses');
    };
    window.addEventListener('license-required', handler);
    return () => window.removeEventListener('license-required', handler);
  }, [onNavigate]);

  // Verificar status da licença para alertas de vencimento
  React.useEffect(() => {
    const checkLicense = async () => {
      const empresaId = activeCompany?.id || user?.active_empresa_id;
      if (empresaId && !isClientUser()) {
        try {
          const data = await licenseService.checkStatus(empresaId);
          setLicenseInfo(data);
        } catch (err) {
          console.error("Erro ao verificar licença:", err);
          setLicenseInfo(null);
        }
      } else {
        setLicenseInfo(null);
      }
    };
    checkLicense();
  }, [activeCompany?.id, user?.active_empresa_id, isClientUser]);

  const isLicensePage = currentPage === 'licenses';
  const isSuperUser = user?.is_superuser;

  // Bloqueio estrito se a licença não estiver ativa
  const isBlocked = licenseInfo && !licenseInfo.is_active && !isLicensePage && !isClientUser();

  const handleBypass = () => {
    if (licenseInfo) {
      setLicenseInfo({ ...licenseInfo, is_active: true });
    }
  };

  const daysRemaining = React.useMemo(() => {
    if (!licenseInfo?.license?.end_date) return null;
    const end = new Date(licenseInfo.license.end_date);
    const today = new Date();
    // Zerar as horas para comparação apenas de data
    today.setHours(0, 0, 0, 0);
    const diffTime = end.getTime() - today.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
  }, [licenseInfo]);

  // Se for usuário cliente, renderiza layout simplificado
  if (isClientUser()) {
    return (
      <div className="min-h-screen bg-gray-50">
        {/* Header simplificado para clientes */}
        <header className="bg-white shadow-sm border-b">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center h-16">
              <div className="flex items-center">
                <h1 className="text-xl font-semibold text-gray-900">Portal do Cliente</h1>
              </div>
              <div className="flex items-center space-x-4">
                <div className="flex flex-col items-end pr-4 border-r border-gray-200">
                  <span className="text-sm font-bold text-gray-900 leading-none">{user?.full_name}</span>
                  <span className="text-[10px] text-indigo-600 font-bold uppercase tracking-tighter mt-1">
                    Cliente
                  </span>
                </div>
                <button
                  onClick={() => {
                    logout();
                    navigate('/');
                  }}
                  className="text-gray-500 hover:text-red-600 px-3 py-2 rounded-md text-sm font-medium transition-colors"
                >
                  Sair
                </button>
              </div>
            </div>
          </div>
        </header>

        {/* Conteúdo principal */}
        <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
          {children}
        </main>
      </div>
    );
  }

  // Largura do drawer colapsado (não utilizado diretamente, mas mantido para referência)

  // Itens do menu organizados por grupos para NFCom
  const menuGroups: MenuGroupType[] = [
    {
      name: 'NFCom',
      icon: DocumentTextIcon,
      color: 'green',
      items: [
        { label: 'Emitir NFCom', icon: DocumentTextIcon, path: 'nfcom' as PageType, group: 'nfcom' },
      ]
    },
    {
      name: 'Cadastros',
      icon: BuildingOfficeIcon,
      color: 'purple',
      items: [

        { label: 'Clientes', icon: UsersIcon, path: 'clients' as PageType, group: 'cadastros' },
        { label: 'Serviços', icon: CogIcon, path: 'services' as PageType, group: 'cadastros' },
        { label: 'Contratos', icon: DocumentCheckIcon, path: 'contracts' as PageType, group: 'cadastros' },
      ]
    },
    {
      name: 'Financeiro',
      icon: DocumentTextIcon,
      color: 'green',
      items: [
        { label: 'Contas Bancárias', icon: DocumentTextIcon, path: 'bank-accounts' as PageType, group: 'financeiro' },
        { label: 'Cobranças', icon: DocumentTextIcon, path: 'receivables' as PageType, group: 'financeiro' },
        { label: 'Relatórios', icon: ChartBarIcon, path: 'reports' as PageType, group: 'financeiro' },
        { label: 'Suporte/Tickets', icon: DocumentTextIcon, path: 'tickets' as PageType, group: 'financeiro' },
      ]
    },
    {
      name: 'Administração',
      icon: UserIcon,
      color: 'orange',
      items: [
        { label: 'Empresas', icon: BuildingOfficeIcon, path: 'companies' as PageType, group: 'cadastros' },
        { label: 'Usuários', icon: UserIcon, path: 'users' as PageType, group: 'administracao' },
        { label: 'Minha Licença', icon: BanknotesIcon, path: 'licenses' as PageType, group: 'administracao' },
        ...(user?.is_superuser ? [
          { label: 'Roles', icon: ShieldCheckIcon, path: 'roles' as PageType, group: 'administracao' },
          { label: 'Permissões', icon: ShieldCheckIcon, path: 'permissions' as PageType, group: 'administracao' },
          { label: 'Aprovar Licenças', icon: BanknotesIcon, path: 'admin-licenses' as PageType, group: 'administracao' }
        ] : []),
      ]
    },
    {
      name: 'Rede',
      icon: WifiIcon,
      color: 'blue',
      items: [
        { label: 'Routers', icon: HomeIcon, path: 'routers' as PageType, group: 'administracao' },
        { label: 'Classes IP', icon: ServerIcon, path: 'ip-classes' as PageType, group: 'administracao' },
        { label: 'PPPoE', icon: GlobeAltIcon, path: 'pppoe' as PageType, group: 'rede' },
        { label: 'DHCP', icon: ServerStackIcon, path: 'dhcp' as PageType, group: 'rede' },
        ...(user?.is_superuser ? [{ label: 'RADIUS NAS', icon: LockClosedIcon, path: 'radius-nas' as PageType, group: 'rede' }] : []),
      ]
    }
  ];

  // Mapeamento opcional de permissão necessária por rota (se vazio -> visível por padrão)
  // Pode ser string ou array de strings para permitir OR lógico entre permissões
  const permissionMap: Record<string, string | string[] | undefined> = {
    nfcom: 'nfcom_manage',
    users: 'user_manage',
    roles: 'role_manage',
    permissions: 'permission_manage',
    companies: 'company_manage',
    clients: 'clients_manage',
    services: 'services_manage',
    // Permitir visualizar Contratos tanto para quem gerencia quanto para quem apenas vê
    contracts: ['contract_manage', 'contract_view'],
    routers: 'network_manage',
    'ip-classes': 'ip_class_manage',
    pppoe: 'pppoe_manage',
    dhcp: 'dhcp_manage',
    reports: 'report_view'
  };

  // Permissões para financeiro
  permissionMap['bank-accounts'] = 'bank_accounts_view';
  permissionMap['receivables'] = 'receivables_view';
  permissionMap['tickets'] = 'tickets_view';
  // RADIUS NAS: apenas super_admin (is_superuser) — verificado na própria página

  const canViewItem = (path: PageType) => {
    const required = permissionMap[path as string];
    if (!required) return true; // sem permissão declarada -> visível
    try {
      if (Array.isArray(required)) {
        return required.some(r => hasPermission(r));
      }
      return hasPermission(required as string);
    } catch (e) {
      return false;
    }
  };

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const handleNavigate = (page: PageType) => {
    onNavigate(page);
    // Fechar sidebar automaticamente em mobile após navegação
    if (window.innerWidth < 768) { // md breakpoint
      setMobileOpen(false);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const toggleGroupExpansion = (groupName: string) => {
    setExpandedGroups(prev => ({
      ...prev,
      [groupName]: !prev[groupName]
    }));
  };

  // Função não utilizada (mantida para compatibilidade futura)

  const getGroupColor = (color: string) => {
    const colors = {
      blue: 'bg-blue-100 text-blue-600',
      green: 'bg-green-100 text-green-600',
      purple: 'bg-purple-100 text-purple-600',
      orange: 'bg-orange-100 text-orange-600',
      emerald: 'bg-emerald-100 text-emerald-600',
    };
    return colors[color as keyof typeof colors] || 'bg-gray-100 text-gray-600';
  };

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Sidebar */}
      <div
        className={`fixed inset-y-0 left-0 z-50 bg-white shadow-lg transform transition-all duration-300 ease-in-out flex flex-col ${mobileOpen ? 'translate-x-0' : '-translate-x-full'
          } ${drawerCollapsed ? 'w-16' : 'w-64'} md:translate-x-0`}
      >
        <div className={`flex items-center border-b border-gray-200 transition-all duration-300 ${drawerCollapsed ? 'p-2 justify-center' : 'p-6'
          } bg-gradient-to-r from-indigo-50 to-blue-50`}>
          <div
            className={`flex items-center ${drawerCollapsed ? '' : 'mr-3'} cursor-pointer hover:bg-white/60 rounded-lg ${drawerCollapsed ? 'p-1' : 'p-2'} transition-all duration-200`}
            onClick={() => setDrawerCollapsed(!drawerCollapsed)}
            title={drawerCollapsed ? 'Expandir sidebar' : 'Recolher sidebar'}
          >
            <Bars3Icon className={`text-indigo-600 ${drawerCollapsed ? 'h-5 w-5' : 'h-5 w-5 mr-3'}`} />
            {!drawerCollapsed && (
              <h1 className="text-sm font-bold text-gray-800 truncate bg-gradient-to-r from-indigo-600 to-blue-600 bg-clip-text text-transparent">
                Brazcom ISP Suite
              </h1>
            )}
          </div>
          <button
            onClick={() => setDrawerCollapsed(!drawerCollapsed)}
            className={`text-gray-500 hover:text-indigo-600 ${drawerCollapsed ? 'p-1' : 'p-2'} rounded-lg hover:bg-white/60 transition-all duration-200 ${drawerCollapsed ? 'ml-0' : 'ml-auto'
              }`}
            title={drawerCollapsed ? 'Expandir sidebar' : 'Recolher sidebar'}
          >
            {drawerCollapsed ? (
              <ChevronLeftIcon className="h-4 w-4" />
            ) : (
              <ChevronLeftIcon className="h-4 w-4" />
            )}
          </button>
        </div>

        <nav
          className={`flex-1 ${drawerCollapsed ? 'mt-4' : 'mt-6'} ${drawerCollapsed ? 'px-0.5' : ''} overflow-y-auto`}
          style={{ WebkitOverflowScrolling: 'touch' }}
        >
          {/* Dashboard item - standalone above groups */}
          <div className="mb-4">
            <button
              onClick={() => handleNavigate('dashboard')}
              className={`flex items-center w-full transition-colors rounded-lg ${drawerCollapsed ? 'px-1 py-3 justify-center' : 'px-3 py-3'
                } ${currentPage === 'dashboard'
                  ? 'bg-indigo-50 text-indigo-700 border-r-2 border-indigo-700 shadow-sm'
                  : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                }`}
              title={drawerCollapsed ? 'Dashboard' : ''}
            >
              <HomeIcon className={`flex-shrink-0 ${drawerCollapsed ? 'h-6 w-6' : 'h-5 w-5 mr-3'}`} />
              {!drawerCollapsed && (
                <span className="truncate font-medium">Dashboard</span>
              )}
            </button>
          </div>

          {/* Separator before groups */}
          {!drawerCollapsed && (
            <div className="mx-4 mb-4 border-t border-gray-200"></div>
          )}

          {menuGroups.map((group, groupIndex) => (
            <div key={group.name} className="mb-2">
              {/* Título do grupo */}
              {(() => {
                const hasVisible = group.items.some(it => canViewItem(it.path));
                if (!hasVisible) return null;
                return (!drawerCollapsed && (
                  <button
                    onClick={() => toggleGroupExpansion(group.name)}
                    className="w-full px-3 py-2 text-left hover:bg-gray-50 rounded-lg transition-colors"
                  >
                    <h3 className="text-xs font-bold text-gray-600 uppercase tracking-wider flex items-center">
                      <div className={`p-1 rounded ${getGroupColor(group.color)} mr-2`}>
                        <group.icon className="h-3 w-3" />
                      </div>
                      <span className="flex-1">{group.name}</span>
                      {expandedGroups[group.name] ? (
                        <ChevronDownIcon className="h-4 w-4 text-gray-400" />
                      ) : (
                        <ChevronRightIcon className="h-4 w-4 text-gray-400" />
                      )}
                    </h3>
                  </button>
                ));
              })()}

              {/* Itens do grupo */}
              {expandedGroups[group.name] && group.items.filter(item => canViewItem(item.path)).map((item) => (
                <button
                  key={item.path}
                  onClick={() => handleNavigate(item.path)}
                  className={`flex items-center w-full transition-colors rounded-lg ${drawerCollapsed ? 'px-1 py-3 justify-center' : 'px-3 py-3'
                    } ${currentPage === item.path
                      ? 'bg-indigo-50 text-indigo-700 border-r-2 border-indigo-700 shadow-sm'
                      : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                    }`}
                  title={drawerCollapsed ? item.label : ''}
                >
                  <item.icon className={`flex-shrink-0 ${drawerCollapsed ? 'h-6 w-6' : 'h-5 w-5 mr-3'}`} />
                  {!drawerCollapsed && (
                    <span className="truncate font-medium">{item.label}</span>
                  )}
                </button>
              ))}

              {/* Separador entre grupos */}
              {groupIndex < menuGroups.length - 1 && !drawerCollapsed && (
                <div className="mx-4 my-4 border-t border-gray-200"></div>
              )}
            </div>
          ))}

          {/* Botão de logout */}
          <div className={`${drawerCollapsed ? 'px-0.5' : 'px-2'}`}>
            <button
              onClick={handleLogout}
              className={`flex items-center w-full transition-colors rounded-lg ${drawerCollapsed ? 'px-1 py-3 justify-center' : 'px-3 py-3'
                } text-gray-600 hover:bg-red-50 hover:text-red-700`}
              title={drawerCollapsed ? 'Sair' : ''}
            >
              <ArrowRightOnRectangleIcon className={`flex-shrink-0 ${drawerCollapsed ? 'h-6 w-6' : 'h-5 w-5 mr-3'}`} />
              {!drawerCollapsed && (
                <span>Sair</span>
              )}
            </button>
          </div>
        </nav>
      </div>

      {/* Main content */}
      <div className={`flex-1 flex flex-col overflow-hidden transition-all duration-300 ${drawerCollapsed ? 'md:ml-16' : 'md:ml-64'
        }`}>
        {/* Top bar */}
        <header className="bg-white shadow-sm border-b border-gray-200">
          <div className="flex items-center justify-between h-14 sm:h-16 px-2 sm:px-3 md:px-4">
            <button
              onClick={handleDrawerToggle}
              className="p-1.5 sm:p-2 rounded-md text-gray-400 hover:text-gray-600 md:hidden"
            >
              <Bars3Icon className="w-5 h-5 sm:w-6 sm:h-6" />
            </button>

            <div className="flex items-center flex-1">
              <div className="ml-2 sm:ml-4">
                <CompanySelector />
              </div>
              
              <div className="ml-auto flex flex-col items-end pl-2 sm:pl-4 border-l border-gray-200">
                <span className="text-[11px] font-extrabold text-indigo-700 leading-tight">
                  <span className="hidden sm:inline">{user?.full_name || user?.nome || 'Usuário'}</span>
                  <span className="sm:hidden">{(user?.full_name || user?.nome || 'Usuário').split(' ')[0]}</span>
                </span>
                <span className="text-[9px] text-gray-400 font-bold uppercase tracking-tight">
                  {user?.is_superuser || user?.is_company_admin ? 'Admin' : 'Op'}
                  <span className="hidden xs:inline"> {user?.is_superuser || user?.is_company_admin ? '' : 'Sistema'}</span>
                </span>
              </div>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto bg-gray-50 p-2 sm:p-3 md:p-4 lg:p-6 relative">
          {/* Bloqueio de Licença */}
          {isBlocked && (
            <div className="absolute inset-0 z-50 flex items-center justify-center bg-gray-900/60 backdrop-blur-md p-4">
              <div className="bg-white p-8 rounded-3xl shadow-2xl max-w-md w-full text-center border border-gray-100">
                <div className="bg-red-100 w-20 h-20 rounded-2xl flex items-center justify-center mx-auto mb-6 transform rotate-3">
                  <ShieldExclamationIcon className="h-12 w-12 text-red-600" />
                </div>
                <h2 className="text-2xl font-bold text-gray-900 mb-2">Sistema Bloqueado</h2>
                <p className="text-gray-600 mb-8">
                  A licença da empresa <span className="font-bold text-indigo-600">{activeCompany?.nome_fantasia || activeCompany?.razao_social}</span> não está ativa ou expirou.
                </p>
                
                <div className="space-y-3">
                  <button 
                    onClick={() => onNavigate('licenses')}
                    className="w-full bg-indigo-600 text-white py-4 rounded-2xl font-bold hover:bg-indigo-700 transition-all shadow-lg shadow-indigo-200 flex items-center justify-center gap-2"
                  >
                    <span>Regularizar Licença</span>
                  </button>
                  
                  <button 
                    onClick={logout}
                    className="w-full bg-gray-100 text-gray-700 py-3 rounded-2xl font-semibold hover:bg-gray-200 transition-all"
                  >
                    Sair do Sistema
                  </button>

                  {isSuperUser && (
                    <button 
                      onClick={handleBypass}
                      className="w-full text-gray-400 hover:text-gray-500 text-xs mt-4 underline"
                    >
                      Bypass temporário (Apenas Superuser)
                    </button>
                  )}
                </div>
              </div>
            </div>
          )}

          {daysRemaining !== null && daysRemaining <= 30 && (
            <div className={`mb-6 p-4 rounded-xl border flex items-center shadow-sm transition-all duration-300 ${
              daysRemaining <= 5 
                ? 'bg-red-50 border-red-200 text-red-800' 
                : 'bg-amber-50 border-amber-200 text-amber-800'
            }`}>
              <div className={`p-2 rounded-lg mr-4 ${
                daysRemaining <= 5 ? 'bg-red-100' : 'bg-amber-100'
              }`}>
                <ExclamationTriangleIcon className={`h-6 w-6 ${
                  daysRemaining <= 5 ? 'text-red-600' : 'text-amber-600'
                }`} />
              </div>
              <div className="flex-1">
                <h4 className="text-sm font-bold uppercase tracking-tight">Aviso de Licenciamento</h4>
                <p className="text-sm opacity-90">
                  {daysRemaining <= 0 
                    ? `Sua licença expirou em ${new Date(licenseInfo?.license?.end_date).toLocaleDateString('pt-BR')}.`
                    : `Sua licença vence em ${daysRemaining} ${daysRemaining === 1 ? 'dia' : 'dias'} (${new Date(licenseInfo?.license?.end_date).toLocaleDateString('pt-BR')}).`
                  } Renove para evitar interrupções no acesso.
                </p>
              </div>
              <button 
                onClick={() => handleNavigate('licenses')}
                className={`ml-4 px-4 py-2 rounded-lg text-sm font-bold shadow-sm transition-all ${
                  daysRemaining <= 5
                    ? 'bg-red-600 text-white hover:bg-red-700'
                    : 'bg-amber-600 text-white hover:bg-amber-700'
                }`}
              >
                Renovar Agora
              </button>
            </div>
          )}
          {children}
        </main>
      </div>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black bg-opacity-50 md:hidden"
          onClick={handleDrawerToggle}
        />
      )}
    </div>
  );
};

export default AuthenticatedLayout;