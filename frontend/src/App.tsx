import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom';
import { ThemeProvider, createTheme, CssBaseline } from '@mui/material';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { CompanyProvider } from './contexts/CompanyContext';
import { SnackbarProvider } from 'notistack';
import Home from './components/Home';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import Companies from './pages/Companies';
import Clients from './pages/Clients';
import NFCom from './pages/NFCom';
import Services from './pages/Services';
import Contracts from './pages/Contracts';
import Users from './pages/Users';
import Roles from './pages/Roles';
import Permissions from './pages/Permissions';
import Reports from './pages/Reports';
import Routers from './pages/Routers';
import RouterInterfaces from './pages/RouterInterfaces';
import IPClasses from './pages/IPClasses';
import PPPoE from './pages/PPPoE';
import DHCP from './pages/DHCP';
import AuthenticatedLayout from './components/AuthenticatedLayout';
import { PageType } from './types';

// Tema personalizado para NFCom
const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
      dark: '#115293',
      light: '#42a5f5',
    },
    secondary: {
      main: '#dc004e',
      dark: '#9a0036',
      light: '#e33371',
    },
    background: {
      default: '#f5f5f5',
      paper: '#ffffff',
    },
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
    h1: {
      fontWeight: 600,
    },
    h2: {
      fontWeight: 600,
    },
  },
  shape: {
    borderRadius: 8,
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 600,
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
        },
      },
    },
  },
});

// Componente de rota protegida
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return <div className="flex items-center justify-center min-h-screen">
      <div className="text-lg">Carregando...</div>
    </div>;
  }

  return isAuthenticated ? <>{children}</> : <Navigate to="/login" />;
};

// Componente de rota pública
const PublicRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return <div className="flex items-center justify-center min-h-screen">
      <div className="text-lg">Carregando...</div>
    </div>;
  }

  return !isAuthenticated ? <>{children}</> : <Navigate to="/dashboard" />;
};

// Layout para páginas autenticadas
const AuthenticatedApp: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const navigate = useNavigate();
  const location = useLocation();

  const getCurrentPage = (): PageType => {
    const path = location.pathname;
    if (path === '/dashboard') return 'dashboard';
    if (path === '/clients') return 'clients';
  if (path.startsWith('/companies')) return 'companies';
  if (path === '/contracts') return 'contracts';
    if (path === '/services') return 'services';
    if (path.startsWith('/nfcom')) return 'nfcom';
    if (path.startsWith('/users')) return 'users';
    if (path.startsWith('/roles')) return 'roles';
    if (path.startsWith('/permissions')) return 'permissions';
    if (path.startsWith('/reports')) return 'reports';
    if (path === '/routers') return 'routers';
    if (path === '/ip-classes') return 'ip-classes';
    if (path === '/pppoe') return 'pppoe';
    if (path === '/dhcp') return 'dhcp';
    if (path === '/profile') return 'profile';
    return 'dashboard';
  };

  const handleNavigate = (page: PageType) => {
    if (page === 'dashboard') navigate('/dashboard');
    else if (page === 'clients') navigate('/clients');
  else if (page === 'companies') navigate('/companies');
  else if (page === 'contracts') navigate('/contracts');
    else if (page === 'services') navigate('/services');
    else if (page === 'nfcom') navigate('/nfcom');
    else if (page === 'users') navigate('/users');
    else if (page === 'roles') navigate('/roles');
    else if (page === 'permissions') navigate('/permissions');
    else if (page === 'reports') navigate('/reports');
    else if (page === 'routers') navigate('/routers');
    else if (page === 'ip-classes') navigate('/ip-classes');
    else if (page === 'pppoe') navigate('/pppoe');
    else if (page === 'dhcp') navigate('/dhcp');
    else if (page === 'profile') navigate('/profile');
  };

  return (
    <AuthenticatedLayout
      currentPage={getCurrentPage()}
      onNavigate={handleNavigate}
    >
      {children}
    </AuthenticatedLayout>
  );
};

const AppContent: React.FC = () => {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route
        path="/login"
        element={
          <PublicRoute>
            <Login />
          </PublicRoute>
        }
      />
      <Route
        path="/register"
        element={
          <PublicRoute>
            <Register />
          </PublicRoute>
        }
      />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <AuthenticatedApp>
              <Dashboard />
            </AuthenticatedApp>
          </ProtectedRoute>
        }
      />
      <Route
        path="/companies"
        element={
          <ProtectedRoute>
            <AuthenticatedApp>
              <Companies />
            </AuthenticatedApp>
          </ProtectedRoute>
        }
      />
      <Route
        path="/clients"
        element={
          <ProtectedRoute>
            <AuthenticatedApp>
              <Clients />
            </AuthenticatedApp>
          </ProtectedRoute>
        }
      />
      <Route
        path="/nfcom"
        element={
          <ProtectedRoute>
            <AuthenticatedApp>
              <NFCom />
            </AuthenticatedApp>
          </ProtectedRoute>
        }
      />
      <Route
        path="/services"
        element={
          <ProtectedRoute>
            <AuthenticatedApp>
              <Services />
            </AuthenticatedApp>
          </ProtectedRoute>
        }
      />
      <Route
        path="/contracts"
        element={
          <ProtectedRoute>
            <AuthenticatedApp>
              <Contracts />
            </AuthenticatedApp>
          </ProtectedRoute>
        }
      />
      <Route
        path="/users"
        element={
          <ProtectedRoute>
            <AuthenticatedApp>
              <Users />
            </AuthenticatedApp>
          </ProtectedRoute>
        }
      />
      <Route
        path="/roles"
        element={
          <ProtectedRoute>
            <AuthenticatedApp>
              <Roles />
            </AuthenticatedApp>
          </ProtectedRoute>
        }
      />
      <Route
        path="/permissions"
        element={
          <ProtectedRoute>
            <AuthenticatedApp>
              <Permissions />
            </AuthenticatedApp>
          </ProtectedRoute>
        }
      />
      <Route
        path="/reports"
        element={
          <ProtectedRoute>
            <AuthenticatedApp>
              <Reports />
            </AuthenticatedApp>
          </ProtectedRoute>
        }
      />
      <Route
        path="/routers"
        element={
          <ProtectedRoute>
            <AuthenticatedApp>
              <Routers />
            </AuthenticatedApp>
          </ProtectedRoute>
        }
      />
      <Route
        path="/routers/:routerId/interfaces"
        element={
          <ProtectedRoute>
            <AuthenticatedApp>
              <RouterInterfaces />
            </AuthenticatedApp>
          </ProtectedRoute>
        }
      />
      <Route
        path="/ip-classes"
        element={
          <ProtectedRoute>
            <AuthenticatedApp>
              <IPClasses />
            </AuthenticatedApp>
          </ProtectedRoute>
        }
      />
      <Route
        path="/pppoe"
        element={
          <ProtectedRoute>
            <AuthenticatedApp>
              <PPPoE />
            </AuthenticatedApp>
          </ProtectedRoute>
        }
      />
      <Route
        path="/dhcp"
        element={
          <ProtectedRoute>
            <AuthenticatedApp>
              <DHCP />
            </AuthenticatedApp>
          </ProtectedRoute>
        }
      />
    </Routes>
  );
};

const App: React.FC = () => {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <AuthProvider>
        <CompanyProvider>
          <SnackbarProvider maxSnack={3} anchorOrigin={{ vertical: 'top', horizontal: 'right' }}>
            <Router>
              <AppContent />
            </Router>
          </SnackbarProvider>
        </CompanyProvider>
      </AuthProvider>
    </ThemeProvider>
  );
};

export default App;