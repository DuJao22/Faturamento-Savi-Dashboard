from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, current_app, send_file
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
import logging
import pandas as pd
from datetime import datetime
from models import AnalysisSession, ProcessedData, User
from app import db
from data_processor import SAVIDataProcessor
from report_generator import ReportGenerator
from utils import save_uploaded_file, cleanup_old_files, format_currency

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('login.html')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    try:
        # Buscar todas as sessões completadas do usuário para seleção
        completed_sessions_list = AnalysisSession.query.filter_by(
            user_id=current_user.id, 
            status='completed'
        ).order_by(AnalysisSession.created_at.desc()).all()
        
        # Buscar últimas análises do usuário
        recent_sessions = AnalysisSession.query.filter_by(user_id=current_user.id)\
                                             .order_by(AnalysisSession.created_at.desc())\
                                             .limit(5).all()
        
        # Estatísticas gerais
        total_sessions = AnalysisSession.query.filter_by(user_id=current_user.id).count()
        completed_sessions = AnalysisSession.query.filter_by(user_id=current_user.id, status='completed').count()
        
        # Filtros de data do request
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        
        # Permitir seleção de sessão específica
        selected_session_id = request.args.get('session_id')
        if selected_session_id:
            selected_session = AnalysisSession.query.filter_by(
                id=selected_session_id, 
                user_id=current_user.id, 
                status='completed'
            ).first()
        else:
            selected_session = completed_sessions_list[0] if completed_sessions_list else None
        
        # Carregar dados da sessão selecionada
        dashboard_data = {}
        if selected_session and selected_session.db_file_path:
            try:
                processor = SAVIDataProcessor(selected_session.db_file_path, 
                                            selected_session.excel_file_path)
                dashboard_data = processor.get_dashboard_data()
                logging.info(f"Dashboard usando sessão {selected_session.id}: {selected_session.database_filename} ({dashboard_data.get('total_registros', 0)} registros)")
                
                # Aplicar filtros de data se fornecidos
                if data_inicio or data_fim:
                    dashboard_data = processor.filter_by_date(dashboard_data, data_inicio, data_fim)
                    
            except Exception as e:
                logging.error(f"Erro ao carregar dados da sessão {selected_session.id}: {e}")
                dashboard_data = {'error': str(e)}
        
        return render_template('dashboard.html', 
                             recent_sessions=recent_sessions,
                             total_sessions=total_sessions,
                             completed_sessions=completed_sessions,
                             completed_sessions_list=completed_sessions_list,
                             selected_session=selected_session,
                             dashboard_data=dashboard_data,
                             format_currency=format_currency,
                             data_inicio=data_inicio,
                             data_fim=data_fim)
    except Exception as e:
        logging.error(f"Erro no dashboard: {e}")
        flash('Erro ao carregar dados do dashboard.', 'error')
        return render_template('dashboard.html', 
                             recent_sessions=[],
                             total_sessions=0,
                             completed_sessions=0,
                             dashboard_data={},
                             format_currency=format_currency)

@main_bp.route('/live_analysis')
@login_required 
def live_analysis():
    """Página de análise detalhada dos dados reais"""
    try:
        processor = SAVIDataProcessor('instance/savi_assistant.db')
        analysis_data = processor.get_detailed_analysis()
        
        return render_template('analysis.html', 
                             analysis_data=analysis_data,
                             format_currency=format_currency)
    except Exception as e:
        logging.error(f"Erro na análise: {e}")
        flash('Erro ao carregar análise detalhada.', 'error')
        return render_template('analysis.html', 
                             analysis_data={},
                             format_currency=format_currency)

