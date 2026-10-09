import sqlite3
from pathlib import Path
import pandas as pd
import streamlit as st

# Configuração da página para um visual profissional
st.set_page_config(page_title='Dashboard Executivo | LGPD', page_icon='📊', layout='wide')

# Caminho do banco de dados gerado pelo app principal
DB = Path(__file__).parent / 'lgpd_mvp.sqlite3'

def get_data(query):
    """Função segura para ler os dados do banco SQLite"""
    try:
        if not DB.exists():
            return pd.DataFrame()
        with sqlite3.connect(DB) as con:
            return pd.read_sql_query(query, con)
    except Exception:
        return pd.DataFrame()

# Estilo customizado (CSS) para melhorar a aparência
st.markdown("""
    <style>
    .metric-card {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #0056b3;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
    </style>
""", unsafe_allow_html=True)

st.title('📊 Dashboard Executivo de Conformidade LGPD')
st.markdown('Resumo analítico dos indicadores de governança e adequação de dados.')
st.markdown('---')

# Carregar Dados
df_fluxos = get_data('SELECT * FROM fluxos_ropa')
df_riscos = get_data('SELECT * FROM riscos_acoes')
df_reqs = get_data('SELECT * FROM requisicoes_titulares')

if df_fluxos.empty and df_riscos.empty:
    st.warning('⚠️ Banco de dados não encontrado ou vazio. Certifique-se de ter executado o aplicativo principal (`app_lgpd_geedu.py`) pelo menos uma vez para gerar os dados iniciais.')
    st.stop()

# --- CÁLCULOS DE PORCENTAGENS E MÉTRICAS ---

# 1. ROPA (Fluxos)
total_fluxos = len(df_fluxos)
fluxos_ativos = len(df_fluxos[df_fluxos['status'] == 'Ativo']) if not df_fluxos.empty else 0
pct_fluxos_ativos = (fluxos_ativos / total_fluxos * 100) if total_fluxos > 0 else 0

# 2. Riscos e Planos de Ação
total_riscos = len(df_riscos)
riscos_concluidos = len(df_riscos[df_riscos['status'] == 'Concluído']) if not df_riscos.empty else 0
pct_riscos_concluidos = (riscos_concluidos / total_riscos * 100) if total_riscos > 0 else 0
riscos_criticos = len(df_riscos[df_riscos['criticidade'] == 'Crítico']) if not df_riscos.empty else 0
riscos_criticos_pendentes = len(df_riscos[(df_riscos['criticidade'] == 'Crítico') & (df_riscos['status'] != 'Concluído')]) if not df_riscos.empty else 0

# 3. Requisições de Titulares
total_reqs = len(df_reqs)
reqs_respondidas = len(df_reqs[df_reqs['status'] == 'Respondida']) if not df_reqs.empty else 0
pct_reqs_respondidas = (reqs_respondidas / total_reqs * 100) if total_reqs > 0 else 0


# --- LAYOUT DO DASHBOARD ---

st.subheader('📈 Visão Geral (KPIs)')

# Linha de Métricas Principais
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(label="Fluxos Mapeados (ROPA)", value=total_fluxos)
    st.progress(pct_fluxos_ativos / 100, text=f"Ativos: {pct_fluxos_ativos:.1f}%")

with col2:
    st.metric(label="Ações de Risco Concluídas", value=f"{riscos_concluidos} de {total_riscos}")
    st.progress(pct_riscos_concluidos / 100, text=f"Mitigados: {pct_riscos_concluidos:.1f}%")

with col3:
    st.metric(label="Riscos Críticos Pendentes", value=riscos_criticos_pendentes, delta=f"De {riscos_criticos} Críticos Totais", delta_color="inverse")
    pct_criticos = ((riscos_criticos - riscos_criticos_pendentes) / riscos_criticos * 100) if riscos_criticos > 0 else 100
    st.progress(pct_criticos / 100, text=f"Tratados: {pct_criticos:.1f}%")

with col4:
    st.metric(label="Requisições Atendidas", value=f"{reqs_respondidas} de {total_reqs}")
    if total_reqs > 0:
        st.progress(pct_reqs_respondidas / 100, text=f"Respondidas: {pct_reqs_respondidas:.1f}%")
    else:
        st.info("Nenhuma requisição recebida")

st.markdown('<br><br>', unsafe_allow_html=True)

# Linha de Gráficos Analíticos
st.subheader('📊 Detalhamento Analítico')
colA, colB = st.columns(2)

with colA:
    st.markdown('**Distribuição de Planos de Ação por Status**')
    if not df_riscos.empty:
        status_count = df_riscos['status'].value_counts()
        # Gráfico de barras simples e elegante do Streamlit
        st.bar_chart(status_count, color="#ff4b4b")
    else:
        st.write("Sem dados.")

with colB:
    st.markdown('**Volume de Fluxos por Situação (Ativo vs Inativo)**')
    if not df_fluxos.empty:
        fluxo_status_count = df_fluxos['status'].value_counts()
        st.bar_chart(fluxo_status_count, color="#0068c9")
    else:
        st.write("Sem dados.")

st.markdown('---')
st.caption('Dashboard Executivo LGPD · Criado com base nos dados do aplicativo original.')
