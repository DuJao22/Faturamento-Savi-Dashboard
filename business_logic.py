"""
Lógica de Negócio para Sistema SAVI - VERSÃO CORRIGIDA
Implementa regras de faturamento, pacotes e validações conforme especificação
"""

from datetime import datetime
from collections import defaultdict
import pandas as pd
import logging

# Preços dos procedimentos conforme códigos reais do banco (sem pontos e hífens)
PRECOS_PROCEDIMENTOS = {
    "60010150": {"padrao": 53.12, "especial": 65.00},  # CONSULTA/SESSAO PSICOPEDAGOGIA - TEA
    "62010204": {"padrao": 53.12, "especial": 65.00},  # SESSAO DE FISIOTERAPIA PARA TEA
    "62010212": {"padrao": 53.12, "especial": 65.00},  # SESSAO MUSICOTERAPIA
    "65010035": {"padrao": 53.12, "especial": 65.00},  # CONSULTA/SESSAO NUTRICAO TEA
    "60010126": {"padrao": 53.12, "especial": 65.00},  # PSICOTERAPIA TEA
    "61010073": {"padrao": 53.12, "especial": 65.00},  # FONOAUDIOLOGIA TEA
    "62010123": {"padrao": 53.12, "especial": 65.00},  # TERAPIA OCUPACIONAL TEA
    # Códigos especiais por médico (mesmo código, preços diferentes)
    "00010014": {
        "MARCELO FARIA DE MORAES BRAGA": {"padrao": 80.00, "especial": 80.00},   # PSIQUIATRIA DA INFANCIA
        "RAFAEL ELIAN ALVARES": {"padrao": 150.00, "especial": 180.00},          # NEUROLOGIA PEDIÁTRICA
        "default": {"padrao": 150.00, "especial": 180.00}  # Fallback para outros médicos
    },
    "60010142": {"padrao": 800.00, "especial": 800.00},  # TESTE NEUROPSICOLÓGICO
    "60010363": {"padrao": 100.00, "especial": 100.00},  # CONSULTA/SESSAO DE NEUROPSICOLOGIA
    # Códigos alternativos encontrados no banco
    "50001213": {"padrao": 53.12, "especial": 65.00},  # MUSICOTERAPIA - POR SESSAO
    "10101012": {"padrao": 150.00, "especial": 180.00},  # CONSULTA EM CONSULTORIO (NO HORARIO NORMAL)
}

# Procedimentos elegíveis para pacotes (códigos reais do banco)
PROCEDIMENTOS_PACOTE = [
    "61010073",  # FONOAUDIOLOGIA TEA
    "60010126",  # PSICOTERAPIA TEA  
    "62010123",  # TERAPIA OCUPACIONAL TEA
    "62010204",  # SESSAO DE FISIOTERAPIA PARA TEA
    "62010212",  # SESSAO MUSICOTERAPIA
    "60010150",  # CONSULTA/SESSAO PSICOPEDAGOGIA - TEA
    "50001213",  # MUSICOTERAPIA - POR SESSAO (código alternativo)
]

# Valores dos pacotes
PACOTE_COMUM = 1150.00
PACOTE_ESPECIAL = 1600.00