@main_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        try:
            # Verificar se os arquivos foram enviados
            if 'database_file' not in request.files:
                flash('Arquivo de banco de dados é obrigatório.', 'error')
                return render_template('upload.html')
            
            db_file = request.files['database_file']
            excel_file = request.files.get('excel_file')
            
            # Log para debug
            logging.info(f"Recebido arquivo de banco: {db_file.filename if db_file else 'None'}")
            logging.info(f"Recebido arquivo Excel: {excel_file.filename if excel_file and excel_file.filename else 'None'}")
            
            # Verificar se arquivo de banco foi selecionado
            if not db_file or db_file.filename == '':
                flash('Por favor, selecione um arquivo de banco de dados.', 'error')
                return render_template('upload.html')
            
            # Salvar arquivo de banco de dados
            db_path, db_message = save_uploaded_file(db_file, 'db')
            if not db_path:
                flash(f'Erro no arquivo de banco: {db_message}', 'error')
                logging.error(f"Erro ao salvar arquivo de banco: {db_message}")
                return render_template('upload.html')
            
            # Salvar arquivo Excel (opcional)
            excel_path = None
            if excel_file and excel_file.filename:
                excel_path, excel_message = save_uploaded_file(excel_file, 'excel')
                if not excel_path:
                    # Remover arquivo db se excel falhou
                    os.remove(db_path)
                    flash(f'Erro no arquivo Excel: {excel_message}', 'error')
                    return render_template('upload.html')
            
            # Criar nova sessão de análise
            session = AnalysisSession()
            session.user_id = current_user.id
            session.database_filename = db_file.filename
            session.excel_filename = excel_file.filename if excel_file and excel_file.filename else None
            session.db_file_path = db_path  # Salvar path do arquivo para usar no dashboard
            session.excel_file_path = excel_path  # Salvar path do Excel para carteirinhas
            session.status = 'processing'
            db.session.add(session)
            db.session.commit()
            
            flash(f'Arquivos enviados com sucesso! {db_message}', 'success')
            
            # Processar dados diretamente (sem thread assíncrona para evitar problemas de contexto)
            try:
                processor = SAVIDataProcessor(db_path, excel_path)
                resultado = processor.process_analysis_session(session.id)
                
                # Atualizar status da sessão com resultados
                session.status = 'completed'
                session.total_records = len(resultado['dados_processados'])
                session.total_faturado = resultado['resumo_financeiro']['total_faturado']
                session.total_pacotes = resultado['resumo_financeiro']['total_pacotes']
                session.inconsistencias = resultado['resumo_financeiro']['total_inconsistencias']
                db.session.commit()
                
                flash('Análise processada com sucesso!', 'success')
            except Exception as e:
                logging.error(f"Erro no processamento: {e}")
                session.status = 'error'
                db.session.commit()
                flash(f'Erro no processamento: {str(e)}', 'error')
            
            # NÃO limpar arquivos - mantê-los para uso no dashboard e relatórios
            # Os arquivos serão limpos apenas quando uma nova sessão for criada
            logging.info(f"Arquivos mantidos para uso futuro: DB={db_path}, Excel={excel_path or 'N/A'}")
            
            return redirect(url_for('main.analysis', session_id=session.id))
            
        except Exception as e:
            logging.error(f"Erro no upload: {e}")
            flash(f'Erro interno: {str(e)}', 'error')
            return render_template('upload.html')
    
    return render_template('upload.html')

# Removido processamento assíncrono para evitar problemas de contexto Flask

@main_bp.route('/analysis/<int:session_id>')
@login_required
def analysis(session_id):
    session = AnalysisSession.query.get_or_404(session_id)
    
    # Verificar se o usuário tem acesso a esta sessão
    if session.user_id != current_user.id and current_user.role != 'admin':
        flash('Acesso negado.', 'error')
        return redirect(url_for('main.dashboard'))
    
    return render_template('analysis.html', session=session, format_currency=format_currency)

