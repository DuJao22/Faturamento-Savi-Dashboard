import pandas as pd
from typing import Dict, List
from models import ProcessedData, AnalysisSession
import logging

class ReportGenerator:
    """
    Gerador de relatórios para análise SAVI
    """
    
    def __init__(self, session_id: int):
        self.session_id = session_id
        self.session = AnalysisSession.query.get(session_id)
        if not self.session:
            raise ValueError(f"Sessão {session_id} não encontrada")
    
    def generate_specialty_report(self) -> Dict:
        """Gera relatório por especialidade (procedimento)"""
        try:
            data = ProcessedData.query.filter_by(session_id=self.session_id).all()
            
            specialty_data = {}
            for record in data:
                specialty = record.procedimento_nome
                if specialty not in specialty_data:
                    specialty_data[specialty] = {
                        'total_sessoes': 0,
                        'total_faturado': 0,
                        'pacientes_unicos': set(),
                        'medicos_unicos': set(),
                        'empresas': set()
                    }
                
                specialty_data[specialty]['total_sessoes'] += 1
                specialty_data[specialty]['total_faturado'] += record.valor_final
                specialty_data[specialty]['pacientes_unicos'].add(record.usuario_codigo)
                specialty_data[specialty]['medicos_unicos'].add(record.medico_nome)
                specialty_data[specialty]['empresas'].add(record.empresa)
            
            # Converter sets para contadores
            for specialty in specialty_data:
                specialty_data[specialty]['pacientes_unicos'] = len(specialty_data[specialty]['pacientes_unicos'])
                specialty_data[specialty]['medicos_unicos'] = len(specialty_data[specialty]['medicos_unicos'])
                specialty_data[specialty]['empresas'] = len(specialty_data[specialty]['empresas'])
            
            return {
                'success': True,
                'data': specialty_data,
                'title': 'Relatório por Especialidade'
            }
            
        except Exception as e:
            logging.error(f"Erro ao gerar relatório por especialidade: {e}")
            return {'success': False, 'error': str(e)}
    
    def generate_packages_report(self) -> Dict:
        """Gera relatório de pacotes aplicados"""
        try:
            packages = ProcessedData.query.filter_by(
                session_id=self.session_id,
                is_pacote=True
            ).all()
            
            packages_data = {}
            for package in packages:
                key = f"{package.usuario_codigo}_{package.procedimento_codigo}_{package.data_sessao.strftime('%Y-%m')}"
                
                if key not in packages_data:
                    packages_data[key] = {
                        'usuario_codigo': package.usuario_codigo,
                        'usuario_nome': package.usuario_nome,
                        'procedimento_nome': package.procedimento_nome,
                        'procedimento_codigo': package.procedimento_codigo,
                        'mes_ano': package.data_sessao.strftime('%Y-%m'),
                        'tipo_pacote': package.tipo_pacote,
                        'total_sessoes': 0,
                        'valor_pacote': 0,
                        'empresa': package.empresa
                    }
                
                packages_data[key]['total_sessoes'] += 1
                if package.valor_final > 0:  # Apenas o registro com valor
                    packages_data[key]['valor_pacote'] = package.valor_final
            
            return {
                'success': True,
                'data': list(packages_data.values()),
                'title': 'Relatório de Pacotes Aplicados'
            }
            
        except Exception as e:
            logging.error(f"Erro ao gerar relatório de pacotes: {e}")
            return {'success': False, 'error': str(e)}
    
    def generate_company_report(self) -> Dict:
        """Gera relatório por empresa"""
        try:
            data = ProcessedData.query.filter_by(session_id=self.session_id).all()
            
            company_data = {}
            for record in data:
                empresa = record.empresa
                if empresa not in company_data:
                    company_data[empresa] = {
                        'total_sessoes': 0,
                        'total_faturado': 0,
                        'pacientes_unicos': set(),
                        'procedimentos': {},
                        'inconsistencias': 0
                    }
                
                company_data[empresa]['total_sessoes'] += 1
                company_data[empresa]['total_faturado'] += record.valor_final
                company_data[empresa]['pacientes_unicos'].add(record.usuario_codigo)
                
                # Contar procedimentos
                proc = record.procedimento_nome
                if proc not in company_data[empresa]['procedimentos']:
                    company_data[empresa]['procedimentos'][proc] = 0
                company_data[empresa]['procedimentos'][proc] += 1
                
                if record.has_inconsistencia:
                    company_data[empresa]['inconsistencias'] += 1
            
            # Converter sets para contadores
            for empresa in company_data:
                company_data[empresa]['pacientes_unicos'] = len(company_data[empresa]['pacientes_unicos'])
            
            return {
                'success': True,
                'data': company_data,
                'title': 'Relatório por Empresa'
            }
            
        except Exception as e:
            logging.error(f"Erro ao gerar relatório por empresa: {e}")
            return {'success': False, 'error': str(e)}
    
    def generate_doctor_report(self) -> Dict:
        """Gera relatório por médico"""
        try:
            data = ProcessedData.query.filter_by(session_id=self.session_id).all()
            
            doctor_data = {}
            for record in data:
                medico = record.medico_nome
                if medico not in doctor_data:
                    doctor_data[medico] = {
                        'total_sessoes': 0,
                        'total_faturado': 0,
                        'pacientes_unicos': set(),
                        'procedimentos': {},
                        'empresas': set()
                    }
                
                doctor_data[medico]['total_sessoes'] += 1
                doctor_data[medico]['total_faturado'] += record.valor_final
                doctor_data[medico]['pacientes_unicos'].add(record.usuario_codigo)
                doctor_data[medico]['empresas'].add(record.empresa)
                
                # Contar procedimentos
                proc = record.procedimento_nome
                if proc not in doctor_data[medico]['procedimentos']:
                    doctor_data[medico]['procedimentos'][proc] = 0
                doctor_data[medico]['procedimentos'][proc] += 1
            
            # Converter sets para contadores
            for medico in doctor_data:
                doctor_data[medico]['pacientes_unicos'] = len(doctor_data[medico]['pacientes_unicos'])
                doctor_data[medico]['empresas'] = len(doctor_data[medico]['empresas'])
            
            return {
                'success': True,
                'data': doctor_data,
                'title': 'Relatório por Médico'
            }
            
        except Exception as e:
            logging.error(f"Erro ao gerar relatório por médico: {e}")
            return {'success': False, 'error': str(e)}
    
    def generate_inconsistencies_report(self) -> Dict:
        """Gera relatório de inconsistências"""
        try:
            inconsistencies = ProcessedData.query.filter_by(
                session_id=self.session_id,
                has_inconsistencia=True
            ).all()
            
            inconsistencies_data = []
            for inc in inconsistencies:
                inconsistencies_data.append({
                    'empresa': inc.empresa,
                    'procedimento_codigo': inc.procedimento_codigo,
                    'procedimento_nome': inc.procedimento_nome,
                    'usuario_codigo': inc.usuario_codigo,
                    'usuario_nome': inc.usuario_nome,
                    'medico_nome': inc.medico_nome,
                    'data_sessao': inc.data_sessao.strftime('%d/%m/%Y'),
                    'valor_original': inc.valor_original,
                    'descricao': inc.inconsistencia_descricao
                })
            
            return {
                'success': True,
                'data': inconsistencies_data,
                'title': 'Relatório de Inconsistências',
                'total': len(inconsistencies_data)
            }
            
        except Exception as e:
            logging.error(f"Erro ao gerar relatório de inconsistências: {e}")
            return {'success': False, 'error': str(e)}
    
    def generate_all_reports(self) -> Dict:
        """Gera todos os relatórios"""
        return {
            'specialty': self.generate_specialty_report(),
            'packages': self.generate_packages_report(),
            'company': self.generate_company_report(),
            'doctor': self.generate_doctor_report(),
            'inconsistencies': self.generate_inconsistencies_report()
        }
