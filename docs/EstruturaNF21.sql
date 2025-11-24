CREATE DATABASE  IF NOT EXISTS `nf21` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;
USE `nf21`;
-- MySQL dump 10.13  Distrib 8.0.42, for Win64 (x86_64)
--
-- Host: localhost    Database: nf21
-- ------------------------------------------------------
-- Server version	8.1.0

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `administradores`
--

DROP TABLE IF EXISTS `administradores`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `administradores` (
  `id` int NOT NULL AUTO_INCREMENT,
  `id_user` int NOT NULL,
  `id_federacao` int NOT NULL,
  `nivel` tinyint NOT NULL DEFAULT '0',
  `ativo` tinyint NOT NULL DEFAULT '1' COMMENT '    # 0 = atleta\n    # 1 = presidente nacional\n    # 2 = secretário nacional\n    # 3 = presidente estadual\n    # 4 = secretario estadual\n',
  PRIMARY KEY (`id`),
  UNIQUE KEY `un_adminstrador` (`id_user`,`id_federacao`),
  KEY `id_federacao` (`id_federacao`),
  CONSTRAINT `administradores_ibfk_1` FOREIGN KEY (`id_federacao`) REFERENCES `federacoes` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `administradores_ibfk_2` FOREIGN KEY (`id_user`) REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `atletas`
--

DROP TABLE IF EXISTS `atletas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `atletas` (
  `id` int NOT NULL AUTO_INCREMENT,
  `email` varchar(100) NOT NULL,
  `equipe` varchar(50) DEFAULT NULL,
  `id_federacao` int DEFAULT NULL COMMENT 'ID da sigla da federação',
  `nome` varchar(50) NOT NULL,
  `CPF` varchar(14) DEFAULT NULL,
  `data_cadastro` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `cep` varchar(9) DEFAULT NULL,
  `endereco` varchar(50) DEFAULT NULL,
  `numero` varchar(5) DEFAULT 'SN',
  `complemento` varchar(15) DEFAULT NULL,
  `bairro` varchar(30) DEFAULT NULL,
  `cidade` varchar(50) DEFAULT NULL,
  `uf` varchar(2) DEFAULT NULL,
  `whatsapp` varchar(15) DEFAULT NULL COMMENT 'Número do whatsapp',
  `data_nascimento` date DEFAULT NULL,
  `peso` decimal(5,1) DEFAULT '0.0' COMMENT 'Em kg',
  `altura` decimal(5,1) DEFAULT '0.0' COMMENT 'Em centímetros\\\\\\\\n',
  PRIMARY KEY (`id`),
  KEY `fk_atletas_sigla_idx` (`id_federacao`),
  CONSTRAINT `fk_atletas_federacao` FOREIGN KEY (`id_federacao`) REFERENCES `federacoes` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `fk_atletas_sigla` FOREIGN KEY (`id_federacao`) REFERENCES `siglas` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cfop`
--

DROP TABLE IF EXISTS `cfop`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cfop` (
  `cfop` varchar(5) NOT NULL,
  `descricao` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`cfop`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `clientes`
--

DROP TABLE IF EXISTS `clientes`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `clientes` (
  `id` int NOT NULL AUTO_INCREMENT,
  `id_user` int DEFAULT NULL COMMENT 'Id do usuário que cadastrou a empresa e é o único que pode alterar. Um cliente pode ser usado em várias empresas diferentes por causa do CNPJ único',
  `cnpj` varchar(18) NOT NULL,
  `inscricao` varchar(18) NOT NULL DEFAULT 'ISENTO',
  `nome` varchar(50) NOT NULL,
  `cep` varchar(9) DEFAULT NULL,
  `endereco` varchar(50) DEFAULT NULL,
  `numero` varchar(5) DEFAULT 'SN',
  `complemento` varchar(15) DEFAULT NULL,
  `bairro` varchar(30) DEFAULT NULL,
  `cidade` varchar(50) DEFAULT NULL,
  `uf` varchar(2) DEFAULT NULL,
  `telefone` varchar(15) DEFAULT NULL,
  `data_cadastro` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `ativo` tinyint DEFAULT '1',
  `ibge` varchar(7) DEFAULT '4128500' COMMENT 'Código do IBGE',
  `email` varchar(100) DEFAULT NULL,
  `obs` varchar(200) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `cnpj_UNIQUE` (`cnpj`),
  KEY `fk_clientes_user_idx` (`id_user`),
  CONSTRAINT `fk_clientes_user` FOREIGN KEY (`id_user`) REFERENCES `users` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=3566 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='DADOS CADASTRAIS DO DESTINATÁRIO DO DOCUMENTO FISCAL';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `compras`
--

DROP TABLE IF EXISTS `compras`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `compras` (
  `id` int NOT NULL AUTO_INCREMENT,
  `id_federacao` int NOT NULL,
  `id_user` int NOT NULL,
  `data_emissao` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `data_pagamento` datetime DEFAULT NULL,
  `pago` tinyint NOT NULL DEFAULT '0',
  `id_payment` bigint DEFAULT NULL COMMENT 'Número de identificação do pagamento no banco (mercado pago)',
  `status` varchar(45) DEFAULT NULL COMMENT 'Status enviado pelo banco (mercado pago)',
  `obs` varchar(50) DEFAULT NULL,
  `token` varchar(100) DEFAULT NULL COMMENT 'Token de autorização pelo banco (mercado pago - cartão de crédito)',
  PRIMARY KEY (`id`),
  KEY `id_user` (`id_user`),
  KEY `id_federacao` (`id_federacao`),
  CONSTRAINT `compras_ibfk_1` FOREIGN KEY (`id_user`) REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `compras_ibfk_2` FOREIGN KEY (`id_federacao`) REFERENCES `federacoes` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=24 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='um usuário pode comprar produtos sem ser atleta';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `contadores`
--

DROP TABLE IF EXISTS `contadores`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `contadores` (
  `id_user` int NOT NULL COMMENT 'Permitido apenas um contador para um usuário',
  `nome` varchar(50) NOT NULL,
  `cpf` varchar(14) NOT NULL,
  `cnpj` varchar(18) DEFAULT NULL,
  `crc` varchar(18) NOT NULL DEFAULT 'ISENTO',
  `email` varchar(100) NOT NULL,
  `cep` varchar(9) NOT NULL,
  `endereco` varchar(50) DEFAULT NULL,
  `numero` varchar(5) NOT NULL DEFAULT 'SN',
  `complemento` varchar(15) DEFAULT NULL,
  `bairro` varchar(30) DEFAULT NULL,
  `cidade` varchar(50) NOT NULL,
  `uf` varchar(2) NOT NULL,
  `telefone` varchar(15) DEFAULT NULL,
  `fax` varchar(15) DEFAULT NULL,
  `data_cadastro` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `ibge` varchar(7) NOT NULL DEFAULT '4128500' COMMENT 'Código do IBGE',
  PRIMARY KEY (`id_user`),
  CONSTRAINT `fk_contadores_users` FOREIGN KEY (`id_user`) REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='Permitido apenas um contador para um usuário';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `dispositivos_autorizados`
--

DROP TABLE IF EXISTS `dispositivos_autorizados`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dispositivos_autorizados` (
  `id` int NOT NULL AUTO_INCREMENT,
  `id_user` int NOT NULL,
  `username` varchar(50) NOT NULL,
  `ip` varchar(50) NOT NULL,
  `data` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `user_agent` varchar(200) NOT NULL COMMENT 'Identifica a origem da conexão com dados do navegador, SO, etc',
  `autorizado` tinyint NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `id_user` (`id_user`),
  CONSTRAINT `dispositivos_autorizados_ibfk_1` FOREIGN KEY (`id_user`) REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=327 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `divisoes`
--

DROP TABLE IF EXISTS `divisoes`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `divisoes` (
  `id` int NOT NULL AUTO_INCREMENT,
  `nome` varchar(45) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='Divisões de categorias';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `divisoes_rpa`
--

DROP TABLE IF EXISTS `divisoes_rpa`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `divisoes_rpa` (
  `id` int NOT NULL AUTO_INCREMENT,
  `id_divisao` int NOT NULL,
  `altura` int NOT NULL COMMENT 'Até essa altura: peso = altura-100+peso',
  `junior` int NOT NULL COMMENT 'Quantos kg a mais pode ter. Usar valor negativo para reduzir o peso',
  `senior` int DEFAULT NULL COMMENT 'Quantos kg a mais pode ter. Usar valor negativo para reduzir o peso',
  PRIMARY KEY (`id`),
  UNIQUE KEY `un_divisao` (`id_divisao`,`altura`),
  KEY `fk_divisao_idx` (`id_divisao`),
  CONSTRAINT `fk_divisao` FOREIGN KEY (`id_divisao`) REFERENCES `divisoes` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=21 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='Relação peso altura para cada divisão';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `empresa_selecionada`
--

DROP TABLE IF EXISTS `empresa_selecionada`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `empresa_selecionada` (
  `id_user` int NOT NULL,
  `cnpj` varchar(18) NOT NULL,
  `data` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id_user`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='Apenas um registro por usuário da última empresa que ele selecionou';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `empresas`
--

DROP TABLE IF EXISTS `empresas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `empresas` (
  `id` int NOT NULL AUTO_INCREMENT,
  `id_user` int DEFAULT NULL COMMENT 'ID do usuário que cadastrou a empresa e só ele pode alterar',
  `tipo_utilizacao` int DEFAULT NULL,
  `razao_social` varchar(50) NOT NULL,
  `fantasia` varchar(50) DEFAULT NULL,
  `cnpj` varchar(18) DEFAULT NULL,
  `inscricao` varchar(18) NOT NULL DEFAULT 'ISENTO',
  `email` varchar(100) NOT NULL,
  `logo` varchar(100) NOT NULL DEFAULT 'svg/profile.svg',
  `cep` varchar(9) NOT NULL,
  `endereco` varchar(50) DEFAULT NULL,
  `numero` varchar(5) NOT NULL DEFAULT 'SN',
  `complemento` varchar(15) DEFAULT NULL,
  `bairro` varchar(30) DEFAULT NULL,
  `cidade` varchar(50) NOT NULL,
  `uf` varchar(2) NOT NULL,
  `telefone` varchar(15) DEFAULT NULL,
  `data_cadastro` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `ativo` tinyint DEFAULT '0',
  `ibge` varchar(7) NOT NULL DEFAULT '4128500' COMMENT 'Código do IBGE',
  `observacao` varchar(500) DEFAULT NULL COMMENT 'Informações complementares da nota fiscal que deve ser atribuído para cada nova nota',
  PRIMARY KEY (`id`),
  UNIQUE KEY `un_empesas_cnpj` (`cnpj`),
  KEY `fk_empresa_user_idx` (`id_user`),
  CONSTRAINT `fk_empresa_user` FOREIGN KEY (`id_user`) REFERENCES `users` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=34 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `federacoes`
--

DROP TABLE IF EXISTS `federacoes`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `federacoes` (
  `id` int NOT NULL AUTO_INCREMENT,
  `id_user` int NOT NULL DEFAULT '1' COMMENT 'ID do usuário dono da federação',
  `email` varchar(200) NOT NULL,
  `nome` varchar(50) NOT NULL,
  `id_sigla` int DEFAULT NULL COMMENT 'Ex.: IFBB-SC',
  `dominio` varchar(100) DEFAULT NULL COMMENT 'Domínio da federação. Ex.: brazcom.com.br',
  `logo` varchar(100) DEFAULT 'img/ifbbsc.png',
  `ativo` tinyint DEFAULT '0',
  `cep` varchar(9) NOT NULL,
  `endereco` varchar(50) DEFAULT NULL,
  `numero` varchar(5) NOT NULL DEFAULT 'SN',
  `complemento` varchar(15) DEFAULT NULL,
  `bairro` varchar(30) DEFAULT NULL,
  `cidade` varchar(50) NOT NULL,
  `uf` varchar(2) NOT NULL,
  `whatsapp` varchar(15) NOT NULL COMMENT 'Número do whatsapp',
  `instagram` varchar(50) DEFAULT NULL,
  `cobrador` int NOT NULL DEFAULT '1' COMMENT 'quem vai efetuar as cobranças: 1 = Plataforma 2 = Federação',
  `access_token` varchar(100) DEFAULT NULL COMMENT 'Mercado Pago',
  `public_key` varchar(100) DEFAULT NULL COMMENT 'Mercado Pago',
  `client_id` varchar(20) DEFAULT NULL COMMENT 'Mercado Pago - User ID',
  `repassar_taxa` tinyint DEFAULT '0' COMMENT 'true=comprador paga os custos',
  `data_cadastro` datetime DEFAULT CURRENT_TIMESTAMP,
  `apresentacao` longtext COMMENT 'Texto de apresentação da federação (sobre)',
  `valor_filiacao` decimal(6,2) DEFAULT '378.00',
  `obs_filiacao` varchar(50) DEFAULT 'Anuidade Confederação',
  PRIMARY KEY (`id`),
  KEY `id_user` (`id_user`),
  KEY `fk_federacao_sigla_idx` (`id_sigla`),
  CONSTRAINT `federacoes_ibfk_1` FOREIGN KEY (`id_user`) REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_federacao_sigla` FOREIGN KEY (`id_sigla`) REFERENCES `siglas` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `filiacoes`
--

DROP TABLE IF EXISTS `filiacoes`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `filiacoes` (
  `id` int NOT NULL AUTO_INCREMENT,
  `id_compra` int NOT NULL,
  `id_atleta` int NOT NULL,
  `ano` varchar(45) NOT NULL,
  `valor` decimal(6,2) DEFAULT NULL,
  `obs` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_filiacoes_atleta_idx` (`id_atleta`),
  KEY `fk_filiacoes_compra_idx` (`id_compra`),
  CONSTRAINT `fk_filiacoes_atleta` FOREIGN KEY (`id_atleta`) REFERENCES `atletas` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_filiacoes_compra` FOREIGN KEY (`id_compra`) REFERENCES `compras` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=24 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `licencas`
--

DROP TABLE IF EXISTS `licencas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `licencas` (
  `id` int NOT NULL AUTO_INCREMENT,
  `id_minha_empresa` int NOT NULL,
  `id_plano` int NOT NULL,
  `autorizacao` timestamp NULL DEFAULT NULL COMMENT 'Data que foi autorizada a Licença',
  `data` date NOT NULL DEFAULT (curdate()) COMMENT 'Data da emissão',
  `status` tinyint NOT NULL DEFAULT '0',
  `comprovante` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_minha_empresa_idx` (`id_minha_empresa`),
  KEY `fk_plano_idx` (`id_plano`),
  CONSTRAINT `fk_minha_empresa` FOREIGN KEY (`id_minha_empresa`) REFERENCES `minha_empresa` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_plano` FOREIGN KEY (`id_plano`) REFERENCES `planos` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=33 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `meus_clientes`
--

DROP TABLE IF EXISTS `meus_clientes`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `meus_clientes` (
  `id` int NOT NULL AUTO_INCREMENT,
  `id_minha_empresa` int NOT NULL,
  `id_cliente` int NOT NULL,
  `tipo_cliente` varchar(2) DEFAULT '03',
  `status` tinyint NOT NULL DEFAULT '1',
  `cep` varchar(9) NOT NULL,
  `endereco` varchar(50) DEFAULT NULL,
  `numero` varchar(5) NOT NULL DEFAULT 'SN',
  `complemento` varchar(15) DEFAULT NULL,
  `bairro` varchar(30) DEFAULT NULL,
  `cidade` varchar(50) NOT NULL,
  `uf` varchar(2) NOT NULL,
  `ibge` varchar(7) NOT NULL DEFAULT '4128500' COMMENT 'Código do IBGE',
  PRIMARY KEY (`id`),
  UNIQUE KEY `un_meus_clientes` (`id_minha_empresa`,`id_cliente`),
  KEY `fk_meus_clientes_empresa_idx` (`id_minha_empresa`),
  KEY `fk_meus_clientes_clientes_idx` (`id_cliente`),
  KEY `fk_meus_clientes_tipo_cliente_idx` (`tipo_cliente`),
  CONSTRAINT `fk_meus_clientes_clientes` FOREIGN KEY (`id_cliente`) REFERENCES `clientes` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_meus_clientes_empresa` FOREIGN KEY (`id_minha_empresa`) REFERENCES `minha_empresa` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_meus_clientes_tipo_cliente` FOREIGN KEY (`tipo_cliente`) REFERENCES `nf21-tipo-cliente` (`codigo`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=3582 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `minha_empresa`
--

DROP TABLE IF EXISTS `minha_empresa`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `minha_empresa` (
  `id` int NOT NULL AUTO_INCREMENT,
  `id_user` int NOT NULL,
  `id_empresa` int NOT NULL,
  `responsavel` varchar(30) DEFAULT NULL COMMENT 'responsável pela apresentação das nf',
  `cargo` varchar(20) DEFAULT NULL,
  `ativo` tinyint DEFAULT '0',
  `validade` date DEFAULT NULL COMMENT 'Data de validade da Licença',
  `email_server` varchar(100) DEFAULT 'smtp.gmail.com',
  `email_username` varchar(100) DEFAULT NULL,
  `email_password` varchar(50) DEFAULT NULL,
  `email_port` varchar(4) DEFAULT '587',
  `email_tls` tinyint DEFAULT '1',
  PRIMARY KEY (`id`),
  UNIQUE KEY `un_empresa` (`id_user`,`id_empresa`),
  KEY `id_empresa` (`id_empresa`),
  CONSTRAINT `minha_empresa_ibfk_1` FOREIGN KEY (`id_user`) REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `minha_empresa_ibfk_2` FOREIGN KEY (`id_empresa`) REFERENCES `empresas` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=62 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nf21-classficacao-grupo`
--

DROP TABLE IF EXISTS `nf21-classficacao-grupo`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nf21-classficacao-grupo` (
  `codigo` varchar(2) NOT NULL,
  `descricao` varchar(45) DEFAULT NULL,
  PRIMARY KEY (`codigo`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nf21-classficacao-item`
--

DROP TABLE IF EXISTS `nf21-classficacao-item`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nf21-classficacao-item` (
  `codigo` varchar(4) NOT NULL,
  `grupo` varchar(2) DEFAULT NULL,
  `descricao` varchar(170) DEFAULT NULL,
  PRIMARY KEY (`codigo`),
  KEY `fk_classficacao_grupo_idx` (`grupo`),
  CONSTRAINT `fk_classficacao_grupo` FOREIGN KEY (`grupo`) REFERENCES `nf21-classficacao-grupo` (`codigo`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nf21-item`
--

DROP TABLE IF EXISTS `nf21-item`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nf21-item` (
  `id` int NOT NULL AUTO_INCREMENT,
  `id_mestre` int NOT NULL,
  `cfop` varchar(5) DEFAULT NULL,
  `id_servico` int DEFAULT NULL COMMENT 'Código do serviço/plano',
  `codigo_item` varchar(10) NOT NULL COMMENT 'Código do serviço/Plano definido pelo contribuinte',
  `descricao` varchar(40) DEFAULT NULL,
  `codigo_classificacao` varchar(4) DEFAULT NULL,
  `tipo_isencao` varchar(2) DEFAULT '99',
  `unidade` varchar(6) DEFAULT NULL,
  `valor` decimal(11,2) DEFAULT '0.00',
  `descontos` decimal(11,2) DEFAULT '0.00',
  `acrescimos` decimal(11,2) DEFAULT '0.00',
  `bc_icms` decimal(11,2) DEFAULT '0.00',
  `icms` decimal(11,2) DEFAULT '0.00',
  `isentos` decimal(11,2) DEFAULT '0.00',
  `outros` decimal(11,2) DEFAULT '0.00',
  `aliquota_icms` decimal(4,2) DEFAULT '0.00',
  `situacao` varchar(1) DEFAULT 'N',
  `numero_contrato` varchar(15) DEFAULT NULL,
  `quantidade_faturada` decimal(12,3) DEFAULT '0.000',
  `tarifa_aplicada` decimal(11,6) DEFAULT '0.000000',
  `aliquota_pis` decimal(6,4) DEFAULT '0.0000',
  `pis_pasep` decimal(11,2) DEFAULT '0.00',
  `aliquota_cofins` decimal(6,4) DEFAULT '0.0000',
  `cofins` decimal(11,2) DEFAULT '0.00',
  `indicador_desconto_judicial` varchar(1) DEFAULT ' ',
  PRIMARY KEY (`id`),
  UNIQUE KEY `un-item2` (`id_mestre`,`codigo_item`),
  UNIQUE KEY `un-item3` (`id_mestre`,`id_servico`),
  KEY `fk-item-servico_idx` (`id_servico`),
  CONSTRAINT `nf21-item-servico` FOREIGN KEY (`id_servico`) REFERENCES `nf21-servicos` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `nf21-item_ibfk_1` FOREIGN KEY (`id_mestre`) REFERENCES `nf21-mestre` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=65590 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nf21-item-agenda`
--

DROP TABLE IF EXISTS `nf21-item-agenda`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nf21-item-agenda` (
  `id` int NOT NULL AUTO_INCREMENT,
  `id_mestre` int NOT NULL,
  `id_servico` int DEFAULT NULL COMMENT 'Código do serviço/plano',
  `valor` decimal(11,2) DEFAULT '0.00',
  `bc_icms` decimal(11,2) DEFAULT '0.00',
  `isentos` decimal(11,2) DEFAULT '0.00',
  `outros` decimal(11,2) DEFAULT '0.00',
  `aliquota_icms` decimal(4,2) DEFAULT '0.00',
  `quantidade_faturada` decimal(12,3) DEFAULT '0.000',
  PRIMARY KEY (`id`),
  UNIQUE KEY `un-item3` (`id_mestre`,`id_servico`),
  KEY `id_servico` (`id_servico`),
  CONSTRAINT `nf21-item-agenda_ibfk_1` FOREIGN KEY (`id_servico`) REFERENCES `nf21-servicos` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `nf21-item-agenda_ibfk_2` FOREIGN KEY (`id_mestre`) REFERENCES `nf21-mestre-agenda` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=3961 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nf21-mensalidades`
--

DROP TABLE IF EXISTS `nf21-mensalidades`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nf21-mensalidades` (
  `CLIENTEID` int NOT NULL,
  `CODIGO_ITEM` varchar(10) NOT NULL,
  `DIA_VENCIMENTO` int DEFAULT NULL,
  `SERIE` varchar(3) DEFAULT '001',
  `VALOR` decimal(10,2) DEFAULT NULL,
  `ENDERECO` varchar(50) DEFAULT NULL,
  `NUMCASA` int DEFAULT NULL,
  `COMPLEMENTO` varchar(50) DEFAULT NULL,
  `BAIRRO` varchar(30) DEFAULT NULL,
  `CODMUNICIPIO` varchar(10) NOT NULL,
  `CEP` varchar(9) NOT NULL,
  `DESCONTOS` decimal(11,2) DEFAULT '0.00',
  `ACRESCIMOS` decimal(11,2) DEFAULT '0.00',
  `ISENTAS` decimal(11,2) DEFAULT NULL,
  `OUTRAS` decimal(11,2) DEFAULT NULL,
  `DTULTIMOLANCAMENTO` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `SEQUENCIA` int NOT NULL DEFAULT '1',
  `TIPO_CLIENTE` varchar(2) DEFAULT NULL,
  `TIPOUTILIZACAO` smallint DEFAULT '4',
  PRIMARY KEY (`CLIENTEID`,`CODIGO_ITEM`),
  KEY `CODIGO_ITEM` (`CODIGO_ITEM`),
  CONSTRAINT `nf21-mensalidades_ibfk_1` FOREIGN KEY (`CLIENTEID`) REFERENCES `clientes` (`id`) ON UPDATE CASCADE,
  CONSTRAINT `nf21-mensalidades_chk_1` CHECK (((`DIA_VENCIMENTO` >= 1) and (`DIA_VENCIMENTO` <= 31)))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nf21-mestre`
--

DROP TABLE IF EXISTS `nf21-mestre`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nf21-mestre` (
  `id` int NOT NULL AUTO_INCREMENT,
  `id_empresa` int NOT NULL,
  `ano_mes` varchar(5) NOT NULL,
  `modelo` varchar(2) NOT NULL DEFAULT '21',
  `serie` varchar(3) NOT NULL DEFAULT '001',
  `numero` int DEFAULT '1',
  `id_cliente` int NOT NULL,
  `cep` varchar(9) DEFAULT NULL,
  `endereco` varchar(50) DEFAULT NULL,
  `numcasa` varchar(5) DEFAULT NULL,
  `complemento` varchar(15) DEFAULT NULL,
  `bairro` varchar(30) DEFAULT NULL,
  `cidade` varchar(30) DEFAULT NULL,
  `uf` varchar(2) DEFAULT NULL,
  `ibge` varchar(7) DEFAULT NULL,
  `data_emissao` date DEFAULT (curdate()),
  `situacao` varchar(1) DEFAULT 'N',
  `tipo_cliente` varchar(2) DEFAULT NULL,
  `tipo_utilizacao` smallint DEFAULT '4',
  `validado` varchar(1) DEFAULT 'N',
  `impresso` varchar(1) DEFAULT 'N',
  `enviado_email` varchar(1) DEFAULT 'N',
  `observacao` varchar(500) DEFAULT NULL,
  `valor_total` decimal(11,2) DEFAULT '0.00',
  `campo13` varchar(32) DEFAULT NULL COMMENT 'Campo 13 - Código de Autenticação Digital do documento fiscal',
  `campo36` varchar(32) DEFAULT NULL COMMENT '# Campo 36 - Código de Autenticação Digital do registro',
  `id_agenda` int DEFAULT NULL COMMENT 'Campo para saber se a nota já foi emitida pelo agendamento porque pode ter notas iguais para um mesmo cliente, no mesmo dia',
  PRIMARY KEY (`id`),
  UNIQUE KEY `un_mestre` (`ano_mes`,`modelo`,`serie`,`numero`,`id_empresa`),
  KEY `fk-nf21-cliente_idx` (`id_cliente`),
  KEY `fk-nf21-empresa_idx` (`id_empresa`),
  KEY `nf21-mestre_ibfk_1` (`id_agenda`),
  CONSTRAINT `fk-nf21-cliente` FOREIGN KEY (`id_cliente`) REFERENCES `clientes` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk-nf21-empresa` FOREIGN KEY (`id_empresa`) REFERENCES `empresas` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `nf21-mestre_ibfk_1` FOREIGN KEY (`id_agenda`) REFERENCES `nf21-mestre-agenda` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=77572 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nf21-mestre-agenda`
--

DROP TABLE IF EXISTS `nf21-mestre-agenda`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nf21-mestre-agenda` (
  `id` int NOT NULL AUTO_INCREMENT,
  `id_empresa` int NOT NULL,
  `modelo` varchar(2) NOT NULL DEFAULT '21',
  `serie` varchar(3) NOT NULL DEFAULT '001',
  `id_cliente` int NOT NULL,
  `dia` int DEFAULT '1',
  `data_proxima_emissao` date NOT NULL DEFAULT (curdate()) COMMENT 'data da próxima nota a emitir. Uso apenas o ano e mês',
  `observacao` varchar(500) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `id_cliente` (`id_cliente`),
  KEY `nf21-mestre-agenda_ibfk_2_idx` (`id_empresa`),
  CONSTRAINT `nf21-mestre-agenda_ibfk_1` FOREIGN KEY (`id_cliente`) REFERENCES `clientes` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `nf21-mestre-agenda_ibfk_2` FOREIGN KEY (`id_empresa`) REFERENCES `empresas` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=3977 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nf21-servicos`
--

DROP TABLE IF EXISTS `nf21-servicos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nf21-servicos` (
  `id` int NOT NULL AUTO_INCREMENT,
  `id_empresa` int NOT NULL,
  `codigo` varchar(10) DEFAULT NULL COMMENT 'Código atribuído pela empresa',
  `descricao` varchar(40) DEFAULT NULL,
  `cfop` varchar(5) DEFAULT NULL,
  `codigo_classificacao` varchar(4) DEFAULT NULL,
  `unidade` varchar(6) DEFAULT 'UN',
  `numero_contrato` varchar(15) DEFAULT '               ',
  `tipo_isencao` varchar(2) DEFAULT '99',
  `indicador_desconto_judicial` varchar(1) DEFAULT ' ',
  `valor` decimal(11,2) DEFAULT '0.00',
  `bc_icms` decimal(11,2) DEFAULT '0.00',
  `aliquota_icms` decimal(4,2) DEFAULT '0.00',
  `isentas` decimal(11,2) DEFAULT '0.00',
  `quantidade_faturada` decimal(12,3) DEFAULT '0.000',
  `aliquota_pis` decimal(6,4) DEFAULT '0.0000',
  `pis_pasep` decimal(11,2) DEFAULT '0.00',
  `aliquota_cofins` decimal(6,4) DEFAULT '0.0000',
  `cofins` decimal(11,2) DEFAULT '0.00',
  `outras` decimal(11,2) DEFAULT '0.00',
  `anatel_tipo_atendimento` varchar(45) DEFAULT NULL COMMENT 'URBANO/RURAL/PUBLICO/INDUSTRIAL',
  `anatel_tipo_meio` varchar(45) DEFAULT NULL COMMENT 'Fibra/wifi/cabo',
  `anatel_tipo_produto` varchar(45) DEFAULT NULL COMMENT 'Internet',
  `anatel_tipo_tecnologia` varchar(45) DEFAULT NULL COMMENT 'ADSL2/FTTH',
  PRIMARY KEY (`id`),
  UNIQUE KEY `un-servicos` (`id_empresa`,`codigo`),
  KEY `CFOP` (`cfop`),
  KEY `CODIGO_CLASSIFICACAO` (`codigo_classificacao`),
  KEY `nf21-servicos_empresa_idx` (`id_empresa`),
  KEY `nf21-servicos_isencao_idx` (`tipo_isencao`),
  CONSTRAINT `nf21-servicos_empresa` FOREIGN KEY (`id_empresa`) REFERENCES `empresas` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `nf21-servicos_ibfk_1` FOREIGN KEY (`cfop`) REFERENCES `cfop` (`cfop`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `nf21-servicos_ibfk_2` FOREIGN KEY (`codigo_classificacao`) REFERENCES `nf21-classficacao-item` (`codigo`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `nf21-servicos_isencao` FOREIGN KEY (`tipo_isencao`) REFERENCES `nf21-tipo-isencao` (`codigo`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=307 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nf21-tipo-cliente`
--

DROP TABLE IF EXISTS `nf21-tipo-cliente`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nf21-tipo-cliente` (
  `codigo` varchar(2) NOT NULL,
  `descricao` varchar(200) DEFAULT NULL,
  `cod_sped` int DEFAULT NULL COMMENT 'Referencia cruzada para gerar o sped',
  PRIMARY KEY (`codigo`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nf21-tipo-isencao`
--

DROP TABLE IF EXISTS `nf21-tipo-isencao`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nf21-tipo-isencao` (
  `codigo` varchar(2) NOT NULL,
  `descricao` varchar(120) DEFAULT NULL,
  PRIMARY KEY (`codigo`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nf21-tipo-utilizacao`
--

DROP TABLE IF EXISTS `nf21-tipo-utilizacao`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nf21-tipo-utilizacao` (
  `codigo` int NOT NULL,
  `descricao` varchar(40) NOT NULL,
  PRIMARY KEY (`codigo`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `novidades`
--

DROP TABLE IF EXISTS `novidades`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `novidades` (
  `id` int NOT NULL AUTO_INCREMENT,
  `data` datetime DEFAULT CURRENT_TIMESTAMP,
  `titulo` varchar(45) NOT NULL,
  `descricao` varchar(500) DEFAULT NULL,
  `url` varchar(200) DEFAULT NULL COMMENT 'Url destino',
  `imagem` varchar(200) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `planos`
--

DROP TABLE IF EXISTS `planos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `planos` (
  `id` int NOT NULL,
  `nome` varchar(30) NOT NULL,
  `valor` float NOT NULL DEFAULT '200',
  `ativo` tinyint NOT NULL DEFAULT '1',
  `validade` int NOT NULL DEFAULT '12' COMMENT 'Validade da Licença em meses',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `registro_login`
--

DROP TABLE IF EXISTS `registro_login`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `registro_login` (
  `id` int NOT NULL AUTO_INCREMENT,
  `id_user` int DEFAULT NULL,
  `username` varchar(50) DEFAULT NULL,
  `ip` varchar(50) NOT NULL,
  `data` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `user_agent` varchar(200) DEFAULT NULL COMMENT 'Identifica a origem da conexão com dados do navegador, SO, etc',
  PRIMARY KEY (`id`),
  KEY `fk_login_users_idx` (`id_user`),
  CONSTRAINT `fk_login_users` FOREIGN KEY (`id_user`) REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=4298 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `siglas`
--

DROP TABLE IF EXISTS `siglas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `siglas` (
  `id` int NOT NULL AUTO_INCREMENT,
  `sigla` varchar(10) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `id` int NOT NULL AUTO_INCREMENT,
  `cpf` varchar(18) NOT NULL,
  `password` varchar(256) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `email` varchar(100) DEFAULT NULL,
  `nome` varchar(50) NOT NULL,
  `data_nascimento` date DEFAULT NULL,
  `celular` varchar(15) DEFAULT NULL,
  `image_file` varchar(100) NOT NULL DEFAULT 'svg/profile.svg',
  `data_ultimo_login` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `data_cadastro` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `verify_account` tinyint NOT NULL DEFAULT '0',
  `id_ultima_novidade` int DEFAULT '0' COMMENT 'ID da última novidade lida pelo usuário',
  PRIMARY KEY (`id`),
  UNIQUE KEY `cpf_UN` (`cpf`),
  UNIQUE KEY `email_UN` (`email`)
) ENGINE=InnoDB AUTO_INCREMENT=23 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `visitas`
--

DROP TABLE IF EXISTS `visitas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `visitas` (
  `id` int NOT NULL AUTO_INCREMENT,
  `ip` varchar(50) NOT NULL,
  `data` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=33789 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-10-24 17:11:17