@main_bp.route('/reports/<int:session_id>')
@login_required
def reports(session_id):
    session = AnalysisSession.query.get_or_404(session_id)
    
    # Verificar acesso
    if session.user_id != current_user.id and current_user.role != 'admin':
        flash('Acesso negado.', 'error')
        return redirect(url_for('main.dashboard'))
    
    if session.status != 'completed':
        flash('Análise ainda não foi concluída.', 'info')
        return redirect(url_for('main.analysis', session_id=session_id))
    
    # Gerar relatórios com dados reais do arquivo carregado pelo usuário
    try:
        # Usar dados do arquivo carregado pelo usuário se disponível
        if session.db_file_path:
            processor = SAVIDataProcessor(session.db_file_path, session.excel_file_path)
            logging.info(f"Usando dados da sessão {session.id} do arquivo carregado: {session.database_filename}")
        else:
            # Fallback para dados padrão
            processor = SAVIDataProcessor('instance/savi_assistant.db')
            logging.info("Usando dados padrão - arquivo do usuário não encontrado")
            
        df_producao = processor.load_data_from_sqlite()
        
        # Processar dados com business logic
        resultado = processor.business_logic.process_faturamento(df_producao)
        
        # Estruturar dados para o template
        reports_data = {
            'specialty': {
                'success': True,
                'data': resultado.get('resumo_por_especialidade', {}),
                'title': 'Relatório por Especialidade'
            },
            'packages': {
                'success': True,
                'data': resultado.get('pacotes_aplicados', []),
                'title': 'Pacotes Aplicados'
            },
            'company': {
                'success': True,
                'data': resultado.get('resumo_por_empresa', {}),
                'title': 'Relatório por Empresa'
            },
            'doctor': {
                'success': True,
                'data': resultado.get('resumo_por_medico', {}),
                'title': 'Relatório por Médico'
            },
            'inconsistencies': {
                'success': True,
                'data': resultado.get('inconsistencias', []),
                'title': 'Inconsistências Detectadas'
            }
        }
        
        return render_template('reports.html', 
                             session=session,
                             reports=reports_data,
                             format_currency=format_currency)
    
    except Exception as e:
        logging.error(f"Erro ao gerar relatórios: {e}")
        flash(f'Erro ao gerar relatórios: {str(e)}', 'error')
        return redirect(url_for('main.analysis', session_id=session_id))

@main_bp.route('/api/session-status/<int:session_id>')
@login_required
def session_status(session_id):
    """API endpoint para verificar status da sessão"""
    session = AnalysisSession.query.get_or_404(session_id)
    
    # Verificar acesso
    if session.user_id != current_user.id and current_user.role != 'admin':
        return jsonify({'error': 'Acesso negado'}), 403
    
    return jsonify({
        'status': session.status,
        'total_records': session.total_records,
        'total_faturado': session.total_faturado,
        'total_pacotes': session.total_pacotes,
        'inconsistencias': session.inconsistencias
    })

@main_bp.route('/api/chart-data/<int:session_id>')
@login_required
def chart_data(session_id):
    """API endpoint para dados dos gráficos"""
    session = AnalysisSession.query.get_or_404(session_id)
    
    # Verificar acesso
    if session.user_id != current_user.id and current_user.role != 'admin':
        return jsonify({'error': 'Acesso negado'}), 403
    
    try:
        # Dados por empresa
        empresa_data = db.session.query(
            ProcessedData.empresa,
            db.func.sum(ProcessedData.valor_final).label('total')
        ).filter_by(session_id=session_id).group_by(ProcessedData.empresa).all()
        
        # Dados por procedimento
        procedimento_data = db.session.query(
            ProcessedData.procedimento_nome,
            db.func.sum(ProcessedData.valor_final).label('total')
        ).filter_by(session_id=session_id).group_by(ProcessedData.procedimento_nome).all()
        
        # Dados por médico
        medico_data = db.session.query(
            ProcessedData.medico_nome,
            db.func.sum(ProcessedData.valor_final).label('total')
        ).filter_by(session_id=session_id).group_by(ProcessedData.medico_nome).all()
        
        return jsonify({
            'empresa': {
                'labels': [item.empresa for item in empresa_data],
                'data': [float(item.total) for item in empresa_data]
            },
            'procedimento': {
                'labels': [item.procedimento_nome for item in procedimento_data],
                'data': [float(item.total) for item in procedimento_data]
            },
            'medico': {
                'labels': [item.medico_nome for item in medico_data],
                'data': [float(item.total) for item in medico_data]
            }
        })
    
    except Exception as e:
        logging.error(f"Erro ao buscar dados dos gráficos: {e}")
        return jsonify({'error': str(e)}), 500

