# SAVI Assistant - Sistema de Análise de Dados TEA

## Overview

SAVI Assistant é um sistema web desenvolvido em Flask para análise e processamento de dados clínicos relacionados ao Transtorno do Espectro Autista (TEA). O sistema processa bancos de dados SQLite contendo informações de atendimentos e sessões, aplicando regras de negócio específicas para cálculo de faturamento, detecção de pacotes de sessões, e validação de procedimentos por empresa.

O assistente automatiza tarefas complexas como:
- Cálculo de faturamento por empresa, procedimento, médico e paciente
- Aplicação automática de regras de pacotes (comum R$ 1.150,00 e especial R$ 1.600,00) quando pacientes atingem 12+ sessões
- Validação de preços especiais através de planilhas Excel de carteirinhas
- Verificação de consistência entre empresas e procedimentos permitidos
- Geração de relatórios detalhados e dashboards interativos

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
O sistema utiliza uma arquitetura web tradicional baseada em templates Jinja2 com Bootstrap para interface responsiva. A interface é construída com tema escuro e inclui:
- Sistema de navegação com autenticação baseada em sessões
- Dashboard interativo com estatísticas e gráficos usando Chart.js
- Interface de upload de arquivos com validação client-side
- Sistema de relatórios com visualizações tabulares e gráficas
- Componentes reutilizáveis através de template inheritance

### Backend Architecture
Arquitetura MVC implementada com Flask seguindo padrões de separação de responsabilidades:
- **Models** (`models.py`): Define entidades de dados usando SQLAlchemy ORM
- **Routes** (`routes.py`, `auth.py`): Controladores para diferentes funcionalidades
- **Data Processing** (`data_processor.py`): Lógica de negócio para análise de dados
- **Report Generation** (`report_generator.py`): Geração de relatórios e estatísticas
- **Utilities** (`utils.py`): Funções auxiliares para validação e processamento

### Data Storage Solutions
Sistema de armazenamento de dados configurado para usar os dados reais do SAVI:
- **SQLite Principal**: Banco de dados da aplicação (`instance/savi_assistant.db`) contendo:
  - Dados reais de produção médica (tabela `producao` com 4.051 registros)
  - Usuários do sistema e sessões de análise
  - Dados processados e resultados de análises
- **Arquivos Excel**: Planilhas opcionais para configuração de preços especiais
- **Upload Directory**: Armazenamento temporário de arquivos carregados

**Última atualização**: 05/08/2025 - Sistema completamente ajustado às especificações corretas:
- Estrutura real da tabela producao implementada com todas as 16 colunas
- Códigos de procedimento corretos conforme especificação (com pontos e hífens)
- Sistema de pacotes: 12+ sessões/mês = R$ 1.150 (comum) ou R$ 1.600 (especial)
- **NOVA LÓGICA IMPLEMENTADA**: Detecção de pacotes considera apenas qtde_autorizada > 0
- Carteirinhas especiais processadas via Excel (usuario_codigo matching)
- Dashboard completamente responsivo com design mobile-first
- Relatório Geral interativo com 6 gráficos animados e filtros avançados
- Interface otimizada para dispositivos móveis e tablets
- Filtros de data implementados no dashboard e relatórios
- Validação empresa x procedimento com detecção de inconsistências
- Upload flexível aceita qualquer arquivo (.db, .xlsx, etc.)
- Sistema prioriza dados do arquivo carregado sobre dados padrão
- **RELATÓRIO DIVINÓPOLIS**: Ajustado para calcular valores médicos apenas com base nas carteirinhas dos usuários específicos de Divinópolis
- **RESPONSIVIDADE**: Sistema completamente adaptado para mobile com CSS específico e componentes touch-friendly

### Authentication and Authorization
Sistema de autenticação implementado com Flask-Login:
- Autenticação baseada em sessões com suporte a "remember me"
- Sistema de roles (admin/operador) para controle de acesso
- Proteção de rotas através de decoradores `@login_required`
- Hash seguro de senhas usando Werkzeug
- Criação automática de usuário admin padrão na inicialização

### Business Logic Processing
Engine de processamento de dados especializado para análise TEA:
- **Validation Rules**: Sistema configurável de regras empresa-procedimento
- **Package Detection**: Algoritmo automático para identificação de pacotes de 12+ sessões
- **Price Management**: Sistema dual de preços (padrão/especial) com override via Excel
- **Inconsistency Detection**: Validação automatizada de dados com relatório de erros
- **Multi-threaded Processing**: Processamento assíncrono para grandes volumes de dados

## External Dependencies

### Core Framework Stack
- **Flask**: Framework web principal com SQLAlchemy para ORM
- **Flask-Login**: Gerenciamento de sessões e autenticação de usuários
- **Werkzeug**: Utilities para segurança e manipulação de arquivos

### Data Processing Libraries
- **Pandas**: Manipulação e análise de grandes datasets
- **NumPy**: Operações matemáticas e arrays para cálculos estatísticos
- **OpenPyXL**: Leitura e processamento de planilhas Excel (.xlsx)

### Frontend Dependencies
- **Bootstrap**: Framework CSS para interface responsiva com tema escuro
- **Chart.js**: Biblioteca para geração de gráficos interativos
- **Feather Icons**: Sistema de ícones SVG para interface consistente

### Database Integration
- **SQLite3**: Banco de dados principal da aplicação e processamento de dados externos
- **SQLAlchemy**: ORM para modelagem e queries de banco de dados

### File Processing
Sistema robusto de upload e validação de arquivos com suporte a:
- Validação de tipos de arquivo (SQLite: .db, .sqlite, .sqlite3 / Excel: .xlsx, .xls)
- Verificação de integridade de schema de banco de dados
- Limpeza automática de arquivos temporários
- Limite de tamanho de upload (50MB) configurável