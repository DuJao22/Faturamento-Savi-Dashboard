"""
Lógica de Negócio para Sistema SAVI
Implementa regras de faturamento, pacotes e validações
"""

from datetime import datetime
from collections import defaultdict
import pandas as pd
import logging

# Configurações de preços baseadas nas especificações corretas
PRECOS_PROCEDIMENTOS = {
    "60.01.015-0": {"nome": "CONSULTA/SESSAO PSICOPEDAGOGIA - TEA", "padrao": 53.12, "especial": 65.00},
    "62.01.020-4": {"nome": "SESSAO DE FISIOTERAPIA PARA TEA", "padrao": 53.12, "especial": 65.00},
    "62.01.021-2": {"nome": "SESSAO MUSICOTERAPIA", "padrao": 53.12, "especial": 65.00},
    "65.01.003-5": {"nome": "CONSULTA/SESSAO NUTRICAO TEA", "padrao": 53.12, "especial": 65.00},
    "60.01.012-6": {"nome": "PSICOTERAPIA TEA", "padrao": 53.12, "especial": 65.00},
    "61.01.007-3": {"nome": "FONOAUDIOLOGIA TEA", "padrao": 53.12, "especial": 65.00},
    "62.01.012-3": {"nome": "TERAPIA OCUPACIONAL TEA", "padrao": 53.12, "especial": 65.00},
    "00.01.001-4": {"nome": "PSIQUIATRIA DA INFÂNCIA / NEURO PEDIATRIA", "padrao": 150.00, "especial": 180.00},
    "60.01.014-2": {"nome": "TESTE NEUROPSICOLÓGICO", "padrao": 800.00, "especial": 800.00},
    "60.01.036-3": {"nome": "CONSULTA/SESSAO DE NEUROPSICOLOGIA", "padrao": 100.00, "especial": 100.00},
}

# Procedimentos elegíveis para pacotes (baseado no procedimento_codigo)
PROCEDIMENTOS_PACOTE = [
    "61.01.007-3",  # FONOAUDIOLOGIA TEA
    "60.01.012-6",  # PSICOTERAPIA TEA  
    "62.01.012-3",  # TERAPIA OCUPACIONAL TEA
    "62.01.020-4",  # SESSAO DE FISIOTERAPIA PARA TEA
    "62.01.021-2",  # SESSAO MUSICOTERAPIA
    "60.01.015-0",  # CONSULTA/SESSAO PSICOPEDAGOGIA - TEA
]

# Valores dos pacotes
PACOTE_COMUM = 1150.00
PACOTE_ESPECIAL = 1600.00

# Validação empresa x procedimento
VALIDACAO_PROCEDIMENTOS = {
    "Hapvida": [
        "PSICOTERAPIA TEA", "TERAPIA OCUPACIONAL TEA", "FONOAUDIOLOGIA TEA",
        "CONSULTA/SESSAO PSICOPEDAGOGIA - TEA", "SESSAO DE FISIOTERAPIA PARA TEA",
        "SESSAO MUSICOTERAPIA",
    ],
    "Notredame": [
        "PSICOTERAPIA TEA", "TERAPIA OCUPACIONAL TEA", "FONOAUDIOLOGIA TEA",
        "CONSULTA/SESSAO PSICOPEDAGOGIA - TEA", "SESSAO DE FISIOTERAPIA PARA TEA",
        "SESSAO MUSICOTERAPIA",
    ],
    "Hapvida_neuro": [
        "TESTE NEUROPSICOLOGICO", "CONSULTA/SESSAO DE NEUROPSICOLOGIA"
    ],
    "Notredame_neuro": [
        "TESTE NEUROPSICOLOGICO", "CONSULTA/SESSAO DE NEUROPSICOLOGIA"
    ],
    "Hapvida_libelula": ["CONSULTA EM CONSULTORIO"],
    "Notredame_libelula": ["CONSULTA EM CONSULTORIO"]
}