@main_bp.route('/delete-session/<int:session_id>', methods=['POST'])
@login_required
def delete_session(session_id):
    """Deletar uma sessão de análise e todos os dados relacionados"""
    try:
        session = AnalysisSession.query.get_or_404(session_id)
        
        # Verificar acesso - só o dono ou admin pode deletar
        if session.user_id != current_user.id and current_user.role != 'admin':
            flash('Acesso negado para deletar esta análise.', 'error')
            return redirect(url_for('main.dashboard'))
        
        # Deletar dados processados relacionados
        ProcessedData.query.filter_by(session_id=session_id).delete()
        
        # Deletar a sessão
        db.session.delete(session)
        db.session.commit()
        
        flash(f'Análise #{session_id} deletada com sucesso.', 'success')
        logging.info(f"Usuário {current_user.username} deletou sessão {session_id}")
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Erro ao deletar sessão {session_id}: {e}")
        flash('Erro ao deletar análise.', 'error')
    
    return redirect(url_for('main.dashboard'))

@main_bp.route('/pacotes/<int:session_id>')
@login_required
def view_pacotes(session_id):
    """Visualizar pacotes detectados em uma sessão"""
    session = AnalysisSession.query.get_or_404(session_id)
    
    # Verificar acesso
    if session.user_id != current_user.id and current_user.role != 'admin':
        flash('Acesso negado.', 'error')
        return redirect(url_for('main.dashboard'))
    
    try:
        # Usar dados do arquivo carregado pelo usuário se disponível
        if session.db_file_path:
            processor = SAVIDataProcessor(session.db_file_path, session.excel_file_path)
            logging.info(f"Carregando pacotes da sessão {session.id}: {session.database_filename}")
        else:
            processor = SAVIDataProcessor('instance/savi_assistant.db')
            logging.info("Usando dados padrão para visualizar pacotes")
            
        df_producao = processor.load_data_from_sqlite()
        pacotes = processor.business_logic.detectar_pacotes(df_producao)
        
        return render_template('pacotes.html', 
                             session=session,
                             pacotes=pacotes,
                             format_currency=format_currency)
    
    except Exception as e:
        logging.error(f"Erro ao carregar pacotes: {e}")
        flash(f'Erro ao carregar pacotes: {str(e)}', 'error')
        return redirect(url_for('main.analysis', session_id=session_id))

