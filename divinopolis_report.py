import pandas as pd
import sqlite3
import logging
from collections import defaultdict
from datetime import datetime

"""
Módulo para geração de relatório específico de Divinópolis
Cruza dados entre planilha Excel e banco de dados SQLite
"""

class DivinopolisReportGenerator:
    def __init__(self, db_path, excel_path):
        self.db_path = db_path
        self.excel_path = excel_path
        self.logger = logging.getLogger(__name__)

    def load_excel_users(self):
        """Carrega usuários da planilha de Divinópolis"""
        try:
            df_excel = pd.read_excel(self.excel_path)
            # Normalizar nomes das colunas
            df_excel.columns = df_excel.columns.str.lower().str.strip()
            
            # Verificar colunas disponíveis
            self.logger.info(f"Colunas da planilha Excel: {list(df_excel.columns)}")
            
            # Tentar diferentes nomes possíveis para codigo do usuario
            codigo_columns = ['usuario_codigo', 'codigo_usuario', 'codigo', 'usuario', 'cod_usuario']
            codigo_col = None
            for col in codigo_columns:
                if col in df_excel.columns:
                    codigo_col = col
                    break
            
            if not codigo_col:
                raise ValueError(f"Coluna de código do usuário não encontrada. Colunas disponíveis: {list(df_excel.columns)}")
            
            # Criar lista de códigos de usuários de Divinópolis
            divinopolis_users = set(df_excel[codigo_col].astype(str).str.strip())
            self.logger.info(f"Carregados {len(divinopolis_users)} usuários de Divinópolis da planilha")
            
            return divinopolis_users, df_excel
            
        except Exception as e:
            self.logger.error(f"Erro ao carregar planilha Excel: {e}")
            raise

    def load_database_data(self, divinopolis_users):
        """Carrega dados do banco que correspondem APENAS aos usuários de Divinópolis"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            if not divinopolis_users:
                self.logger.warning("Nenhum usuário de Divinópolis encontrado na planilha")
                return pd.DataFrame()
            
            # Carregar dados da tabela producao APENAS para usuários de Divinópolis
            placeholders = ','.join(['?' for _ in divinopolis_users])
            query = f"""
            SELECT * FROM producao 
            WHERE usuario_codigo IN ({placeholders})
            ORDER BY usuario_codigo, data_execucao
            """
            
            df_producao = pd.read_sql_query(query, conn, params=list(divinopolis_users))
            conn.close()
            
            self.logger.info(f"Carregados {len(df_producao)} registros de produção EXCLUSIVAMENTE para usuários de Divinópolis")
            self.logger.info(f"Usuários únicos encontrados: {df_producao['usuario_codigo'].nunique()}")
            
            return df_producao
            
        except Exception as e:
            self.logger.error(f"Erro ao carregar dados do banco: {e}")
            raise

    def calculate_values(self, df_producao, divinopolis_users):
        """Calcula valores baseado nas regras de negócio APENAS para usuários de Divinópolis"""
        # Importar business logic para usar as mesmas regras
        from business_logic import SAVIBusinessLogic
        
        # Criar instância da lógica de negócio
        business_logic = SAVIBusinessLogic()
        
        # Configurar carteirinhas especiais APENAS com usuários de Divinópolis
        # Isso garante que apenas usuários desta lista tenham preços especiais
        business_logic.carteirinhas_especiais = set(str(user) for user in divinopolis_users)
        
        self.logger.info(f"Configuradas {len(business_logic.carteirinhas_especiais)} carteirinhas especiais de Divinópolis")
        
        # Aplicar cálculo de valores
        df_producao['valor_unitario'] = df_producao.apply(
            lambda row: business_logic.calcular_valor_procedimento(
                row.get('procedimento_codigo', ''), 
                row.get('usuario_codigo', ''),
                row.get('medico_nome', '')
            ), axis=1
        )
        
        return df_producao

    def generate_report(self):
        """Gera relatório completo de Divinópolis"""
        try:
            # Carregar usuários da planilha
            divinopolis_users, df_excel = self.load_excel_users()
            
            # Carregar dados do banco para esses usuários
            df_producao = self.load_database_data(divinopolis_users)
            
            if df_producao.empty:
                return {
                    'status': 'warning',
                    'message': 'Nenhum registro encontrado no banco de dados para os usuários de Divinópolis',
                    'total_usuarios_planilha': len(divinopolis_users),
                    'total_registros_encontrados': 0
                }
            
            # Calcular valores usando apenas carteirinhas de Divinópolis
            df_producao = self.calculate_values(df_producao, divinopolis_users)
            
            # Gerar estatísticas
            report = self._generate_statistics(df_producao, divinopolis_users, df_excel)
            
            return report
            
        except Exception as e:
            self.logger.error(f"Erro ao gerar relatório de Divinópolis: {e}")
            return {
                'status': 'error',
                'message': f'Erro ao processar dados: {str(e)}'
            }

    def _generate_statistics(self, df_producao, divinopolis_users, df_excel):
        """Gera estatísticas detalhadas do relatório"""
        
        # Estatísticas gerais
        total_usuarios_planilha = len(divinopolis_users)
        usuarios_encontrados = set(df_producao['usuario_codigo'].astype(str))
        usuarios_nao_encontrados = divinopolis_users - usuarios_encontrados
        total_faturado = df_producao['valor_unitario'].sum()
        total_registros = len(df_producao)
        
        # Faturamento por usuário
        faturamento_por_usuario = df_producao.groupby(['usuario_codigo', 'usuario_nome']).agg({
            'valor_unitario': 'sum',
            'procedimento_codigo': 'count'
        }).reset_index()
        faturamento_por_usuario.columns = ['codigo', 'nome', 'valor_total', 'total_sessoes']
        faturamento_por_usuario = faturamento_por_usuario.sort_values('valor_total', ascending=False)
        
        # Faturamento por procedimento
        faturamento_por_procedimento = df_producao.groupby('procedimento_nome').agg({
            'valor_unitario': 'sum',
            'usuario_codigo': 'nunique',
            'procedimento_codigo': 'count'
        }).reset_index()
        faturamento_por_procedimento.columns = ['procedimento', 'valor_total', 'usuarios_unicos', 'total_sessoes']
        faturamento_por_procedimento = faturamento_por_procedimento.sort_values('valor_total', ascending=False)
        
        # Faturamento por médico
        faturamento_por_medico = df_producao.groupby('medico_nome').agg({
            'valor_unitario': 'sum',
            'usuario_codigo': 'nunique',
            'procedimento_codigo': 'count'
        }).reset_index()
        faturamento_por_medico.columns = ['medico', 'valor_total', 'usuarios_unicos', 'total_sessoes']
        faturamento_por_medico = faturamento_por_medico.sort_values('valor_total', ascending=False)
        
        # Faturamento por período (se existir coluna de data)
        faturamento_por_periodo = None
        if 'data_execucao' in df_producao.columns:
            try:
                df_producao['data_execucao'] = pd.to_datetime(df_producao['data_execucao'], errors='coerce')
                df_producao['ano_mes'] = df_producao['data_execucao'].dt.to_period('M')
                faturamento_por_periodo = df_producao.groupby('ano_mes').agg({
                    'valor_unitario': 'sum',
                    'usuario_codigo': 'nunique',
                    'procedimento_codigo': 'count'
                }).reset_index()
                faturamento_por_periodo.columns = ['periodo', 'valor_total', 'usuarios_unicos', 'total_sessoes']
                faturamento_por_periodo['periodo'] = faturamento_por_periodo['periodo'].astype(str)
            except:
                faturamento_por_periodo = None
        
        # Construir relatório final
        report = {
            'status': 'success',
            'timestamp': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
            'identificacao': 'RELATÓRIO DIVINÓPOLIS',
            'resumo_geral': {
                'total_usuarios_planilha': total_usuarios_planilha,
                'usuarios_encontrados': len(usuarios_encontrados),
                'usuarios_nao_encontrados': len(usuarios_nao_encontrados),
                'total_registros': total_registros,
                'total_faturado': total_faturado,
                'valor_medio_por_sessao': total_faturado / total_registros if total_registros > 0 else 0,
                'valor_medio_por_usuario': total_faturado / len(usuarios_encontrados) if usuarios_encontrados else 0
            },
            'faturamento_por_usuario': faturamento_por_usuario.head(20).to_dict('records'),
            'faturamento_por_procedimento': faturamento_por_procedimento.to_dict('records'),
            'faturamento_por_medico': faturamento_por_medico.to_dict('records'),
            'usuarios_nao_encontrados': list(usuarios_nao_encontrados),
            'detalhes_registros': df_producao.to_dict('records')[:100]  # Limitar a 100 registros para não sobrecarregar
        }
        
        if faturamento_por_periodo is not None:
            report['faturamento_por_periodo'] = faturamento_por_periodo.to_dict('records')
        
        return report