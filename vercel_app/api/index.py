from flask import Flask
import sqlite3
import pandas as pd
from datetime import datetime
import os

app = Flask(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'lgpd_mvp.sqlite3')

def get_data(query):
    try:
        if not os.path.exists(DB_PATH):
            return pd.DataFrame()
        with sqlite3.connect(DB_PATH) as con:
            return pd.read_sql_query(query, con)
    except Exception as e:
        print(f"Erro: {e}")
        return pd.DataFrame()

@app.route('/')
def home():
    df_fluxos = get_data('SELECT * FROM fluxos_ropa')
    df_riscos = get_data('SELECT * FROM riscos_acoes')
    df_reqs = get_data('SELECT * FROM requisicoes_titulares')
    
    # Consultas detalhadas
    df_setores = get_data('''SELECT s.nome, COUNT(f.id) as qtd 
                             FROM setores s 
                             LEFT JOIN fluxos_ropa f ON f.setor_id = s.id AND f.status='Ativo' 
                             GROUP BY s.id ORDER BY qtd DESC''')
    
    df_riscos_pend = get_data('''SELECT f.codigo, a.risco, a.criticidade, a.responsavel, a.prazo 
                                 FROM riscos_acoes a 
                                 JOIN fluxos_ropa f ON f.id = a.fluxo_id 
                                 WHERE a.status != 'Concluído' 
                                 ORDER BY a.prazo ASC''')
                                 
    df_reqs_pend = get_data('''SELECT protocolo, tipo, data_recebimento, prazo_operacional 
                               FROM requisicoes_titulares 
                               WHERE status != 'Respondida' 
                               ORDER BY prazo_operacional ASC''')

    if df_fluxos.empty and df_riscos.empty:
        return "<h1>⚠️ Banco de Dados vazio ou não encontrado.</h1>"

    # KPIs Básicos
    total_fluxos = len(df_fluxos)
    fluxos_ativos = len(df_fluxos[df_fluxos['status'] == 'Ativo']) if not df_fluxos.empty else 0
    pct_fluxos = (fluxos_ativos / total_fluxos * 100) if total_fluxos > 0 else 0

    total_riscos = len(df_riscos)
    riscos_concluidos = len(df_riscos[df_riscos['status'] == 'Concluído']) if not df_riscos.empty else 0
    pct_riscos = (riscos_concluidos / total_riscos * 100) if total_riscos > 0 else 0

    riscos_criticos = len(df_riscos[df_riscos['criticidade'] == 'Crítico']) if not df_riscos.empty else 0
    riscos_criticos_pend = len(df_riscos[(df_riscos['criticidade'] == 'Crítico') & (df_riscos['status'] != 'Concluído')]) if not df_riscos.empty else 0
    pct_criticos = ((riscos_criticos - riscos_criticos_pend) / riscos_criticos * 100) if riscos_criticos > 0 else 100

    total_reqs = len(df_reqs)
    reqs_resp = len(df_reqs[df_reqs['status'] == 'Respondida']) if not df_reqs.empty else 0
    pct_reqs = (reqs_resp / total_reqs * 100) if total_reqs > 0 else 0

    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    # Renderização de Tabelas
    riscos_html = ""
    if df_riscos_pend.empty:
        riscos_html = "<p style='color:#31a24c;'>Nenhum risco pendente! 🎉</p>"
    else:
        riscos_html += "<table class='data-table'><tr><th>Fluxo</th><th>Risco</th><th>Crit.</th><th>Responsável</th><th>Prazo</th></tr>"
        for _, row in df_riscos_pend.iterrows():
            crit_class = "crit-critico" if row['criticidade'] == 'Crítico' else "crit-alto" if row['criticidade'] == 'Alto' else "crit-medio"
            riscos_html += f"<tr><td>{row['codigo']}</td><td>{row['risco']}</td><td><span class='badge {crit_class}'>{row['criticidade']}</span></td><td>{row['responsavel']}</td><td>{row['prazo']}</td></tr>"
        riscos_html += "</table>"

    reqs_html = ""
    if df_reqs_pend.empty:
        reqs_html = "<p style='color:#31a24c;'>Nenhuma requisição de titular em aberto! 🎉</p>"
    else:
        reqs_html += "<table class='data-table'><tr><th>Protocolo</th><th>Tipo</th><th>Recebido</th><th>Prazo</th></tr>"
        for _, row in df_reqs_pend.iterrows():
            reqs_html += f"<tr><td>{row['protocolo']}</td><td>{row['tipo']}</td><td>{row['data_recebimento']}</td><td><strong style='color:#e52a2a;'>{row['prazo_operacional']}</strong></td></tr>"
        reqs_html += "</table>"

    setores_html = ""
    if not df_setores.empty:
        setores_html += "<ul class='sector-list'>"
        for _, row in df_setores.iterrows():
            setores_html += f"<li><strong>{row['nome']}</strong>: {row['qtd']} fluxo(s) ativo(s)</li>"
        setores_html += "</ul>"

    # HTML
    html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard Detalhado LGPD</title>
    <style>
        body {{ font-family: 'Segoe UI', Roboto, Helvetica, sans-serif; background-color: #f0f2f5; color: #1c1e21; margin: 0; padding: 40px 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ background: #fff; padding: 30px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 25px; display: flex; justify-content: space-between; align-items: center; border-left: 5px solid #1877f2; }}
        h1 {{ margin: 0; color: #1877f2; font-size: 26px; }}
        .timestamp {{ color: #65676b; font-size: 14px; }}
        
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 25px; margin-bottom: 25px; }}
        .card {{ background: #fff; padding: 20px; border-radius: 8px; border-top: 4px solid #1877f2; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }}
        .card.success {{ border-top-color: #31a24c; }}
        .card.warning {{ border-top-color: #e52a2a; }}
        .card.neutral {{ border-top-color: #f6b024; }}
        .card-title {{ color: #65676b; font-size: 14px; font-weight: 600; text-transform: uppercase; margin-bottom: 10px; }}
        .card-value {{ font-size: 32px; font-weight: bold; color: #1c1e21; margin-bottom: 5px; }}
        .card-subtext {{ font-size: 13px; color: #65676b; margin-bottom: 15px; }}
        
        .progress-bg {{ background-color: #e4e6eb; height: 8px; border-radius: 4px; width: 100%; overflow: hidden; }}
        .progress-fill {{ height: 100%; background-color: #1877f2; border-radius: 4px; }}
        .card.success .progress-fill {{ background-color: #31a24c; }}
        .card.warning .progress-fill {{ background-color: #e52a2a; }}
        .card.neutral .progress-fill {{ background-color: #f6b024; }}
        
        .details-grid {{ display: grid; grid-template-columns: 2fr 1fr; gap: 25px; }}
        .details-card {{ background: #fff; padding: 25px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }}
        .details-card h2 {{ margin-top: 0; font-size: 18px; color: #1c1e21; border-bottom: 2px solid #f0f2f5; padding-bottom: 10px; margin-bottom: 20px; display:flex; align-items:center; gap: 10px; }}
        
        .data-table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
        .data-table th, .data-table td {{ border-bottom: 1px solid #e4e6eb; padding: 12px; text-align: left; }}
        .data-table th {{ background-color: #f8f9fa; color: #65676b; font-weight: 600; text-transform: uppercase; font-size: 12px; }}
        .data-table tr:hover {{ background-color: #f0f2f5; }}
        
        .badge {{ padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: bold; color: white; display: inline-block; }}
        .crit-critico {{ background-color: #e52a2a; }}
        .crit-alto {{ background-color: #f6b024; }}
        .crit-medio {{ background-color: #1877f2; }}
        .crit-baixo {{ background-color: #31a24c; }}
        
        .sector-list {{ list-style: none; padding: 0; margin: 0; }}
        .sector-list li {{ padding: 12px; border-bottom: 1px solid #e4e6eb; display: flex; justify-content: space-between; }}
        .sector-list li:last-child {{ border-bottom: none; }}
        
        .footer {{ margin-top: 40px; text-align: center; color: #8c939d; font-size: 13px; padding-bottom: 20px; }}
        
        @media (max-width: 900px) {{ .details-grid {{ grid-template-columns: 1fr; }} }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>🛡️ Painel Executivo e Operacional LGPD</h1>
                <div class="timestamp">Status consolidado dos controles de privacidade</div>
            </div>
            <div class="timestamp">Atualizado: <strong>{agora}</strong></div>
        </div>
        
        <!-- KPIs Principais -->
        <div class="grid">
            <div class="card">
                <div class="card-title">ROPA (Fluxos Ativos)</div>
                <div class="card-value">{fluxos_ativos} <span style="font-size:16px; color:#65676b; font-weight:normal;">/ {total_fluxos}</span></div>
                <div class="card-subtext">Base de operações mapeada</div>
                <div class="progress-bg"><div class="progress-fill" style="width: {pct_fluxos}%;"></div></div>
            </div>
            <div class="card success">
                <div class="card-title">Riscos Mitigados</div>
                <div class="card-value">{riscos_concluidos} <span style="font-size:16px; color:#65676b; font-weight:normal;">/ {total_riscos}</span></div>
                <div class="card-subtext">Planos de ação concluídos</div>
                <div class="progress-bg"><div class="progress-fill" style="width: {pct_riscos}%;"></div></div>
            </div>
            <div class="card warning">
                <div class="card-title">Riscos Críticos Pendentes</div>
                <div class="card-value">{riscos_criticos_pend}</div>
                <div class="card-subtext">Exigem atenção imediata</div>
                <div class="progress-bg"><div class="progress-fill" style="width: {pct_criticos}%;"></div></div>
            </div>
            <div class="card neutral">
                <div class="card-title">Requisições Atendidas</div>
                <div class="card-value">{reqs_resp} <span style="font-size:16px; color:#65676b; font-weight:normal;">/ {total_reqs}</span></div>
                <div class="card-subtext">Solicitações de titulares encerradas</div>
                <div class="progress-bg"><div class="progress-fill" style="width: {pct_reqs}%;"></div></div>
            </div>
        </div>
        
        <!-- Detalhamentos -->
        <div class="details-grid">
            <!-- Esquerda: Tabelas de Ações e Requisições -->
            <div>
                <div class="details-card" style="margin-bottom: 25px;">
                    <h2>⚠️ Planos de Ação Pendentes</h2>
                    <p style="font-size:13px; color:#65676b; margin-top:-10px;">Riscos ainda não concluídos ordenados pelo prazo.</p>
                    {riscos_html}
                </div>
                
                <div class="details-card">
                    <h2>⏳ Requisições de Titulares em Aberto</h2>
                    <p style="font-size:13px; color:#65676b; margin-top:-10px;">Solicitações dentro do prazo operacional.</p>
                    {reqs_html}
                </div>
            </div>
            
            <!-- Direita: Setores -->
            <div>
                <div class="details-card">
                    <h2>🏢 Mapeamento por Setor</h2>
                    <p style="font-size:13px; color:#65676b; margin-top:-10px;">Volume de fluxos de dados ativos geridos por área.</p>
                    {setores_html}
                </div>
            </div>
        </div>
        
        <div class="footer">
            Relatório Operacional LGPD · Gerado via Serverless API (Vercel)
        </div>
    </div>
</body>
</html>"""
    return html_content