@main_bp.route('/api/dashboard-charts')
@login_required
def dashboard_charts_data():
    """API endpoint para dados dos gráficos do dashboard principal"""
    try:
        # Carregar dados em tempo real do banco principal
        processor = SAVIDataProcessor('instance/savi_assistant.db')
        dashboard_data = processor.get_dashboard_data()
        
        if not dashboard_data:
            return jsonify({'error': 'Nenhum dado disponível'}), 404
        
        # Calcular dados para o gráfico Divinópolis vs BH/Contagem
        divinopolis_data = dashboard_data.get('divinopolis', {})
        valor_divinopolis = float(divinopolis_data.get('valor_faturado', 0) or 0)
        valor_total = float(dashboard_data.get('resumo_financeiro', {}).get('total_faturado', 0) or 0)
        valor_bh_contagem = max(0, valor_total - valor_divinopolis)
        
        # Debug: Log dos valores calculados
        logging.info(f"[API] Valor Divinópolis: R$ {valor_divinopolis:,.2f}")
        logging.info(f"[API] Valor Total: R$ {valor_total:,.2f}")
        logging.info(f"[API] Valor BH/Contagem: R$ {valor_bh_contagem:,.2f}")
        
        # Preparar dados dos gráficos
        chart_data = {
            'empresas': {
                'labels': list(dashboard_data.get('resumo_por_empresa', {}).keys()),
                'data': [float(dados.get('valor', 0)) for dados in dashboard_data.get('resumo_por_empresa', {}).values()],
                'backgroundColor': ['#0d6efd', '#198754', '#dc3545', '#ffc107', '#6f42c1', '#fd7e14', '#20c997', '#e83e8c']
            },
            'especialidades': {
                'labels': [esp[:20] + '...' if len(esp) > 20 else esp for esp in list(dashboard_data.get('resumo_por_especialidade', {}).keys())[:10]],
                'data': [int(dados.get('sessoes', 0)) for dados in list(dashboard_data.get('resumo_por_especialidade', {}).values())[:10]]
            },
            'medicos_top': {
                'labels': [med[:25] + '...' if len(med) > 25 else med for med in list(dashboard_data.get('resumo_por_medico', {}).keys())[:10]],
                'data': [float(dados.get('valor', 0)) for dados in list(dashboard_data.get('resumo_por_medico', {}).values())[:10]]
            },
            'divinopolis_vs_bh': {
                'labels': ['Divinópolis', 'BH/Contagem'],
                'data': [valor_divinopolis, valor_bh_contagem],
                'backgroundColor': ['#28a745', '#0d6efd'],
                'formatted_data': [
                    f"R$ {valor_divinopolis:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                    f"R$ {valor_bh_contagem:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                ]
            },
            'faturamento_mes': {
                'labels': ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'],
                'data': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]  # Placeholder - seria calculado por mês
            }
        }
        
        return jsonify(chart_data)
        
    except Exception as e:
        logging.error(f"Erro ao buscar dados dos gráficos do dashboard: {e}")
        return jsonify({'error': str(e)}), 500

@main_bp.route('/general-report')
@login_required
def general_report():
    """Página de relatório geral com dashboard interativo"""
    return render_template('general_report.html')

@main_bp.route('/api/general-report/filters')
@login_required
def general_report_filters():
    """API endpoint para opções de filtros do relatório geral"""
    try:
        # Usar dados da sessão mais recente ou dados padrão
        completed_sessions = AnalysisSession.query.filter_by(
            user_id=current_user.id, status='completed'
        ).order_by(AnalysisSession.created_at.desc()).all()
        
        if not completed_sessions:
            processor = SAVIDataProcessor('instance/savi_assistant.db')
        else:
            latest_session = completed_sessions[0]
            processor = SAVIDataProcessor(latest_session.db_file_path, latest_session.excel_file_path)
        
        df_producao = processor.load_data_from_sqlite()
        
        if df_producao.empty:
            return jsonify({
                'empresas': [],
                'especialidades': [],
                'medicos': []
            })
        
        filters_data = {
            'empresas': sorted(df_producao['empresa'].dropna().unique().tolist()),
            'especialidades': sorted(df_producao['procedimento_nome'].dropna().unique().tolist()),
            'medicos': sorted(df_producao['medico_nome'].dropna().unique().tolist())[:50]  # Limitar a 50 para performance
        }
        
        return jsonify(filters_data)
        
    except Exception as e:
        logging.error(f"Erro ao carregar filtros do relatório geral: {e}")
        return jsonify({'error': str(e)}), 500

