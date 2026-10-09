from flask import Flask
import sqlite3
import pandas as pd
from datetime import datetime
import os

app = Flask(__name__)

# O Vercel hospeda tudo no diretório raiz, subimos um nível do /api para achar o banco
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'lgpd_mvp.sqlite3')

def get_data(query):
    try:
        if not os.path.exists(DB_PATH):
            return pd.DataFrame()
        with sqlite3.connect(DB_PATH) as con:
            return pd.read_sql_query(query, con)
    except Exception as e:
        print(f"Erro ao ler banco: {e}")
        return pd.DataFrame()

@app.route('/')
def home():
    df_fluxos = get_data('SELECT * FROM fluxos_ropa')
    df_riscos = get_data('SELECT * FROM riscos_acoes')
    df_reqs = get_data('SELECT * FROM requisicoes_titulares')

    # Se o banco não existir ou estiver vazio no Vercel
    if df_fluxos.empty and df_riscos.empty:
        return """<h1>⚠️ Banco de Dados não encontrado</h1>
                  <p>Certifique-se de que o arquivo <b>lgpd_mvp.sqlite3</b> foi enviado para o Vercel junto com o código.</p>"""

    # Cálculos - Fluxos
    total_fluxos = len(df_fluxos)
    fluxos_ativos = len(df_fluxos[df_fluxos['status'] == 'Ativo']) if not df_fluxos.empty else 0
    pct_fluxos = (fluxos_ativos / total_fluxos * 100) if total_fluxos > 0 else 0

    # Cálculos - Riscos
    total_riscos = len(df_riscos)
    riscos_concluidos = len(df_riscos[df_riscos['status'] == 'Concluído']) if not df_riscos.empty else 0
    pct_riscos = (riscos_concluidos / total_riscos * 100) if total_riscos > 0 else 0

    riscos_criticos = len(df_riscos[df_riscos['criticidade'] == 'Crítico']) if not df_riscos.empty else 0
    riscos_criticos_pend = len(df_riscos[(df_riscos['criticidade'] == 'Crítico') & (df_riscos['status'] != 'Concluído')]) if not df_riscos.empty else 0
    pct_criticos = ((riscos_criticos - riscos_criticos_pend) / riscos_criticos * 100) if riscos_criticos > 0 else 100

    # Cálculos - Requisições
    total_reqs = len(df_reqs)
    reqs_resp = len(df_reqs[df_reqs['status'] == 'Respondida']) if not df_reqs.empty else 0
    pct_reqs = (reqs_resp / total_reqs * 100) if total_reqs > 0 else 0

    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    # Template HTML com CSS Integrado
    html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard Executivo LGPD</title>
    <style>
        body {{
            font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background-color: #f0f2f5;
            color: #1c1e21;
            margin: 0;
            padding: 40px 20px;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
            background: #ffffff;
            padding: 30px 40px;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid #e4e6eb;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        h1 {{
            margin: 0;
            color: #1877f2;
            font-size: 24px;
        }}
        .timestamp {{
            color: #65676b;
            font-size: 14px;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 25px;
        }}
        .card {{
            background: #ffffff;
            border: 1px solid #e4e6eb;
            padding: 20px;
            border-radius: 8px;
            border-top: 4px solid #1877f2;
            box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        }}
        .card.success {{ border-top-color: #31a24c; }}
        .card.warning {{ border-top-color: #e52a2a; }}
        .card.neutral {{ border-top-color: #f6b024; }}
        
        .card-title {{
            color: #65676b;
            font-size: 14px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 10px;
        }}
        .card-value {{
            font-size: 32px;
            font-weight: bold;
            color: #1c1e21;
            margin-bottom: 5px;
        }}
        .card-subtext {{
            font-size: 13px;
            color: #65676b;
            margin-bottom: 15px;
        }}
        .progress-bg {{
            background-color: #e4e6eb;
            height: 8px;
            border-radius: 4px;
            width: 100%;
            overflow: hidden;
        }}
        .progress-fill {{
            height: 100%;
            background-color: #1877f2;
            border-radius: 4px;
        }}
        .card.success .progress-fill {{ background-color: #31a24c; }}
        .card.warning .progress-fill {{ background-color: #e52a2a; }}
        .card.neutral .progress-fill {{ background-color: #f6b024; }}
        .footer {{
            margin-top: 40px;
            text-align: center;
            color: #8c939d;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛡️ Resumo Executivo LGPD</h1>
            <div class="timestamp">Acessado em: {agora}</div>
        </div>
        
        <div class="grid">
            <div class="card">
                <div class="card-title">Fluxos Mapeados (ROPA)</div>
                <div class="card-value">{total_fluxos}</div>
                <div class="card-subtext">{pct_fluxos:.1f}% ativos ({fluxos_ativos} de {total_fluxos})</div>
                <div class="progress-bg"><div class="progress-fill" style="width: {pct_fluxos}%;"></div></div>
            </div>

            <div class="card success">
                <div class="card-title">Ações Mitigadas</div>
                <div class="card-value">{riscos_concluidos}/{total_riscos}</div>
                <div class="card-subtext">{pct_riscos:.1f}% dos riscos tratados</div>
                <div class="progress-bg"><div class="progress-fill" style="width: {pct_riscos}%;"></div></div>
            </div>

            <div class="card warning">
                <div class="card-title">Riscos Críticos</div>
                <div class="card-value">{riscos_criticos_pend}</div>
                <div class="card-subtext">{pct_criticos:.1f}% tratados (Restam {riscos_criticos_pend} pendentes)</div>
                <div class="progress-bg"><div class="progress-fill" style="width: {pct_criticos}%;"></div></div>
            </div>

            <div class="card neutral">
                <div class="card-title">Requisições de Titulares</div>
                <div class="card-value">{reqs_resp}/{total_reqs}</div>
                <div class="card-subtext">{pct_reqs:.1f}% respondidas com sucesso</div>
                <div class="progress-bg"><div class="progress-fill" style="width: {pct_reqs}%;"></div></div>
            </div>
        </div>
        
        <div class="footer">
            Relatório gerado dinamicamente via Vercel (Python Serverless)
        </div>
    </div>
</body>
</html>"""
    return html_content

# Vercel precisa exportar a variável 'app'