# Validação empresa x procedimento (usando nomes reais do banco)
VALIDACAO_PROCEDIMENTOS = {
    "Hapvida": [
        "PSICOTERAPIA TEA", "TERAPIA OCUPACIONAL TEA", "FONOAUDIOLOGIA TEA",
        "CONSULTA/SESSAO PSICOPEDAGOGIA - TEA", "SESSAO DE FISIOTERAPIA PARA TEA",
        "SESSAO MUSICOTERAPIA", "CONSULTA/ SESSAO NUTRICAO TEA",
    ],
    "Notredame": [
        "PSICOTERAPIA TEA", "TERAPIA OCUPACIONAL TEA", "FONOAUDIOLOGIA TEA",
        "CONSULTA/SESSAO PSICOPEDAGOGIA - TEA", "SESSAO DE FISIOTERAPIA PARA TEA",
        "SESSAO MUSICOTERAPIA", "CONSULTA/ SESSAO NUTRICAO TEA",
    ],
    "Hapvida_neuro": [
        "TESTE NEUROPSICOLOGICO", "CONSULTA/SESSAO DE NEUROPSICOLOGIA"
    ],
    "Notredame_neuro": [
        "TESTE NEUROPSICOLOGICO", "CONSULTA/SESSAO DE NEUROPSICOLOGIA"
    ],
    "Hapvida_libelula": [
        "CONSULTA EM CONSULTORIO", 
        "CONSULTA EM CONSULTORIO (NO HORARIO NORMAL OU PREESTABELECIDO)"
    ],
    "Notredame_libelula": [
        "CONSULTA EM CONSULTORIO",
        "CONSULTA EM CONSULTORIO (NO HORARIO NORMAL OU PREESTABELECIDO)"
    ]
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
    
    def calcular_valor_procedimento(self, procedimento_codigo, usuario_codigo, medico_nome=None):
        """Calcula o valor do procedimento baseado no código, médico e se tem carteirinha especial"""
        if procedimento_codigo in PRECOS_PROCEDIMENTOS:
            config = PRECOS_PROCEDIMENTOS[procedimento_codigo]
            
            # Caso especial: código 00010014 - diferenciar por médico
            if procedimento_codigo == "00010014" and medico_nome:
                if medico_nome in config:
                    medico_config = config[medico_nome]
                else:
                    medico_config = config["default"]
                
                if str(usuario_codigo) in self.carteirinhas_especiais:
                    return medico_config["especial"]
                else:
                    return medico_config["padrao"]
            
            # Casos normais
            if isinstance(config, dict) and "padrao" in config:
                if str(usuario_codigo) in self.carteirinhas_especiais:
                    return config["especial"]
                else:
                    return config["padrao"]
                    
        return 0.0  # Procedimento não tem preço configurado
    
    def detectar_pacotes(self, df_producao):
        """Detecta pacientes que atingiram 12+ sessões no mesmo mês para aplicar pacotes"""
        pacotes_aplicados = []
        df_producao = df_producao.copy()
        
        logging.info(f"Iniciando detecção de pacotes em {len(df_producao)} registros")
        
        # Filtrar apenas procedimentos elegíveis para pacote primeiro
        df_elegivel = df_producao[df_producao['procedimento_codigo'].isin(PROCEDIMENTOS_PACOTE)].copy()
        logging.info(f"Encontrados {len(df_elegivel)} registros com procedimentos elegíveis para pacote")
        
        # CORRIGIDO: Filtrar apenas registros com qtde_realizada > 0
        if 'qtde_realizada' in df_elegivel.columns:
            antes_filtro = len(df_elegivel)
            df_elegivel = df_elegivel[df_elegivel['qtde_realizada'] > 0].copy()
            logging.info(f"Filtro qtde_realizada > 0: {len(df_elegivel)} registros válidos (eram {antes_filtro})")
        else:
            logging.warning("Coluna 'qtde_realizada' não encontrada. Usando todos os registros.")
        
        # Tentar agrupar por mês se houver data válida
        tem_data_valida = False
        if 'data_execucao' in df_elegivel.columns:
            # CORRIGIDO: Converter datas brasileiras (dd/mm/yyyy) corretamente
            df_elegivel['data_execucao'] = pd.to_datetime(df_elegivel['data_execucao'], format='%d/%m/%Y', errors='coerce')
            df_elegivel['mes_ano'] = df_elegivel['data_execucao'].dt.to_period('M')
            tem_data_valida = df_elegivel['mes_ano'].notna().any()
            logging.info(f"Data válida encontrada: {tem_data_valida}")
            
            # Debug: verificar quantas datas são válidas
            datas_validas = df_elegivel['data_execucao'].notna().sum()
            logging.info(f"Registros com data válida: {datas_validas} de {len(df_elegivel)}")
            
            # Debug: mostrar alguns exemplos de conversão
            if datas_validas > 0:
                sample_dates = df_elegivel[df_elegivel['data_execucao'].notna()][['data_execucao', 'mes_ano']].head(3)
                logging.info(f"Exemplo de datas convertidas: {sample_dates.to_dict('records')}")
        
        if tem_data_valida:
            # Agrupar por paciente e mês
            grupos = df_elegivel.groupby(['usuario_codigo', 'mes_ano'])
            logging.info("Agrupando por paciente e mês")
        else:
            # Se não há data válida, agrupar apenas por paciente (considerando todo o período)
            df_elegivel['mes_ano'] = 'total'
            grupos = df_elegivel.groupby(['usuario_codigo'])
            logging.info("Agrupando apenas por paciente (sem data)")
        
        for chave, grupo in grupos:
            if tem_data_valida:
                usuario_codigo, mes_ano = chave
                if pd.isna(mes_ano):
                    continue
                    
                # Debug: mostrar detalhes do agrupamento
                mes_ano_str = str(mes_ano)
                logging.info(f"Processando {usuario_codigo} no mês {mes_ano_str}")
            else:
                usuario_codigo = chave
                mes_ano = 'Período Total'
                mes_ano_str = mes_ano
                
            # CORRIGIDO: Contar sessões baseado em qtde_realizada
            if 'qtde_realizada' in grupo.columns:
                total_sessoes = int(grupo['qtde_realizada'].sum())
                logging.info(f"Usando qtde_realizada: {usuario_codigo} tem {total_sessoes} sessões realizadas")
            else:
                total_sessoes = len(grupo)
                logging.info(f"Usando contagem de registros: {usuario_codigo} tem {total_sessoes} registros")
            
            # Log para debug - mostrar todos os pacientes com mais de 6 sessões
            if total_sessoes >= 6:
                logging.info(f"Debug: {usuario_codigo} tem {total_sessoes} sessões elegíveis em {mes_ano_str}")
            
            if total_sessoes >= 12:
                # Determinar tipo de pacote (comum ou especial)
                tipo_pacote = 'especial' if str(usuario_codigo) in self.carteirinhas_especiais else 'comum'
                valor_pacote = PACOTE_ESPECIAL if tipo_pacote == 'especial' else PACOTE_COMUM
                
                pacotes_aplicados.append({
                    'usuario_codigo': usuario_codigo,
                    'usuario_nome': grupo['usuario_nome'].iloc[0] if 'usuario_nome' in grupo.columns else '',
                    'mes_ano': mes_ano_str,
                    'quantidade_sessoes': total_sessoes,
                    'tipo_pacote': tipo_pacote,
                    'valor_pacote': valor_pacote,
                    'sessoes_ids': grupo.index.tolist()
                })
                
                logging.info(f"🎯 PACOTE DETECTADO: {usuario_codigo} - {total_sessoes} sessões - {tipo_pacote} - R$ {valor_pacote}")
        
        logging.info(f"Total de pacotes detectados: {len(pacotes_aplicados)}")
        return pacotes_aplicados
    
    def validar_empresa_procedimento(self, df_processado):
        """Valida se o procedimento é permitido para a empresa"""
        inconsistencias = []
        
        for idx, row in df_processado.iterrows():
            empresa = row.get('empresa', '')
            procedimento_nome = row.get('procedimento_nome', '')
            
            if empresa in VALIDACAO_PROCEDIMENTOS:
                procedimentos_permitidos = VALIDACAO_PROCEDIMENTOS[empresa]
                if procedimento_nome not in procedimentos_permitidos:
                    inconsistencias.append({
                        'registro_id': idx,
                        'empresa': empresa,
                        'procedimento_nome': procedimento_nome,
                        'usuario_codigo': row.get('usuario_codigo', ''),
                        'usuario_nome': row.get('usuario_nome', ''),
                        'data_execucao': row.get('data_execucao', ''),
                        'motivo': f'Procedimento "{procedimento_nome}" não permitido para empresa "{empresa}"'
                    })
            else:
                inconsistencias.append({
                    'registro_id': idx,
                    'empresa': empresa,
                    'procedimento_nome': procedimento_nome,
                    'usuario_codigo': row.get('usuario_codigo', ''),
                    'usuario_nome': row.get('usuario_nome', ''),
                    'data_execucao': row.get('data_execucao', ''),
                    'motivo': f'Empresa "{empresa}" não configurada no sistema'
                })
                
        return inconsistencias
    
    def aplicar_pacotes(self, df_producao, pacotes):
        """Aplica valores de pacotes anulando sessões individuais"""
        df_processado = df_producao.copy()
        
        # Criar coluna de valor calculado
        df_processado['valor_unitario'] = df_processado.apply(
            lambda row: self.calcular_valor_procedimento(
                row.get('procedimento_codigo', ''), 
                row.get('usuario_codigo', ''),
                row.get('medico_nome', '')
            ), axis=1
        )
        
        # Criar set de sessões que fazem parte de pacotes
        sessoes_em_pacotes = set()
        for pacote in pacotes:
            sessoes_em_pacotes.update(pacote['sessoes_ids'])
        
        # Anular valores das sessões que fazem parte de pacotes
        df_processado.loc[df_processado.index.isin(sessoes_em_pacotes), 'valor_unitario'] = 0.0
        
        # Adicionar registros de pacotes como novas linhas
        for pacote in pacotes:
            novo_registro = {
                'empresa': 'PACOTE',
                'servico': f"Pacote {pacote['tipo_pacote'].upper()}",
                'rede': '',
                'data_execucao': '', 
                'usuario_codigo': pacote['usuario_codigo'],
                'usuario_nome': pacote['usuario_nome'],
                'medico_codigo': '',
                'medico_nome': 'SISTEMA',
                'procedimento_codigo': 'PACOTE',
                'procedimento_nome': f"Pacote {pacote['quantidade_sessoes']} sessões - {pacote['tipo_pacote']}",
                'urgencia': '',
                'qtde_autorizada': pacote['quantidade_sessoes'],
                'qtde_realizada': pacote['quantidade_sessoes'],
                'data_autorizacao': '',
                'numero_guia': '',
                'senha': '',
                'valor_unitario': pacote['valor_pacote']
            }
            df_processado = pd.concat([df_processado, pd.DataFrame([novo_registro])], ignore_index=True)
        
        return df_processado
    
    def gerar_resumos(self, df_processado):
        """Gera todos os resumos necessários"""
        resumos = {
            'resumo_financeiro': {},
            'resumo_por_empresa': {},
            'resumo_por_especialidade': {},
            'resumo_por_medico': {},
            'resumo_por_paciente': {}
        }
        
        # Resumo financeiro geral
        total_faturado = df_processado['valor_unitario'].sum()
        total_registros = len(df_processado)
        # Contar pacotes (registros com procedimento_codigo = 'PACOTE')
        total_pacotes = len(df_processado[df_processado['procedimento_codigo'] == 'PACOTE'])
        # Contar inconsistências (se existir coluna has_inconsistencia)
        total_inconsistencias = 0
        if 'has_inconsistencia' in df_processado.columns:
            total_inconsistencias = df_processado['has_inconsistencia'].sum()
        
        resumos['resumo_financeiro'] = {
            'total_faturado': total_faturado,
            'total_registros': total_registros,
            'total_pacotes': total_pacotes,
            'total_inconsistencias': total_inconsistencias,
            'valor_medio': total_faturado / total_registros if total_registros > 0 else 0
        }
        
        # Resumo por empresa
        empresa_dados = defaultdict(lambda: {'registros': 0, 'valor': 0})
        for _, row in df_processado.iterrows():
            empresa = row.get('empresa', 'N/A')
            valor = row.get('valor_unitario', 0)
            empresa_dados[empresa]['registros'] += 1
            empresa_dados[empresa]['valor'] += valor
        resumos['resumo_por_empresa'] = dict(empresa_dados)
        
        # Resumo por especialidade/procedimento
        esp_dados = defaultdict(lambda: {'sessoes': 0, 'valor': 0})
        for _, row in df_processado.iterrows():
            procedimento = row.get('procedimento_nome', 'N/A')
            valor = row.get('valor_unitario', 0)
            esp_dados[procedimento]['sessoes'] += 1
            esp_dados[procedimento]['valor'] += valor
        resumos['resumo_por_especialidade'] = dict(esp_dados)
        
        # Resumo por médico
        med_dados = defaultdict(lambda: {'sessoes': 0, 'valor': 0})
        for _, row in df_processado.iterrows():
            medico = row.get('medico_nome', 'N/A')
            valor = row.get('valor_unitario', 0)
            med_dados[medico]['sessoes'] += 1
            med_dados[medico]['valor'] += valor
        resumos['resumo_por_medico'] = dict(med_dados)
        
        # Resumo por paciente
        pac_dados = defaultdict(lambda: {'sessoes': 0, 'valor': 0})
        for _, row in df_processado.iterrows():
            paciente = f"{row.get('usuario_codigo', '')} - {row.get('usuario_nome', 'N/A')}"
            valor = row.get('valor_unitario', 0)
            pac_dados[paciente]['sessoes'] += 1
            pac_dados[paciente]['valor'] += valor
        resumos['resumo_por_paciente'] = dict(pac_dados)
        
        return resumos
    
    def process_faturamento(self, df_producao, excel_path=None):
        """Processa faturamento aplicando todas as regras de negócio conforme especificação"""
        if excel_path:
            self.load_carteirinhas_especiais(excel_path)
            
        resultado = {
            'dados_processados': [],
            'resumo_financeiro': {},
            'resumo_por_empresa': {},
            'resumo_por_especialidade': {},
            'resumo_por_medico': {},
            'resumo_por_paciente': {},
            'pacotes_aplicados': [],
            'inconsistencias': []
        }
        
        try:
            logging.info(f"Iniciando processamento de {len(df_producao)} registros")
            
            # Detectar pacotes de 12 sessões por mês/paciente
            pacotes = self.detectar_pacotes(df_producao.copy())
            resultado['pacotes_aplicados'] = pacotes
            logging.info(f"Detectados {len(pacotes)} pacotes")
            
            # Aplicar valores de pacotes (anular sessões individuais e aplicar valor do pacote)
            df_processado = self.aplicar_pacotes(df_producao.copy(), pacotes)
            
            # Validar inconsistências empresa x procedimento
            inconsistencias = self.validar_empresa_procedimento(df_processado)
            resultado['inconsistencias'] = inconsistencias
            logging.info(f"Detectadas {len(inconsistencias)} inconsistências")
            
            # Gerar resumos detalhados
            resumos = self.gerar_resumos(df_processado)
            resultado.update(resumos)
            
            logging.info(f"Faturamento total final: R$ {resultado['resumo_financeiro'].get('total_faturado', 0):.2f}")
            
            # Converter DataFrame para lista de dicionários para serialização
            resultado['dados_processados'] = df_processado.to_dict('records')
            
        except Exception as e:
            logging.error(f"Erro no processamento de faturamento: {e}")
            raise e
            
        return resultado