@main_bp.route('/api/general-report/data')
@login_required
def general_report_data():
    """API endpoint para dados do dashboard interativo"""
    try:
        # Obter filtros da query string
        filters = {
            'start_date': request.args.get('start_date'),
            'end_date': request.args.get('end_date'),
            'empresa': request.args.get('empresa'),
            'especialidade': request.args.get('especialidade'),
            'medico': request.args.get('medico'),
            'regiao': request.args.get('regiao'),
            'carteira': request.args.get('carteira')
        }
        
        # Remover filtros vazios
        filters = {k: v for k, v in filters.items() if v}
        
        logging.info(f"Aplicando filtros no relatório geral: {filters}")
        
        # Usar dados da sessão mais recente ou dados padrão
        completed_sessions = AnalysisSession.query.filter_by(
            user_id=current_user.id, status='completed'
        ).order_by(AnalysisSession.created_at.desc()).all()
        
        if not completed_sessions:
            processor = SAVIDataProcessor('instance/savi_assistant.db')
        else:
            latest_session = completed_sessions[0]
            processor = SAVIDataProcessor(latest_session.db_file_path, latest_session.excel_file_path)
        
        # Carregar e filtrar dados
        df_producao = processor.load_data_from_sqlite()
        
        if df_producao.empty:
            return jsonify({'error': 'Nenhum dado disponível'}), 404
        
        # Aplicar filtros
        df_filtered = df_producao.copy()
        
        # Filtro de data
        if filters.get('start_date') or filters.get('end_date'):
            df_filtered['data_execucao'] = pd.to_datetime(df_filtered['data_execucao'], format='%d/%m/%Y', errors='coerce')
            
            if filters.get('start_date'):
                start_date = pd.to_datetime(filters['start_date'])
                df_filtered = df_filtered[df_filtered['data_execucao'] >= start_date]
            
            if filters.get('end_date'):
                end_date = pd.to_datetime(filters['end_date'])
                df_filtered = df_filtered[df_filtered['data_execucao'] <= end_date]
        
        # Outros filtros
        if filters.get('empresa'):
            df_filtered = df_filtered[df_filtered['empresa'] == filters['empresa']]
        
        if filters.get('especialidade'):
            df_filtered = df_filtered[df_filtered['procedimento_nome'] == filters['especialidade']]
        
        if filters.get('medico'):
            df_filtered = df_filtered[df_filtered['medico_nome'] == filters['medico']]
        
        # Filtro por região (requer lógica específica)
        if filters.get('regiao') == 'divinopolis':
            divinopolis_data = processor._calculate_divinopolis_data(df_producao)
            # Filtrar apenas usuários de Divinópolis se houver dados específicos
            pass  # Implementar lógica específica se necessário
        
        # Processar dados filtrados
        resultado = processor.business_logic.process_faturamento(df_filtered, processor.excel_path)
        
        # Calcular métricas principais
        metrics = {
            'faturamento_total': resultado['resumo_financeiro'].get('total_faturado', 0),
            'total_sessoes': len(df_filtered),
            'total_pacientes': df_filtered['usuario_codigo'].nunique(),
            'total_medicos': df_filtered['medico_nome'].nunique()
        }
        
        # Preparar dados dos gráficos
        charts_data = {
            'faturamento_periodo': _calculate_faturamento_periodo(df_filtered),
            'empresas': _prepare_empresas_data(resultado['resumo_por_empresa']),
            'medicos': _prepare_medicos_data(resultado['resumo_por_medico']),
            'especialidades': _prepare_especialidades_data(resultado['resumo_por_especialidade']),
            'regional': _calculate_regional_data(processor, df_producao),
            'pacotes': _prepare_pacotes_data(resultado['pacotes_aplicados'])
        }
        
        return jsonify({
            'metrics': metrics,
            'charts': charts_data
        })
        
    except Exception as e:
        logging.error(f"Erro ao carregar dados do relatório geral: {e}")
        return jsonify({'error': str(e)}), 500

def _calculate_faturamento_periodo(df):
    """Calcular faturamento por período (mensal)"""
    try:
        if df.empty or 'valor_unitario' not in df.columns:
            return {'labels': [], 'data': []}
            
        df_periodo = df.copy()
        
        # Converter data_execucao se necessário
        if 'data_execucao' in df_periodo.columns:
            df_periodo['data_execucao'] = pd.to_datetime(df_periodo['data_execucao'], format='%d/%m/%Y', errors='coerce')
            df_periodo['mes_ano'] = df_periodo['data_execucao'].dt.to_period('M')
            
            faturamento_mensal = df_periodo.groupby('mes_ano')['valor_unitario'].sum().sort_index()
            
            return {
                'labels': [str(mes) for mes in faturamento_mensal.index],
                'data': faturamento_mensal.values.tolist()
            }
        else:
            # Se não houver coluna de data, agrupar por mês atual
            total_faturamento = df_periodo['valor_unitario'].sum()
            mes_atual = datetime.now().strftime('%Y-%m')
            return {
                'labels': [mes_atual],
                'data': [total_faturamento]
            }
            
    except Exception as e:
        logging.error(f"Erro ao calcular faturamento por período: {e}")
        return {'labels': [], 'data': []}

