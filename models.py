from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from app import db

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='operador')  # admin, operador
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<User {self.username}>'

class AnalysisSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    database_filename = db.Column(db.String(255), nullable=False)
    excel_filename = db.Column(db.String(255))
    db_file_path = db.Column(db.String(500))  # Path completo do arquivo DB carregado
    excel_file_path = db.Column(db.String(500))  # Path completo do arquivo Excel carregado
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default='processing')  # processing, completed, error
    total_records = db.Column(db.Integer)
    total_faturado = db.Column(db.Float)
    total_pacotes = db.Column(db.Integer)
    inconsistencias = db.Column(db.Integer)
    
    user = db.relationship('User', backref=db.backref('analysis_sessions', lazy=True))
    
    def __repr__(self):
        return f'<AnalysisSession {self.id}>'

class ProcessedData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('analysis_session.id'), nullable=False)
    empresa = db.Column(db.String(255))
    procedimento_nome = db.Column(db.String(255))
    procedimento_codigo = db.Column(db.String(50))
    medico_nome = db.Column(db.String(255))
    usuario_nome = db.Column(db.String(255))
    usuario_codigo = db.Column(db.String(50))
    valor_original = db.Column(db.Float)
    valor_final = db.Column(db.Float)
    data_execucao = db.Column(db.Date)
    is_pacote = db.Column(db.Boolean, default=False)
    tipo_pacote = db.Column(db.String(50))  # comum, especial
    has_inconsistencia = db.Column(db.Boolean, default=False)
    inconsistencia_descricao = db.Column(db.Text)
    
    session = db.relationship('AnalysisSession', backref=db.backref('processed_data', lazy=True))
    
    def __repr__(self):
        return f'<ProcessedData {self.id}>'

class Producao(db.Model):
    """Modelo para os dados reais do sistema SAVI - representa a tabela de produção existente"""
    __tablename__ = 'producao'
    
    # Não definimos id como primary key pois os dados existem e podem não ter uma coluna id
    # Utilizamos row_id interno do SQLite
    rowid = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    empresa = db.Column(db.Text)
    servico = db.Column(db.Text)
    rede = db.Column(db.Text)
    data_execucao = db.Column(db.Text)  # Mantemos como TEXT conforme o schema original
    usuario_codigo = db.Column(db.Text)
    usuario_nome = db.Column(db.Text)
    medico_codigo = db.Column(db.Text)
    medico_nome = db.Column(db.Text)
    procedimento_codigo = db.Column(db.Text)
    procedimento_nome = db.Column(db.Text)
    urgencia = db.Column(db.Text)
    qtde_autorizada = db.Column(db.Integer)
    qtde_realizada = db.Column(db.Integer)
    data_autorizacao = db.Column(db.Text)
    numero_guia = db.Column(db.Text)
    senha = db.Column(db.Text)
    
    def __repr__(self):
        return f'<Producao {self.usuario_nome} - {self.procedimento_nome}>'
    
    def to_dict(self):
        """Converte o registro para dicionário para facilitar análise"""
        return {
            'empresa': self.empresa,
            'servico': self.servico,
            'rede': self.rede,
            'data_execucao': self.data_execucao,
            'usuario_codigo': self.usuario_codigo,
            'usuario_nome': self.usuario_nome,
            'medico_codigo': self.medico_codigo,
            'medico_nome': self.medico_nome,
            'procedimento_codigo': self.procedimento_codigo,
            'procedimento_nome': self.procedimento_nome,
            'urgencia': self.urgencia,
            'qtde_autorizada': self.qtde_autorizada,
            'qtde_realizada': self.qtde_realizada,
            'data_autorizacao': self.data_autorizacao,
            'numero_guia': self.numero_guia,
            'senha': self.senha
        }
