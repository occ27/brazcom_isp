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
  ChevronRightIcon
} from '@heroicons/react/24/outline';
import { PageType } from '../types';
import { useAuth } from '../contexts/AuthContext';
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
  const { user, logout, hasPermission } = useAuth();

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
      name: 'Administração',
      icon: UserIcon,
      color: 'orange',
      items: [
        { label: 'Empresas', icon: BuildingOfficeIcon, path: 'companies' as PageType, group: 'cadastros' },
        { label: 'Usuários', icon: UserIcon, path: 'users' as PageType, group: 'administracao' },
            { label: 'Roles', icon: ShieldCheckIcon, path: 'roles' as PageType, group: 'administracao' },
            { label: 'Permissões', icon: ShieldCheckIcon, path: 'permissions' as PageType, group: 'administracao' },
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
      ]
    },
    {
      name: 'Relatórios',
      icon: ChartBarIcon,
      color: 'emerald',
      items: [
        { label: 'Relatórios', icon: ChartBarIcon, path: 'reports' as PageType, group: 'relatorios' },
      ]
    },
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
        className={`fixed inset-y-0 left-0 z-50 bg-white shadow-lg transform transition-all duration-300 ease-in-out flex flex-col ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full'
        } ${drawerCollapsed ? 'w-16' : 'w-64'} md:translate-x-0`}
      >
        <div className={`flex items-center border-b border-gray-200 transition-all duration-300 ${
          drawerCollapsed ? 'p-2 justify-center' : 'p-6'
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
            className={`text-gray-500 hover:text-indigo-600 ${drawerCollapsed ? 'p-1' : 'p-2'} rounded-lg hover:bg-white/60 transition-all duration-200 ${
              drawerCollapsed ? 'ml-0' : 'ml-auto'
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
              className={`flex items-center w-full transition-colors rounded-lg ${
                drawerCollapsed ? 'px-1 py-3 justify-center' : 'px-3 py-3'
              } ${
                currentPage === 'dashboard'
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
                  className={`flex items-center w-full transition-colors rounded-lg ${
                    drawerCollapsed ? 'px-1 py-3 justify-center' : 'px-3 py-3'
                  } ${
                    currentPage === item.path
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
              className={`flex items-center w-full transition-colors rounded-lg ${
                drawerCollapsed ? 'px-1 py-3 justify-center' : 'px-3 py-3'
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
      <div className={`flex-1 flex flex-col overflow-hidden transition-all duration-300 ${
        drawerCollapsed ? 'md:ml-16' : 'md:ml-64'
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

            <div className="flex items-center space-x-2 sm:space-x-4">
              <div>
                <CompanySelector />
              </div>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto bg-gray-50 p-2 sm:p-3 md:p-4 lg:p-6">
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