def _prepare_empresas_data(empresas_resumo):
    """Preparar dados de empresas para o gráfico"""
    if not empresas_resumo:
        return {'labels': [], 'data': []}
    
    # Pegar top 8 empresas
    empresas_sorted = sorted(empresas_resumo.items(), key=lambda x: x[1].get('valor', 0), reverse=True)[:8]
    
    return {
        'labels': [empresa for empresa, _ in empresas_sorted],
        'data': [dados.get('valor', 0) for _, dados in empresas_sorted]
    }

def _prepare_medicos_data(medicos_resumo):
    """Preparar dados de médicos para o gráfico"""
    if not medicos_resumo:
        return {'labels': [], 'data': []}
    
    # Pegar top 10 médicos
    medicos_sorted = sorted(medicos_resumo.items(), key=lambda x: x[1].get('valor', 0), reverse=True)[:10]
    
    return {
        'labels': [medico[:30] + '...' if len(medico) > 30 else medico for medico, _ in medicos_sorted],
        'data': [dados.get('valor', 0) for _, dados in medicos_sorted]
    }

def _prepare_especialidades_data(especialidades_resumo):
    """Preparar dados de especialidades para o gráfico"""
    if not especialidades_resumo:
        return {'labels': [], 'data': []}
    
    # Pegar top 10 especialidades
    especialidades_sorted = sorted(especialidades_resumo.items(), key=lambda x: x[1].get('sessoes', 0), reverse=True)[:10]
    
    return {
        'labels': [esp[:25] + '...' if len(esp) > 25 else esp for esp, _ in especialidades_sorted],
        'data': [dados.get('sessoes', 0) for _, dados in especialidades_sorted]
    }

def _calculate_regional_data(processor, df_producao):
    """Calcular dados regionais (Divinópolis vs BH/Contagem)"""
    try:
        divinopolis_data = processor._calculate_divinopolis_data(df_producao)
        valor_divinopolis = float(divinopolis_data.get('valor_faturado', 0))
        
        resultado = processor.business_logic.process_faturamento(df_producao, processor.excel_path)
        valor_total = float(resultado['resumo_financeiro'].get('total_faturado', 0))
        valor_bh_contagem = max(0, valor_total - valor_divinopolis)
        
        return {
            'labels': ['Divinópolis', 'BH/Contagem'],
            'data': [valor_divinopolis, valor_bh_contagem]
        }
    except Exception as e:
        logging.error(f"Erro ao calcular dados regionais: {e}")
        return {'labels': ['Divinópolis', 'BH/Contagem'], 'data': [0, 0]}

def _prepare_pacotes_data(pacotes_aplicados):
    """Preparar dados de pacotes para o gráfico"""
    if not pacotes_aplicados:
        return {'labels': ['Sem Pacotes', 'Com Pacotes'], 'data': [1, 0]}
    
    pacotes_comuns = sum(1 for p in pacotes_aplicados if p.get('tipo_pacote') == 'comum')
    pacotes_especiais = sum(1 for p in pacotes_aplicados if p.get('tipo_pacote') == 'especial')
    
    return {
        'labels': ['Pacotes Comuns', 'Pacotes Especiais'],
        'data': [pacotes_comuns, pacotes_especiais]
    }