class SAVIBusinessLogic:
    def __init__(self):
        self.carteirinhas_especiais = set()
        
    def load_carteirinhas_especiais(self, excel_path=None):
        """Carrega lista de pacientes com preços especiais do Excel"""
        if excel_path:
            try:
                df = pd.read_excel(excel_path)
                if 'usuario_codigo' in df.columns:
                    self.carteirinhas_especiais = set(df['usuario_codigo'].astype(str))
                    logging.info(f"Carregadas {len(self.carteirinhas_especiais)} carteirinhas especiais")
                else:
                    logging.warning("Coluna 'usuario_codigo' não encontrada no Excel")
            except Exception as e:
                logging.error(f"Erro ao carregar carteirinhas especiais: {e}")
    
    def get_preco_procedimento(self, codigo_procedimento, usuario_codigo):
        """Retorna o preço do procedimento (padrão ou especial)"""
        if codigo_procedimento in PRECOS_PROCEDIMENTOS:
            config = PRECOS_PROCEDIMENTOS[codigo_procedimento]
            if str(usuario_codigo) in self.carteirinhas_especiais:
                return config["especial"]
            else:
                return config["padrao"]
        return 0.0  # Procedimento não tem preço configurado
    
    def detect_pacotes(self, df_producao):
        """Detecta pacientes que atingiram 12+ sessões no mês para aplicar pacotes"""
        pacotes_aplicados = []
        
        # Converter data_execucao para datetime
        df_producao['data_execucao'] = pd.to_datetime(df_producao['data_execucao'], format='%d/%m/%Y', errors='coerce')
        
        # Agrupar por paciente e mês
        df_producao['mes_ano'] = df_producao['data_execucao'].dt.to_period('M')
        
        for (usuario_codigo, mes_ano), grupo in df_producao.groupby(['usuario_codigo', 'mes_ano']):
            # Filtrar apenas procedimentos elegíveis para pacote
            sessoes_pacote = grupo[grupo['procedimento_codigo'].isin(PROCEDIMENTOS_PACOTE)]
            
            if len(sessoes_pacote) >= 12:
                # Determinar tipo de pacote (comum ou especial)
                tipo_pacote = 'especial' if str(usuario_codigo) in self.carteirinhas_especiais else 'comum'
                valor_pacote = PACOTE_ESPECIAL if tipo_pacote == 'especial' else PACOTE_COMUM
                
                pacotes_aplicados.append({
                    'usuario_codigo': usuario_codigo,
                    'usuario_nome': grupo['usuario_nome'].iloc[0],
                    'mes_ano': str(mes_ano),
                    'quantidade_sessoes': len(sessoes_pacote),
                    'tipo_pacote': tipo_pacote,
                    'valor_pacote': valor_pacote,
                    'sessoes_ids': sessoes_pacote.index.tolist()
                })
        
        return pacotes_aplicados
    
    def validate_empresa_procedimento(self, empresa, procedimento_nome):
        """Valida se o procedimento é permitido para a empresa"""
        if empresa in VALIDACAO_PROCEDIMENTOS:
            procedimentos_permitidos = VALIDACAO_PROCEDIMENTOS[empresa]
            return procedimento_nome in procedimentos_permitidos
        return False  # Empresa não configurada = inconsistência
    
    def process_faturamento(self, df_producao, excel_path=None):
        """Processa todo o faturamento aplicando regras de negócio"""
        
        # Carregar carteirinhas especiais se fornecidas
        if excel_path:
            self.load_carteirinhas_especiais(excel_path)
        
        resultado = {
            'dados_processados': [],
            'pacotes_aplicados': [],
            'inconsistencias': [],
            'resumo_financeiro': {},
            'resumo_por_empresa': {},
            'resumo_por_especialidade': {},
            'resumo_por_medico': {},
            'resumo_por_paciente': {}
        }
        
        # Detectar pacotes primeiro
        pacotes = self.detect_pacotes(df_producao.copy())
        resultado['pacotes_aplicados'] = pacotes
        
        # Criar set de sessões que fazem parte de pacotes
        sessoes_em_pacotes = set()
        for pacote in pacotes:
            sessoes_em_pacotes.update(pacote['sessoes_ids'])
        
        # Processar cada registro
        total_faturado = 0
        resumo_empresa = defaultdict(lambda: {'registros': 0, 'valor': 0})
        resumo_especialidade = defaultdict(lambda: {'sessoes': 0, 'valor': 0})
        resumo_medico = defaultdict(lambda: {'sessoes': 0, 'valor': 0})
        resumo_paciente = defaultdict(lambda: {'sessoes': 0, 'valor': 0})
        
        for idx, row in df_producao.iterrows():
            registro = {
                'empresa': row['empresa'],
                'procedimento_codigo': row['procedimento_codigo'],
                'procedimento_nome': row['procedimento_nome'],
                'usuario_codigo': row['usuario_codigo'],
                'usuario_nome': row['usuario_nome'],
                'medico_nome': row['medico_nome'],
                'data_execucao': row['data_execucao'],
                'valor_original': 0.0,
                'valor_final': 0.0,
                'is_pacote': False,
                'tipo_pacote': None,
                'has_inconsistencia': False,
                'inconsistencia_descricao': ''
            }
            
            # Calcular valor original
            valor_original = self.get_preco_procedimento(row['procedimento_codigo'], row['usuario_codigo'])
            registro['valor_original'] = valor_original
            
            # Verificar se faz parte de pacote
            if idx in sessoes_em_pacotes:
                registro['is_pacote'] = True
                registro['valor_final'] = 0.0  # Valor zerado pois está no pacote
                # Encontrar qual pacote
                for pacote in pacotes:
                    if idx in pacote['sessoes_ids']:
                        registro['tipo_pacote'] = pacote['tipo_pacote']
                        break
            else:
                registro['valor_final'] = valor_original
            
            # Validar empresa x procedimento
            if not self.validate_empresa_procedimento(row['empresa'], row['procedimento_nome']):
                registro['has_inconsistencia'] = True
                registro['inconsistencia_descricao'] = f"Procedimento '{row['procedimento_nome']}' não autorizado para empresa '{row['empresa']}'"
                resultado['inconsistencias'].append(registro.copy())
            
            # Somar aos resumos
            total_faturado += registro['valor_final']
            resumo_empresa[row['empresa']]['registros'] += 1
            resumo_empresa[row['empresa']]['valor'] += registro['valor_final']
            
            resumo_especialidade[row['procedimento_nome']]['sessoes'] += 1
            resumo_especialidade[row['procedimento_nome']]['valor'] += registro['valor_final']
            
            resumo_medico[row['medico_nome']]['sessoes'] += 1
            resumo_medico[row['medico_nome']]['valor'] += registro['valor_final']
            
            resumo_paciente[f"{row['usuario_codigo']} - {row['usuario_nome']}"]['sessoes'] += 1
            resumo_paciente[f"{row['usuario_codigo']} - {row['usuario_nome']}"]['valor'] += registro['valor_final']
            
            resultado['dados_processados'].append(registro)
        
        # Adicionar valor dos pacotes ao total
        for pacote in pacotes:
            total_faturado += pacote['valor_pacote']
            resumo_empresa[df_producao[df_producao.index.isin(pacote['sessoes_ids'])]['empresa'].iloc[0]]['valor'] += pacote['valor_pacote']
        
        # Montar resumos finais
        resultado['resumo_financeiro'] = {
            'total_faturado': total_faturado,
            'total_registros': len(df_producao),
            'total_pacotes': len(pacotes),
            'valor_total_pacotes': sum(p['valor_pacote'] for p in pacotes),
            'total_inconsistencias': len(resultado['inconsistencias'])
        }
        
        resultado['resumo_por_empresa'] = dict(resumo_empresa)
        resultado['resumo_por_especialidade'] = dict(resumo_especialidade)
        resultado['resumo_por_medico'] = dict(resumo_medico)
        resultado['resumo_por_paciente'] = dict(resumo_paciente)
        
        return resultado