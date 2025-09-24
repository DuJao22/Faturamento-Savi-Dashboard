import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime
import logging
from typing import Dict, List, Tuple, Optional
import openpyxl
from models import ProcessedData, AnalysisSession
from app import db

class SAVIDataProcessor:
    """
    Processador de dados do sistema SAVI para análise de atendimentos TEA
    """
    
    def __init__(self, db_path: str, excel_path: Optional[str] = None):
        self.db_path = db_path
        self.excel_path = excel_path
        self.carteirinhas_df = None
        self.validation_rules = self._load_validation_rules()
        self.price_rules = self._load_price_rules()
        
        if excel_path:
            self._load_carteirinhas()
    
    def _load_carteirinhas(self):
        """Carrega a planilha de carteirinhas com preços especiais"""
        try:
            self.carteirinhas_df = pd.read_excel(self.excel_path)
            logging.info(f"Carteirinhas carregadas: {len(self.carteirinhas_df)} registros")
        except Exception as e:
            logging.error(f"Erro ao carregar carteirinhas: {e}")
            self.carteirinhas_df = pd.DataFrame()
    
    def _load_validation_rules(self) -> Dict:
        """Define as regras de validação empresa x procedimento"""
        return {
            # Exemplo de regras - deve ser configurado conforme necessário
            "EMPRESA_A": ["60.01.015-0", "00.01.001-4"],
            "EMPRESA_B": ["60.01.015-0"],
            # Adicionar mais regras conforme necessário
        }
    
    def _load_price_rules(self) -> Dict:
        """Define as regras de preços padrão e especiais"""
        return {
            "60.01.015-0": {"padrao": 53.12, "especial": 65.00},
            "00.01.001-4": {"padrao": 150.00, "especial": 180.00},
            # Adicionar mais procedimentos conforme necessário
        }
    
    def load_production_data(self) -> pd.DataFrame:
        """Carrega dados da tabela producao do banco SQLite"""
        try:
            conn = sqlite3.connect(self.db_path)
            query = """
            SELECT 
                empresa,
                procedimento_nome,
                procedimento_codigo,
                medico_nome,
                usuario_nome,
                usuario_codigo,
                valor,
                data_sessao,
                created_at
            FROM producao
            ORDER BY data_sessao, usuario_codigo
            """
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            # Converter data_sessao para datetime
            df['data_sessao'] = pd.to_datetime(df['data_sessao'])
            df['mes_ano'] = df['data_sessao'].dt.to_period('M')
            
            logging.info(f"Dados carregados: {len(df)} registros")
            return df
            
        except Exception as e:
            logging.error(f"Erro ao carregar dados de produção: {e}")
            return pd.DataFrame()
    
    def detect_packages(self, df: pd.DataFrame) -> pd.DataFrame:
        """Detecta pacotes de 12+ sessões no mesmo mês"""
        df_copy = df.copy()
        df_copy['is_pacote'] = False
        df_copy['tipo_pacote'] = None
        df_copy['valor_final'] = df_copy['valor']
        
        # Procedimentos elegíveis para pacote
        procedimentos_pacote = ["60.01.015-0"]  # Adicionar mais conforme necessário
        
        # Agrupar por paciente, procedimento e mês
        groups = df_copy.groupby(['usuario_codigo', 'procedimento_codigo', 'mes_ano'])
        for group_key, group in groups:
            usuario_codigo, procedimento_codigo, mes_ano = group_key
            if procedimento_codigo in procedimentos_pacote and len(group) >= 12:
                # Verificar se é pacote especial (paciente tem carteirinha)
                is_especial = False
                if self.carteirinhas_df is not None and not self.carteirinhas_df.empty:
                    is_especial = usuario_codigo in self.carteirinhas_df['usuario_codigo'].values
                
                tipo_pacote = 'especial' if is_especial else 'comum'
                valor_pacote = 1600.00 if is_especial else 1150.00
                
                # Marcar todas as sessões do grupo como pacote
                indices = group.index
                df_copy.loc[indices, 'is_pacote'] = True
                df_copy.loc[indices, 'tipo_pacote'] = tipo_pacote
                
                # Aplicar valor do pacote apenas na primeira sessão, zerar as outras
                df_copy.loc[indices[0], 'valor_final'] = valor_pacote
                df_copy.loc[indices[1:], 'valor_final'] = 0.0
                
                logging.info(f"Pacote {tipo_pacote} detectado: {usuario_codigo} - {procedimento_codigo} - {mes_ano} ({len(group)} sessões)")
        
        return df_copy
    
    def apply_special_pricing(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aplica preços especiais baseados na planilha de carteirinhas"""
        if self.carteirinhas_df is None or self.carteirinhas_df.empty:
            return df
        
        df_copy = df.copy()
        
        for idx, row in df_copy.iterrows():
            if not bool(row['is_pacote']):  # Não aplicar preços especiais em pacotes
                procedimento_codigo = row['procedimento_codigo']
                usuario_codigo = row['usuario_codigo']
                
                if procedimento_codigo in self.price_rules:
                    # Verificar se usuário tem carteirinha especial
                    has_carteirinha = usuario_codigo in self.carteirinhas_df['usuario_codigo'].values
                    
                    if has_carteirinha:
                        valor_especial = self.price_rules[procedimento_codigo]['especial']
                        df_copy.loc[idx, 'valor_final'] = valor_especial
                        logging.debug(f"Preço especial aplicado: {usuario_codigo} - {procedimento_codigo} - R$ {valor_especial}")
        
        return df_copy
    
    def apply_rafael_elian_rule(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aplica regra especial para código 00.01.001-4 com RAFAEL ELIAN"""
        df_copy = df.copy()
        
        mask = (df_copy['procedimento_codigo'] == '00.01.001-4') & (df_copy['medico_nome'] == 'RAFAEL ELIAN')
        rafael_sessions = df_copy[mask]
        
        for idx, row in rafael_sessions.iterrows():
            if not bool(row['is_pacote']):
                usuario_codigo = row['usuario_codigo']
                
                # Verificar se paciente está na planilha
                has_carteirinha = False
                if self.carteirinhas_df is not None and not self.carteirinhas_df.empty:
                    has_carteirinha = usuario_codigo in self.carteirinhas_df['usuario_codigo'].values
                
                valor_rafael = 180.00 if has_carteirinha else 150.00
                df_copy.loc[idx, 'valor_final'] = valor_rafael
                
                logging.info(f"Regra Rafael Elian aplicada: {usuario_codigo} - R$ {valor_rafael}")
        
        return df_copy
    
    def validate_empresa_procedimento(self, df: pd.DataFrame) -> pd.DataFrame:
        """Valida se procedimentos foram realizados nas empresas corretas"""
        df_copy = df.copy()
        df_copy['has_inconsistencia'] = False
        df_copy['inconsistencia_descricao'] = ''
        
        for idx, row in df_copy.iterrows():
            empresa = row['empresa']
            procedimento_codigo = row['procedimento_codigo']
            
            # Verificar se empresa está nas regras
            if empresa in self.validation_rules:
                allowed_procedures = self.validation_rules[empresa]
                if procedimento_codigo not in allowed_procedures:
                    df_copy.loc[idx, 'has_inconsistencia'] = True
                    df_copy.loc[idx, 'inconsistencia_descricao'] = f"Procedimento {procedimento_codigo} não autorizado para empresa {empresa}"
                    logging.warning(f"Inconsistência: {empresa} x {procedimento_codigo}")
        
        return df_copy
    
    def process_data(self, session_id: int) -> Dict:
        """Processa todos os dados e retorna relatório consolidado"""
        try:
            # Carregar dados
            df = self.load_production_data()
            if df.empty:
                return {"error": "Nenhum dado encontrado na tabela producao"}
            
            # Aplicar todas as regras de negócio
            df = self.detect_packages(df)
            df = self.apply_special_pricing(df)
            df = self.apply_rafael_elian_rule(df)
            df = self.validate_empresa_procedimento(df)
            
            # Salvar dados processados no banco
            self._save_processed_data(df, session_id)
            
            # Gerar relatório consolidado
            report = self._generate_consolidated_report(df, session_id)
            
            return report
            
        except Exception as e:
            logging.error(f"Erro no processamento de dados: {e}")
            return {"error": str(e)}
    
    def _save_processed_data(self, df: pd.DataFrame, session_id: int):
        """Salva dados processados no banco"""
        try:
            for _, row in df.iterrows():
                processed_data = ProcessedData()
                processed_data.session_id = session_id
                processed_data.empresa = row['empresa']
                processed_data.procedimento_nome = row['procedimento_nome']
                processed_data.procedimento_codigo = row['procedimento_codigo']
                processed_data.medico_nome = row['medico_nome']
                processed_data.usuario_nome = row['usuario_nome']
                processed_data.usuario_codigo = row['usuario_codigo']
                processed_data.valor_original = row['valor']
                processed_data.valor_final = row['valor_final']
                processed_data.data_sessao = row['data_sessao'] if hasattr(row['data_sessao'], 'date') else row['data_sessao']
                processed_data.is_pacote = row['is_pacote']
                processed_data.tipo_pacote = row.get('tipo_pacote')
                processed_data.has_inconsistencia = row['has_inconsistencia']
                processed_data.inconsistencia_descricao = row['inconsistencia_descricao']
                db.session.add(processed_data)
            
            db.session.commit()
            logging.info(f"Dados processados salvos: {len(df)} registros")
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Erro ao salvar dados processados: {e}")
            raise
    
    def _generate_consolidated_report(self, df: pd.DataFrame, session_id: int) -> Dict:
        """Gera relatório consolidado"""
        try:
            # Estatísticas gerais
            total_records = len(df)
            total_faturado = df['valor_final'].sum()
            total_pacotes = df[df['is_pacote']].groupby(['usuario_codigo', 'procedimento_codigo', 'mes_ano']).ngroups
            inconsistencias = df['has_inconsistencia'].sum()
            
            # Relatórios por categoria
            faturamento_empresa = df.groupby('empresa')['valor_final'].sum().to_dict()
            faturamento_procedimento = df.groupby('procedimento_nome')['valor_final'].sum().to_dict()
            faturamento_medico = df.groupby('medico_nome')['valor_final'].sum().to_dict()
            
            # Pacotes detectados
            pacotes_info = []
            pacotes_df = df[df['is_pacote']].groupby(['usuario_codigo', 'procedimento_codigo', 'mes_ano', 'tipo_pacote']).agg({
                'valor_final': 'sum',
                'data_sessao': 'count'
            }).reset_index()
            
            for _, pacote in pacotes_df.iterrows():
                if pacote['valor_final'] > 0:  # Apenas o registro com valor
                    pacotes_info.append({
                        'usuario_codigo': pacote['usuario_codigo'],
                        'procedimento_codigo': pacote['procedimento_codigo'],
                        'mes_ano': str(pacote['mes_ano']),
                        'tipo_pacote': pacote['tipo_pacote'],
                        'valor': pacote['valor_final'],
                        'sessoes': pacote['data_sessao']
                    })
            
            # Inconsistências
            inconsistencias_list = []
            if inconsistencias > 0:
                inconsistencias_df = df[df['has_inconsistencia']]
                for _, inc in inconsistencias_df.iterrows():
                    inconsistencias_list.append({
                        'empresa': inc['empresa'],
                        'procedimento_codigo': inc['procedimento_codigo'],
                        'procedimento_nome': inc['procedimento_nome'],
                        'usuario_codigo': inc['usuario_codigo'],
                        'descricao': inc['inconsistencia_descricao']
                    })
            
            # Atualizar sessão com estatísticas
            session = AnalysisSession.query.get(session_id)
            if session:
                session.total_records = total_records
                session.total_faturado = total_faturado
                session.total_pacotes = total_pacotes
                session.inconsistencias = inconsistencias
                session.status = 'completed'
                db.session.commit()
            
            return {
                'success': True,
                'statistics': {
                    'total_records': total_records,
                    'total_faturado': total_faturado,
                    'total_pacotes': total_pacotes,
                    'inconsistencias': inconsistencias
                },
                'faturamento_empresa': faturamento_empresa,
                'faturamento_procedimento': faturamento_procedimento,
                'faturamento_medico': faturamento_medico,
                'pacotes': pacotes_info,
                'inconsistencias': inconsistencias_list
            }
            
        except Exception as e:
            logging.error(f"Erro ao gerar relatório consolidado: {e}")
            return {"error": str(e)}