@main_bp.route('/api/general-report/export')
@login_required
def export_general_report():
    """Exportar relatório geral para Excel"""
    try:
        # Obter filtros da query string
        filters = {
            'start_date': request.args.get('start_date'),
            'end_date': request.args.get('end_date'),
            'empresa': request.args.get('empresa'),
            'especialidade': request.args.get('especialidade'),
            'medico': request.args.get('medico'),
            'regiao': request.args.get('regiao'),
            'carteira': request.args.get('carteira')
        }
        
        # Remover filtros vazios
        filters = {k: v for k, v in filters.items() if v}
        
        # Usar ReportGenerator para exportar dados filtrados
        completed_sessions = AnalysisSession.query.filter_by(
            user_id=current_user.id, status='completed'
        ).order_by(AnalysisSession.created_at.desc()).all()
        
        if not completed_sessions:
            processor = SAVIDataProcessor('instance/savi_assistant.db')
        else:
            latest_session = completed_sessions[0]
            processor = SAVIDataProcessor(latest_session.db_file_path, latest_session.excel_file_path)
        
        report_generator = ReportGenerator(processor)
        
        # Aplicar filtros e gerar relatório
        df_filtered = processor.load_data_from_sqlite()
        
        # Aplicar filtros (mesmo código da função anterior)
        # ... código de filtros ...
        
        # Por enquanto, retornar erro indicando funcionalidade em desenvolvimento
        return jsonify({'error': 'Funcionalidade de exportação em desenvolvimento'}), 501
        
    except Exception as e:
        logging.error(f"Erro ao exportar relatório geral: {e}")
        return jsonify({'error': str(e)}), 500

@main_bp.route('/cleanup')
@login_required
def cleanup():
    """Endpoint para limpeza de arquivos (apenas admin)"""
    if current_user.role != 'admin':
        flash('Acesso negado.', 'error')
        return redirect(url_for('main.dashboard'))
    
    try:
        cleanup_old_files()
        flash('Limpeza de arquivos realizada com sucesso.', 'success')
    except Exception as e:
        flash(f'Erro na limpeza: {str(e)}', 'error')
    
    return redirect(url_for('main.dashboard'))

@main_bp.route('/relatorio-divinopolis/<int:session_id>')
@login_required
def relatorio_divinopolis(session_id):
    """Gera relatório específico de Divinópolis cruzando dados Excel x Banco"""
    try:
        session = AnalysisSession.query.get_or_404(session_id)
        
        # Verificar acesso
        if session.user_id != current_user.id and current_user.role != 'admin':
            flash('Acesso negado.', 'error')
            return redirect(url_for('main.dashboard'))
        
        # Verificar se tem arquivo Excel
        if not session.excel_file_path or not os.path.exists(session.excel_file_path):
            flash('Arquivo Excel de Divinópolis não encontrado para esta sessão.', 'error')
            return redirect(url_for('main.analysis', session_id=session_id))
        
        # Gerar relatório usando o módulo específico
        from divinopolis_report import DivinopolisReportGenerator
        
        report_generator = DivinopolisReportGenerator(
            session.db_file_path, 
            session.excel_file_path
        )
        
        report_data = report_generator.generate_report()
        
        if report_data['status'] == 'error':
            flash(f'Erro ao gerar relatório: {report_data["message"]}', 'error')
            return redirect(url_for('main.analysis', session_id=session_id))
        
        return render_template('relatorio_divinopolis.html', 
                             report=report_data, 
                             session=session)
        
    except Exception as e:
        logging.error(f"Erro ao gerar relatório de Divinópolis: {e}")
        flash(f'Erro interno: {str(e)}', 'error')
        return redirect(url_for('main.dashboard'))

@main_bp.route('/sessions')
@login_required
def sessions():
    """Lista todas as sessões do usuário"""
    if current_user.role == 'admin':
        all_sessions = AnalysisSession.query.order_by(AnalysisSession.created_at.desc()).all()
    else:
        all_sessions = AnalysisSession.query.filter_by(user_id=current_user.id)\
                                           .order_by(AnalysisSession.created_at.desc()).all()
    
    return render_template('sessions.html', sessions=all_sessions, format_currency=format_currency)
