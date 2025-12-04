import { Typography, Box } from '@mui/material';
import React from 'react';
import { Link } from 'react-router-dom';

const Home = () => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-1 sm:px-2 md:px-6 lg:px-8">
          <div className="flex justify-between items-center py-2 sm:py-3 md:py-4">
            <div className="flex items-center">
            </div>
            <div className="flex items-center space-x-1 sm:space-x-2 md:space-x-3 lg:space-x-4">
              <Link
                to="/client-login"
                className="text-blue-600 hover:text-blue-800 font-medium text-xs sm:text-sm md:text-base px-1 sm:px-2 md:px-3 py-1 sm:py-2 border border-blue-600 rounded-md"
              >
                Portal do Cliente
              </Link>
              <Link
                to="/login"
                className="text-indigo-600 hover:text-indigo-800 font-medium text-xs sm:text-sm md:text-base px-1 sm:px-2 md:px-3 py-1 sm:py-2"
              >
                Entrar
              </Link>
              <Link
                to="/register"
                className="bg-indigo-600 text-white px-1 sm:px-2 md:px-3 lg:px-4 py-1 sm:py-2 rounded-md hover:bg-indigo-700 font-medium text-xs sm:text-sm md:text-base"
              >
                Criar Conta
              </Link>
            </div>
          </div>
        </div>
      </header>

      <Box
        sx={{
          display: 'flex',
          flexDirection: { xs: 'column', sm: 'row' },
          alignItems: 'center',
          justifyContent: 'center',
          mt: 2,
          px: 2,
        }}
      >
        <Box
          component="img"
          src={process.env.PUBLIC_URL + '/logo_retangular.png'}
          alt="Brazcom ISP Logo"
          sx={{
            height: { xs: 80, sm: 120, md: 150 },
            width: 'auto',
            mr: { xs: 0, sm: 2 },
            mb: { xs: 1, sm: 0 },
            display: 'block',
          }}
        />

        {/*<Box sx={{ textAlign: { xs: 'center', sm: 'left' } }}>
          <Box component="header">
            <Typography
              variant="h4"
              component="div"
              className="text-indigo-600"
              sx={{ fontWeight: 900, lineHeight: 1 }}
            >
              Brazcom
            </Typography>
            <Typography
              variant="subtitle1"
              component="div"
              className="text-indigo-600"
              sx={{ fontWeight: 700, fontSize: { xs: '0.95rem', sm: '1.25rem' } }}
            >
              ISP Suite
            </Typography>
          </Box>
        </Box>*/}
      </Box>

      {/* Hero Section */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 sm:py-4 md:py-4 lg:py-4">
        <div className="text-center">
          <h2 className="text-xl sm:text-2xl md:text-3xl lg:text-4xl xl:text-5xl font-bold text-gray-900 mb-3 sm:mb-4 md:mb-6 leading-tight">
            <span className="text-indigo-600 block">Gestão de Provedores de Internet</span>
          </h2>
          <p className="text-sm sm:text-base md:text-lg lg:text-xl text-gray-600 mb-4 sm:mb-6 md:mb-8 max-w-3xl mx-auto leading-relaxed">
             Administração de aspectos técnicos, financeiros e operacionais, com o objetivo de otimizar serviços, reter clientes e garantir o crescimento do negócio.<br className="hidden sm:block" />
             Gerencie planos, clientes e infraestrutura, o acompanhamento de indicadores de desempenho e a implementação de estratégias para melhorar a satisfação e fidelização dos clientes. 
          </p>
          <div className="flex flex-col sm:flex-row gap-2 sm:gap-3 md:gap-4 justify-center">
            <Link
              to="/client-login"
              className="bg-blue-600 text-white px-4 sm:px-6 md:px-8 py-2 sm:py-3 rounded-lg text-sm sm:text-base md:text-lg font-semibold hover:bg-blue-700 transition-colors"
            >
              Portal do Cliente
            </Link>
            <Link
              to="/register"
              className="bg-indigo-600 text-white px-4 sm:px-6 md:px-8 py-2 sm:py-3 rounded-lg text-sm sm:text-base md:text-lg font-semibold hover:bg-indigo-700 transition-colors"
            >
              Começar Gratuitamente
            </Link>
            <Link
              to="#planos"
              className="border-2 border-indigo-600 text-indigo-600 px-4 sm:px-6 md:px-8 py-2 sm:py-3 rounded-lg text-sm sm:text-base md:text-lg font-semibold hover:bg-indigo-700 hover:text-white transition-colors"
            >
              Ver Planos
            </Link>
          </div>
        </div>

        {/* Empresas Section */}
        <div className="mt-6 sm:mt-8 md:mt-12 lg:mt-20">
          <h3 className="text-lg sm:text-xl md:text-2xl lg:text-3xl font-bold text-center text-gray-900 mb-4 sm:mb-6 md:mb-8 lg:mb-12 px-0">
            Principais áreas da gestão
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 md:gap-6 lg:gap-8 px-0">
            <div className="bg-white p-4 sm:p-6 rounded-lg shadow-md hover:shadow-lg transition-shadow">
              <div className="w-10 h-10 sm:w-12 sm:h-12 bg-blue-100 rounded-lg flex items-center justify-center mb-3 sm:mb-4">
                <svg className="w-5 h-5 sm:w-6 sm:h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </div>
              <h4 className="text-base sm:text-lg md:text-xl font-semibold text-gray-900 mb-2">Técnica e operacional</h4>
              <p className="text-gray-600 text-sm sm:text-base">Gerenciar a infraestrutura de rede, monitorar conexões, configurar roteadores e lidar com o suporte técnico para resolver problemas de forma rápida.</p>
            </div>

            <div className="bg-white p-4 sm:p-6 rounded-lg shadow-md hover:shadow-lg transition-shadow">
              <div className="w-10 h-10 sm:w-12 sm:h-12 bg-green-100 rounded-lg flex items-center justify-center mb-3 sm:mb-4">
                <svg className="w-5 h-5 sm:w-6 sm:h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h4 className="text-base sm:text-lg md:text-xl font-semibold text-gray-900 mb-2">Financeira</h4>
              <p className="text-gray-600 text-sm sm:text-base">Controlar o fluxo de caixa, gerenciar faturas e inadimplência, planejar o orçamento e garantir que os valores cobrados estejam alinhados com os custos de instalação e manutenção.</p>
            </div>

            <div className="bg-white p-4 sm:p-6 rounded-lg shadow-md hover:shadow-lg transition-shadow">
              <div className="w-10 h-10 sm:w-12 sm:h-12 bg-purple-100 rounded-lg flex items-center justify-center mb-3 sm:mb-4">
                <svg className="w-5 h-5 sm:w-6 sm:h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z" />
                </svg>
              </div>
              <h4 className="text-base sm:text-lg md:text-xl font-semibold text-gray-900 mb-2">Comercial e de relacionamento</h4>
              <p className="text-gray-600 text-sm sm:text-base">Definir planos de serviço, negociar contratos, gerenciar o relacionamento com os clientes e criar estratégias para aumentar a retenção e a satisfação. </p>
            </div>

            <div className="bg-white p-4 sm:p-6 rounded-lg shadow-md hover:shadow-lg transition-shadow">
              <div className="w-12 h-12 bg-red-100 rounded-lg flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                </svg>
              </div>
              <h4 className="text-lg sm:text-xl font-semibold text-gray-900 mb-2">Sucesso do cliente</h4>
              <p className="text-gray-600 text-sm sm:text-base">Criar uma cultura de satisfação que vai além do atendimento de problemas, buscando garantir que o cliente obtenha valor máximo do serviço.</p>
            </div>

            <div className="bg-white p-4 sm:p-6 rounded-lg shadow-md hover:shadow-lg transition-shadow">
              <div className="w-12 h-12 bg-yellow-100 rounded-lg flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <h4 className="text-lg sm:text-xl font-semibold text-gray-900 mb-2">Documentação digital</h4>
              <p className="text-gray-600 text-sm sm:text-base">Manter registros digitais de todos os processos, como a documentação da rede e do gerenciamento de ativos.</p>
            </div>

            <div className="bg-white p-4 sm:p-6 rounded-lg shadow-md hover:shadow-lg transition-shadow">
              <div className="w-10 h-10 sm:w-12 sm:h-12 bg-indigo-100 rounded-lg flex items-center justify-center mb-3 sm:mb-4">
                <svg className="w-5 h-5 sm:w-6 sm:h-6 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <h4 className="text-base sm:text-lg md:text-xl font-semibold text-gray-900 mb-2">Indicadores de desempenho</h4>
              <p className="text-gray-600 text-sm sm:text-base">Acompanhar métricas de crescimento, taxa de cancelamento e satisfação do cliente para tomar decisões estratégicas.</p>
            </div>
          </div>
        </div>

        {/* Features Section */}
        <div className="mt-6 sm:mt-8 md:mt-12 lg:mt-20 px-0">
          <h3 className="text-lg sm:text-xl md:text-2xl lg:text-3xl font-bold text-center text-gray-900 mb-4 sm:mb-6 md:mb-8 lg:mb-12">
            Por que escolher Brazcom ISP Suite?
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4 md:gap-6 lg:gap-8">
            <div className="bg-white p-4 sm:p-6 rounded-lg shadow-md">
              <div className="w-10 h-10 sm:w-12 sm:h-12 bg-indigo-100 rounded-lg flex items-center justify-center mb-3 sm:mb-4">
                <svg className="w-5 h-5 sm:w-6 sm:h-6 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h4 className="text-base sm:text-lg md:text-xl font-semibold text-gray-900 mb-2">Conformidade Fiscal</h4>
              <p className="text-gray-600 text-sm sm:text-base">Mantenha-se 100% compliant com a legislação fiscal brasileira. Evite multas e problemas com o fisco.</p>
            </div>

            <div className="bg-white p-4 sm:p-6 rounded-lg shadow-md">
              <div className="w-10 h-10 sm:w-12 sm:h-12 bg-indigo-100 rounded-lg flex items-center justify-center mb-3 sm:mb-4">
                <svg className="w-5 h-5 sm:w-6 sm:h-6 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <h4 className="text-base sm:text-lg md:text-xl font-semibold text-gray-900 mb-2">Automação Completa</h4>
              <p className="text-gray-600 text-sm sm:text-base">Emita NFCom automaticamente, limine processos manuais demorados.</p>
            </div>

            <div className="bg-white p-4 sm:p-6 rounded-lg shadow-md">
              <div className="w-10 h-10 sm:w-12 sm:h-12 bg-indigo-100 rounded-lg flex items-center justify-center mb-3 sm:mb-4">
                <svg className="w-5 h-5 sm:w-6 sm:h-6 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <h4 className="text-base sm:text-lg md:text-xl font-semibold text-gray-900 mb-2">Relatórios Avançados</h4>
              <p className="text-gray-600 text-sm sm:text-base">Dashboards completos com análise de faturamento, clientes e performance fiscal.</p>
            </div>
          </div>
        </div>

        {/* Pricing Section */}
        <div id="planos" className="mt-6 sm:mt-8 md:mt-12 lg:mt-20 px-0">
          <h3 className="text-lg sm:text-xl md:text-2xl lg:text-3xl font-bold text-center text-gray-900 mb-2 sm:mb-3 md:mb-4">
            Planos e Preços
          </h3>
          <p className="text-center text-gray-600 mb-4 sm:mb-6 md:mb-8 lg:mb-12 max-w-2xl mx-auto text-xs sm:text-sm md:text-base px-4">
            Escolha o plano ideal para seu negócio. Comece gratuitamente e faça upgrade quando precisar.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 md:gap-6 lg:gap-8">
            {/* Plano Gratuito */}
            <div className="bg-white rounded-lg shadow-md p-4 sm:p-6 border-2 border-gray-200">
              <div className="text-center">
                <h4 className="text-base sm:text-lg font-semibold text-gray-900">Gratuito</h4>
                <div className="mt-4">
                  <span className="text-3xl sm:text-4xl font-bold">R$ 0</span>
                  <span className="text-gray-600 text-sm sm:text-base">/mês</span>
                </div>
                <p className="text-gray-600 mt-2 text-sm">Para começar</p>
              </div>
              <ul className="mt-4 sm:mt-6 space-y-2 sm:space-y-3">
                <li className="flex items-center text-sm">
                  <svg className="w-4 h-4 sm:w-5 sm:h-5 text-green-500 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  Até 10 NFCom/mês
                </li>
                <li className="flex items-center text-sm">
                  <svg className="w-4 h-4 sm:w-5 sm:h-5 text-green-500 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  1 empresa
                </li>
                <li className="flex items-center text-sm">
                  <svg className="w-4 h-4 sm:w-5 sm:h-5 text-green-500 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  Suporte por email
                </li>
              </ul>
              <div className="mt-4 sm:mt-6">
                <Link
                  to="/register"
                  className="w-full bg-gray-100 text-gray-900 px-3 sm:px-4 py-2 rounded-md hover:bg-gray-200 text-center block font-medium text-sm sm:text-base"
                >
                  Começar Gratuitamente
                </Link>
              </div>
            </div>

            {/* Plano Básico */}
            <div className="bg-white rounded-lg shadow-md p-4 sm:p-6 border-2 border-indigo-200 relative">
              <div className="absolute top-0 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
                <span className="bg-indigo-600 text-white px-2 sm:px-3 py-1 rounded-full text-xs sm:text-sm font-medium">
                  Mais Popular
                </span>
              </div>
              <div className="text-center">
                <h4 className="text-base sm:text-lg font-semibold text-gray-900">Básico</h4>
                <div className="mt-3 sm:mt-4">
                  <span className="text-3xl sm:text-4xl font-bold">R$ 49</span>
                  <span className="text-gray-600 text-sm sm:text-base">/mês</span>
                </div>
                <p className="text-gray-600 mt-1 sm:mt-2 text-sm sm:text-base">Para pequenos negócios</p>
              </div>
              <ul className="mt-4 sm:mt-6 space-y-2 sm:space-y-3">
                <li className="flex items-center text-sm sm:text-base">
                  <svg className="w-4 h-4 sm:w-5 sm:h-5 text-green-500 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  Até 500 NFCom/mês
                </li>
                <li className="flex items-center text-sm sm:text-base">
                  <svg className="w-4 h-4 sm:w-5 sm:h-5 text-green-500 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  Até 3 empresas
                </li>
                <li className="flex items-center text-sm sm:text-base">
                  <svg className="w-4 h-4 sm:w-5 sm:h-5 text-green-500 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  Relatórios básicos
                </li>
                <li className="flex items-center text-sm sm:text-base">
                  <svg className="w-4 h-4 sm:w-5 sm:h-5 text-green-500 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  Suporte prioritário
                </li>
              </ul>
              <div className="mt-4 sm:mt-6">
                <Link
                  to="/register"
                  className="w-full bg-indigo-600 text-white px-4 py-3 sm:py-2 rounded-md hover:bg-indigo-700 text-center block font-medium text-sm sm:text-base"
                >
                  Escolher Básico
                </Link>
              </div>
            </div>

            {/* Plano Profissional */}
            <div className="bg-white rounded-lg shadow-md p-4 sm:p-6 border-2 border-gray-200">
              <div className="text-center">
                <h4 className="text-base sm:text-lg font-semibold text-gray-900">Profissional</h4>
                <div className="mt-3 sm:mt-4">
                  <span className="text-3xl sm:text-4xl font-bold">R$ 149</span>
                  <span className="text-gray-600 text-sm sm:text-base">/mês</span>
                </div>
                <p className="text-gray-600 mt-1 sm:mt-2 text-sm sm:text-base">Para médias empresas</p>
              </div>
              <ul className="mt-4 sm:mt-6 space-y-2 sm:space-y-3">
                <li className="flex items-center text-sm sm:text-base">
                  <svg className="w-4 h-4 sm:w-5 sm:h-5 text-green-500 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  Até 2.000 NFCom/mês
                </li>
                <li className="flex items-center text-sm sm:text-base">
                  <svg className="w-4 h-4 sm:w-5 sm:h-5 text-green-500 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  Até 10 empresas
                </li>
                <li className="flex items-center text-sm sm:text-base">
                  <svg className="w-4 h-4 sm:w-5 sm:h-5 text-green-500 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  API completa
                </li>
                <li className="flex items-center text-sm sm:text-base">
                  <svg className="w-4 h-4 sm:w-5 sm:h-5 text-green-500 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  Integração ERP
                </li>
                <li className="flex items-center text-sm sm:text-base">
                  <svg className="w-4 h-4 sm:w-5 sm:h-5 text-green-500 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  Suporte por telefone
                </li>
              </ul>
              <div className="mt-4 sm:mt-6">
                <Link
                  to="/register"
                  className="w-full bg-gray-100 text-gray-900 px-4 py-3 sm:py-2 rounded-md hover:bg-gray-200 text-center block font-medium text-sm sm:text-base"
                >
                  Escolher Profissional
                </Link>
              </div>
            </div>

            {/* Plano Enterprise */}
            <div className="bg-white rounded-lg shadow-md p-4 sm:p-6 border-2 border-gray-200">
              <div className="text-center">
                <h4 className="text-base sm:text-lg font-semibold text-gray-900">Enterprise</h4>
                <div className="mt-3 sm:mt-4">
                  <span className="text-2xl sm:text-3xl font-bold">Sob Consulta</span>
                </div>
                <p className="text-gray-600 mt-1 sm:mt-2 text-sm sm:text-base">Para grandes corporações</p>
              </div>
              <ul className="mt-4 sm:mt-6 space-y-2 sm:space-y-3">
                <li className="flex items-center text-sm sm:text-base">
                  <svg className="w-4 h-4 sm:w-5 sm:h-5 text-green-500 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  NFCom ilimitadas
                </li>
                <li className="flex items-center text-sm sm:text-base">
                  <svg className="w-4 h-4 sm:w-5 sm:h-5 text-green-500 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  Empresas ilimitadas
                </li>
                <li className="flex items-center text-sm sm:text-base">
                  <svg className="w-4 h-4 sm:w-5 sm:h-5 text-green-500 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  SLA garantido
                </li>
                <li className="flex items-center text-sm sm:text-base">
                  <svg className="w-4 h-4 sm:w-5 sm:h-5 text-green-500 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  Consultoria dedicada
                </li>
                <li className="flex items-center text-sm sm:text-base">
                  <svg className="w-4 h-4 sm:w-5 sm:h-5 text-green-500 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  Infraestrutura dedicada
                </li>
              </ul>
              <div className="mt-4 sm:mt-6">
                <a
                  href="mailto:contato@nfcom.com.br"
                  className="w-full bg-gray-100 text-gray-900 px-4 py-3 sm:py-2 rounded-md hover:bg-gray-200 text-center block font-medium text-sm sm:text-base"
                >
                  Fale Conosco
                </a>
              </div>
            </div>
          </div>
        </div>

        {/* Testimonials Section */}
        <div className="mt-8 sm:mt-12 md:mt-16 lg:mt-20 px-0">
          <h3 className="text-lg sm:text-xl md:text-2xl lg:text-3xl font-bold text-center text-gray-900 mb-4 sm:mb-6 md:mb-8 lg:mb-12">
            O que nossos clientes dizem
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6 md:gap-8">
            <div className="bg-white p-4 sm:p-6 rounded-lg shadow-md">
              <div className="flex items-center mb-3 sm:mb-4">
                <div className="w-10 h-10 sm:w-12 sm:h-12 bg-indigo-100 rounded-full flex items-center justify-center flex-shrink-0">
                  <span className="text-indigo-600 font-semibold text-sm sm:text-base">R</span>
                </div>
                <div className="ml-3 sm:ml-4">
                  <h4 className="font-semibold text-gray-900 text-sm sm:text-base">Rádio Comunitária FM</h4>
                  <p className="text-gray-600 text-xs sm:text-sm">São Paulo, SP</p>
                </div>
              </div>
              <p className="text-gray-600 italic text-sm sm:text-base">
                "O NFCom revolucionou nossa gestão fiscal. Antes levávamos horas para emitir uma NFCom,
                agora é automático e sem erros."
              </p>
            </div>

            <div className="bg-white p-4 sm:p-6 rounded-lg shadow-md">
              <div className="flex items-center mb-3 sm:mb-4">
                <div className="w-10 h-10 sm:w-12 sm:h-12 bg-green-100 rounded-full flex items-center justify-center flex-shrink-0">
                  <span className="text-green-600 font-semibold text-sm sm:text-base">J</span>
                </div>
                <div className="ml-3 sm:ml-4">
                  <h4 className="font-semibold text-gray-900 text-sm sm:text-base">Jornal Local</h4>
                  <p className="text-gray-600 text-xs sm:text-sm">Rio de Janeiro, RJ</p>
                </div>
              </div>
              <p className="text-gray-600 italic text-sm sm:text-base">
                "Conseguimos reduzir nossos custos operacionais em 40% e eliminar completamente
                as multas fiscais. Sistema excepcional!"
              </p>
            </div>

            <div className="bg-white p-4 sm:p-6 rounded-lg shadow-md">
              <div className="flex items-center mb-3 sm:mb-4">
                <div className="w-10 h-10 sm:w-12 sm:h-12 bg-purple-100 rounded-full flex items-center justify-center flex-shrink-0">
                  <span className="text-purple-600 font-semibold text-sm sm:text-base">I</span>
                </div>
                <div className="ml-3 sm:ml-4">
                  <h4 className="font-semibold text-gray-900 text-sm sm:text-base">Internet Provedor</h4>
                  <p className="text-gray-600 text-xs sm:text-sm">Belo Horizonte, MG</p>
                </div>
              </div>
              <p className="text-gray-600 italic text-sm sm:text-base">
                "A integração com nosso sistema de cobrança foi perfeita. Agora emitimos
                NFCom automaticamente para milhares de clientes."
              </p>
            </div>
          </div>
        </div>

        {/* Additional Features */}
        <div className="mt-8 sm:mt-12 md:mt-16 lg:mt-20 px-4">
          <h3 className="text-lg sm:text-xl md:text-2xl lg:text-3xl font-bold text-center text-gray-900 mb-4 sm:mb-6 md:mb-8 lg:mb-12">
            Recursos Avançados
          </h3>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 md:gap-6 lg:gap-8">
            <div className="text-center">
              <div className="w-12 h-12 sm:w-16 sm:h-16 bg-indigo-100 rounded-full flex items-center justify-center mx-auto mb-3 sm:mb-4">
                <svg className="w-6 h-6 sm:w-8 sm:h-8 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
              </div>
              <h4 className="font-semibold text-gray-900 mb-1 sm:mb-2 text-sm sm:text-base">API Completa</h4>
              <p className="text-gray-600 text-xs sm:text-sm">Integre com qualquer sistema através de nossa API RESTful</p>
            </div>

            <div className="text-center">
              <div className="w-12 h-12 sm:w-16 sm:h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-3 sm:mb-4">
                <svg className="w-6 h-6 sm:w-8 sm:h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
              </div>
              <h4 className="font-semibold text-gray-900 mb-1 sm:mb-2 text-sm sm:text-base">Segurança SSL</h4>
              <p className="text-gray-600 text-xs sm:text-sm">Transmissão criptografada e armazenamento seguro de dados</p>
            </div>

            <div className="text-center">
              <div className="w-12 h-12 sm:w-16 sm:h-16 bg-yellow-100 rounded-full flex items-center justify-center mx-auto mb-3 sm:mb-4">
                <svg className="w-6 h-6 sm:w-8 sm:h-8 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" />
                </svg>
              </div>
              <h4 className="font-semibold text-gray-900 mb-1 sm:mb-2 text-sm sm:text-base">Backup Automático</h4>
              <p className="text-gray-600 text-xs sm:text-sm">Seus dados sempre seguros com backup diário</p>
            </div>

            <div className="text-center">
              <div className="w-12 h-12 sm:w-16 sm:h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-3 sm:mb-4">
                <svg className="w-6 h-6 sm:w-8 sm:h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 5.636l-3.536 3.536m0 5.656l3.536 3.536M9.172 9.172L5.636 5.636m3.536 9.192L5.636 18.364M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h4 className="font-semibold text-gray-900 mb-1 sm:mb-2 text-sm sm:text-base">Suporte 24/7</h4>
              <p className="text-gray-600 text-xs sm:text-sm">Equipe técnica disponível para ajudar sempre que precisar</p>
            </div>
          </div>
        </div>

        {/* CTA Section */}
        <div className="mt-8 sm:mt-12 md:mt-16 lg:mt-20 mx-0 bg-indigo-600 rounded-lg p-4 sm:p-6 md:p-8 text-center text-white">
          <h3 className="text-lg sm:text-xl md:text-2xl lg:text-3xl font-bold mb-2 sm:mb-3 md:mb-4">Pronto para transformar seu provedor?</h3>
          <p className="text-sm sm:text-base md:text-lg lg:text-xl mb-3 sm:mb-4 md:mb-6 opacity-90">
            Junte-se a comunidade de provedores de comunicação que já confiam no Brazcom ISP Suite
          </p>
          <div className="flex flex-col sm:flex-row gap-2 sm:gap-3 md:gap-4 justify-center">
            <Link
              to="/register"
              className="bg-white text-indigo-600 px-4 sm:px-6 md:px-8 py-2 sm:py-3 rounded-lg text-sm sm:text-base md:text-lg font-semibold hover:bg-gray-100 transition-colors"
            >
              Começar Agora - Gratuitamente
            </Link>
            <a
              href="#planos"
              className="border-2 border-white text-white px-4 sm:px-6 md:px-8 py-2 sm:py-3 rounded-lg text-sm sm:text-base md:text-lg font-semibold hover:bg-white hover:text-indigo-600 transition-colors"
            >
              Ver Todos os Planos
            </a>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-gray-800 text-white py-4 sm:py-6 md:py-8 mt-8 sm:mt-12 md:mt-16 lg:mt-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6 md:gap-8">
            <div>
              <h4 className="text-base sm:text-lg md:text-xl font-semibold mb-2 sm:mb-3 md:mb-4">Brazcom NFCom</h4>
              <p className="text-gray-400 text-xs sm:text-sm">
                Sistema completo para emissão de Nota Fiscal de Comunicação (NFCom).
                Tecnologia de ponta para empresas de comunicação.
              </p>
            </div>
            <div>
              <h4 className="font-semibold mb-2 sm:mb-3 md:mb-4 text-sm sm:text-base">Produto</h4>
              <ul className="space-y-1 sm:space-y-2 text-xs sm:text-sm text-gray-400">
                <li><a href="#" className="hover:text-white">Recursos</a></li>
                <li><a href="#" className="hover:text-white">Preços</a></li>
                <li><a href="#" className="hover:text-white">API</a></li>
                <li><a href="#" className="hover:text-white">Integrações</a></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-2 sm:mb-3 md:mb-4 text-sm sm:text-base">Suporte</h4>
              <ul className="space-y-1 sm:space-y-2 text-xs sm:text-sm text-gray-400">
                <li><a href="#" className="hover:text-white">Documentação</a></li>
                <li><a href="#" className="hover:text-white">Central de Ajuda</a></li>
                <li><a href="#" className="hover:text-white">Contato</a></li>
                <li><a href="#" className="hover:text-white">Status</a></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-3 sm:mb-4">Empresa</h4>
              <p className="text-gray-400 text-sm mb-2">Brazcom Engenharia de Software</p>
              <ul className="space-y-2 text-sm text-gray-400">
                <li><a href="#" className="hover:text-white">Sobre nós</a></li>
                <li><a href="#" className="hover:text-white">Blog</a></li>
                <li><a href="#" className="hover:text-white">Carreiras</a></li>
                <li><a href="#" className="hover:text-white">Imprensa</a></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-gray-700 mt-4 sm:mt-6 md:mt-8 pt-4 sm:pt-6 md:pt-8 text-center text-gray-400 text-xs sm:text-sm">
            <div className="flex flex-col sm:flex-row items-center justify-center space-y-2 sm:space-y-0 sm:space-x-4">
              <Box
                component="img"
                src={process.env.PUBLIC_URL + '/logo_brazcom_sem_texto_escuro.svg'}
                alt="Brazcom Engenharia de Software Logo"
                sx={{
                  height: { xs: 24, sm: 32 },
                  width: 'auto',
                  //filter: 'brightness(0) invert(1)', // Para tornar branco no fundo escuro
                }}
              />
              <p>© 2025 Brazcom ISP Suite. Todos os direitos reservados. Desenvolvido por Brazcom Engenharia de Software.</p>
            </div>
            <div className="mt-2 sm:mt-3 md:mt-4 flex flex-col sm:flex-row justify-center space-y-1 sm:space-y-0 sm:space-x-4 md:space-x-6">
              <a href="#" className="hover:text-white text-xs sm:text-sm">Política de Privacidade</a>
              <a href="#" className="hover:text-white text-xs sm:text-sm">Termos de Uso</a>
              <a href="#" className="hover:text-white text-xs sm:text-sm">LGPD</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Home;