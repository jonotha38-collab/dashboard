"""MVP local de governanca LGPD. Execute: streamlit run app_lgpd_geedu.py"""
import sqlite3
from datetime import date, timedelta
from pathlib import Path
import pandas as pd
import streamlit as st

DB = Path(__file__).with_name('lgpd_mvp.sqlite3')
STATUSES = ['A fazer', 'Em andamento', 'Concluído']
SEVERITIES = ['Baixo', 'Médio', 'Alto', 'Crítico']

st.set_page_config(page_title='GEEDU | Gestão LGPD', page_icon='🛡️', layout='wide')


def connect():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys = ON')
    return con


def init_db():
    with connect() as con:
        con.executescript('''
        CREATE TABLE IF NOT EXISTS setores (
          id INTEGER PRIMARY KEY, nome TEXT NOT NULL UNIQUE, responsavel TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS fluxos_ropa (
          id INTEGER PRIMARY KEY, codigo TEXT NOT NULL UNIQUE, nome TEXT NOT NULL,
          setor_id INTEGER NOT NULL REFERENCES setores(id), finalidade TEXT NOT NULL,
          titulares TEXT NOT NULL DEFAULT '', dados TEXT NOT NULL DEFAULT '',
          base_legal TEXT NOT NULL DEFAULT 'A validar',
          ultima_revisao TEXT NOT NULL, proxima_revisao TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'Ativo' CHECK(status IN ('Ativo','Inativo'))
        );
        CREATE TABLE IF NOT EXISTS riscos_acoes (
          id INTEGER PRIMARY KEY, fluxo_id INTEGER NOT NULL REFERENCES fluxos_ropa(id),
          risco TEXT NOT NULL, criticidade TEXT NOT NULL,
          acao TEXT NOT NULL, responsavel TEXT NOT NULL, prazo TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'A fazer', risco_residual TEXT NOT NULL DEFAULT 'A avaliar',
          evidencia TEXT NOT NULL DEFAULT '', validado INTEGER NOT NULL DEFAULT 0,
          CHECK(status IN ('A fazer','Em andamento','Concluído'))
        );
        CREATE TABLE IF NOT EXISTS requisicoes_titulares (
          id INTEGER PRIMARY KEY, protocolo TEXT NOT NULL UNIQUE,
          fluxo_id INTEGER REFERENCES fluxos_ropa(id), tipo TEXT NOT NULL,
          referencia_titular TEXT NOT NULL, data_recebimento TEXT NOT NULL,
          prazo_operacional TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Aberta',
          resposta TEXT NOT NULL DEFAULT '',
          CHECK(status IN ('Aberta','Em análise','Respondida'))
        );
        ''')
        if con.execute('SELECT COUNT(*) FROM setores').fetchone()[0] == 0:
            con.executemany('INSERT INTO setores(nome,responsavel) VALUES(?,?)',
                            [('Recursos Humanos','Gestor de RH'),('Acadêmico','Gestor Acadêmico'),('Financeiro','Gestor Financeiro')])
            today = date.today()
            con.executemany('''INSERT INTO fluxos_ropa(codigo,nome,setor_id,finalidade,titulares,dados,base_legal,ultima_revisao,proxima_revisao)
                            VALUES(?,?,?,?,?,?,?,?,?)''', [
                ('EX-001','Gestão de currículos',1,'Recrutamento e seleção','Candidatos','Nome, e-mail, experiência','Art. 7º, V (avaliar)',str(today-timedelta(days=140)),str(today+timedelta(days=40))),
                ('EX-002','Matrícula escolar',2,'Formalização e gestão de matrículas','Alunos e responsáveis','Identificação, turma, contatos','Art. 7º, V; art. 14 (avaliar)',str(today-timedelta(days=200)),str(today-timedelta(days=20))),
                ('EX-003','Cobrança de mensalidades',3,'Gestão financeira contratual','Responsáveis financeiros','CPF, cobrança, pagamentos','Art. 7º, V (avaliar)',str(today-timedelta(days=90)),str(today+timedelta(days=90)))])
            con.executemany('''INSERT INTO riscos_acoes(fluxo_id,risco,criticidade,acao,responsavel,prazo,status,risco_residual)
                            VALUES(?,?,?,?,?,?,?,?)''', [
                (2,'Exposição de dados de alunos','Crítico','Revisar perfis de acesso e testar segregação entre escolas','TI',str(today-timedelta(days=4)),'Em andamento','Alto (projetado)'),
                (1,'Retenção indefinida de currículos','Alto','Definir prazo e rotina de descarte verificável','RH',str(today+timedelta(days=20)),'A fazer','Médio (projetado)'),
                (3,'Exportação financeira sem trilha','Alto','Registrar downloads e restringir exportação por perfil','TI',str(today+timedelta(days=12)),'A fazer','Médio (projetado)')])


def rows(sql, params=()):
    with connect() as con:
        return [dict(x) for x in con.execute(sql, params).fetchall()]


def execute(sql, params):
    with connect() as con:
        con.execute(sql, params)
    st.success('Registro salvo.')


def options(sql):
    return {f"{r['id']} · {r['nome']}": r['id'] for r in rows(sql)}


def show_table(data):
    if data:
        st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
    else:
        st.info('Nenhum registro encontrado.')

init_db()
st.sidebar.title('🛡️ GEEDU | LGPD')
page = st.sidebar.radio('Navegação', ['Dashboard','ROPA / Fluxos','Riscos e Ações','Titulares'])
st.sidebar.caption('Protótipo local · dados fictícios · sem autenticação')
today = date.today()

if page == 'Dashboard':
    st.title('Painel de governança LGPD')
    fluxos = rows('SELECT * FROM fluxos_ropa')
    riscos = rows('SELECT * FROM riscos_acoes')
    requests = rows('SELECT * FROM requisicoes_titulares')
    overdue = [r for r in riscos if r['status'] != 'Concluído' and r['prazo'] < str(today)]
    critical = [r for r in riscos if r['criticidade'] == 'Crítico' and (r['status'] != 'Concluído' or not r['validado'])]
    cols = st.columns(4)
    for col, label, value in zip(cols, ['Fluxos ativos','Riscos críticos pendentes','Tarefas atrasadas','Revisões vencidas'],
                                  [sum(f['status']=='Ativo' for f in fluxos),len(critical),len(overdue),sum(f['proxima_revisao']<str(today) and f['status']=='Ativo' for f in fluxos)]):
        col.metric(label,value)
    st.subheader('Fluxos por setor')
    sector_counts = rows('''SELECT s.nome AS setor,COUNT(f.id) AS quantidade FROM setores s LEFT JOIN fluxos_ropa f ON f.setor_id=s.id AND f.status='Ativo' GROUP BY s.id''')
    st.bar_chart(pd.DataFrame(sector_counts).set_index('setor'))
    st.subheader('Ações que exigem atenção')
    show_table([{'Risco':r['risco'],'Criticidade':r['criticidade'],'Prazo':r['prazo'],'Responsável':r['responsavel'],'Status':r['status']} for r in riscos if r in overdue or r in critical])
    st.caption('Os indicadores representam o estado dos registros, não um percentual jurídico de conformidade.')

elif page == 'ROPA / Fluxos':
    st.title('ROPA e revisão de fluxos')
    sector_map = options('SELECT id,nome FROM setores ORDER BY nome')
    with st.expander('Cadastrar fluxo', expanded=False):
        with st.form('flow_add'):
            code=st.text_input('Código ROPA (único)')
            name=st.text_input('Nome do fluxo')
            sector=st.selectbox('Setor',list(sector_map))
            purpose=st.text_area('Finalidade')
            subjects=st.text_input('Titulares')
            data=st.text_area('Dados tratados')
            basis=st.text_input('Base legal / validação',value='A validar')
            review=st.date_input('Próxima revisão',value=today+timedelta(days=180))
            submitted=st.form_submit_button('Cadastrar')
            if submitted:
                if not code.strip() or not name.strip() or not purpose.strip():
                    st.error('Preencha código, nome e finalidade.')
                else:
                    try:
                        execute('''INSERT INTO fluxos_ropa(codigo,nome,setor_id,finalidade,titulares,dados,base_legal,ultima_revisao,proxima_revisao) VALUES(?,?,?,?,?,?,?,?,?)''',
                                (code.strip(),name.strip(),sector_map[sector],purpose,subjects,data,basis,str(today),str(review)))
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error('Código ROPA já utilizado.')
    flow_map=options('SELECT id,nome FROM fluxos_ropa ORDER BY id')
    if flow_map:
        selected=st.selectbox('Fluxo para revisão',list(flow_map))
        flow=rows('SELECT * FROM fluxos_ropa WHERE id=?',(flow_map[selected],))[0]
        st.write(f"**Código:** {flow['codigo']} · **Finalidade:** {flow['finalidade']}")
        st.write(f"**Titulares:** {flow['titulares']} · **Dados:** {flow['dados']}")
        st.write(f"**Base legal:** {flow['base_legal']}")
        with st.form('flow_review'):
            next_review=st.date_input('Próxima revisão',value=date.fromisoformat(flow['proxima_revisao']))
            status=st.selectbox('Situação', ['Ativo','Inativo'],index=['Ativo','Inativo'].index(flow['status']))
            if st.form_submit_button('Registrar revisão'):
                execute('UPDATE fluxos_ropa SET ultima_revisao=?,proxima_revisao=?,status=? WHERE id=?',
                        (str(today),str(next_review),status,flow['id']))
                st.rerun()
    st.subheader('Inventário')
    show_table(rows('''SELECT f.codigo,f.nome,s.nome AS setor,f.base_legal,f.proxima_revisao,f.status FROM fluxos_ropa f JOIN setores s ON s.id=f.setor_id ORDER BY f.id'''))

elif page == 'Riscos e Ações':
    st.title('Gestão de riscos e plano de ação')
    flow_map=options('SELECT id,nome FROM fluxos_ropa ORDER BY id')
    with st.expander('Cadastrar ação mitigatória'):
        with st.form('risk_add'):
            flow=st.selectbox('Fluxo relacionado',list(flow_map))
            risk=st.text_input('Descrição do risco')
            severity=st.selectbox('Criticidade',SEVERITIES,index=2)
            action=st.text_area('Medida de tratamento')
            owner=st.text_input('Responsável')
            deadline=st.date_input('Prazo',value=today+timedelta(days=30))
            if st.form_submit_button('Cadastrar ação'):
                if risk.strip() and action.strip() and owner.strip():
                    execute('''INSERT INTO riscos_acoes(fluxo_id,risco,criticidade,acao,responsavel,prazo) VALUES(?,?,?,?,?,?)''',
                            (flow_map[flow],risk,severity,action,owner,str(deadline)))
                    st.rerun()
                else:
                    st.error('Preencha risco, medida e responsável.')
    severity_filter=st.selectbox('Filtrar criticidade',['Todas']+SEVERITIES)
    all_risks=rows('''SELECT a.*,f.codigo FROM riscos_acoes a JOIN fluxos_ropa f ON f.id=a.fluxo_id ORDER BY a.prazo''')
    filtered=[r for r in all_risks if severity_filter=='Todas' or r['criticidade']==severity_filter]
    show_table([{'ID':r['id'],'ROPA':r['codigo'],'Risco':r['risco'],'Criticidade':r['criticidade'],'Ação':r['acao'],'Responsável':r['responsavel'],'Prazo':r['prazo'],'Status':r['status'],'Residual':r['risco_residual'],'Validado':bool(r['validado'])} for r in filtered])
    if all_risks:
        risk_map={f"{r['id']} · {r['risco']}":r for r in all_risks}
        selected=st.selectbox('Atualizar ação',list(risk_map))
        current=risk_map[selected]
        with st.form('risk_edit'):
            new_status=st.selectbox('Status',STATUSES,index=STATUSES.index(current['status']))
            residual=st.text_input('Risco residual (projetado ou validado)',value=current['risco_residual'])
            evidence=st.text_area('Referência da evidência (sem dados pessoais)',value=current['evidencia'])
            validated=st.checkbox('Controle testado e validado pelo responsável',value=bool(current['validado']))
            if st.form_submit_button('Salvar acompanhamento'):
                if validated and (new_status!='Concluído' or not evidence.strip()):
                    st.error('Para validar, conclua a ação e registre a referência da evidência.')
                else:
                    execute('UPDATE riscos_acoes SET status=?,risco_residual=?,evidencia=?,validado=? WHERE id=?',
                            (new_status,residual,evidence,int(validated),current['id']))
                    st.rerun()

elif page == 'Titulares':
    st.title('Atendimento a titulares · simulado')
    st.warning('Não insira dados pessoais reais. Este MVP não possui autenticação, criptografia ou canal seguro de atendimento.')
    st.caption('15 dias = referência operacional configurada neste protótipo. Não é prazo universal para todos os direitos da LGPD.')
    flow_map=options('SELECT id,nome FROM fluxos_ropa ORDER BY id')
    with st.form('request_add'):
        kind=st.selectbox('Tipo de solicitação',['Acesso','Confirmação','Correção','Exclusão','Oposição','Outro'])
        ref=st.text_input('Referência pseudonimizada do titular (não inserir CPF/e-mail)')
        related=st.selectbox('Fluxo relacionado', ['Não identificado']+list(flow_map))
        received=st.date_input('Data de recebimento',value=today)
        days=st.number_input('Prazo operacional (dias corridos)',min_value=1,max_value=365,value=15)
        if st.form_submit_button('Registrar protocolo'):
            if not ref.strip():
                st.error('Informe uma referência pseudonimizada.')
            else:
                with connect() as con:
                    con.execute('''INSERT INTO requisicoes_titulares(protocolo,fluxo_id,tipo,referencia_titular,data_recebimento,prazo_operacional) VALUES(?,?,?,?,?,?)''',
                                (f"SOL-{date.today():%Y%m%d}-{con.execute('SELECT COALESCE(MAX(id),0)+1 FROM requisicoes_titulares').fetchone()[0]:04d}",flow_map.get(related),kind,ref,str(received),str(received+timedelta(days=int(days)))))
                st.success('Protocolo registrado.')
                st.rerun()
    requests=rows('SELECT * FROM requisicoes_titulares ORDER BY id DESC')
    show_table([{'Protocolo':r['protocolo'],'Tipo':r['tipo'],'Recebimento':r['data_recebimento'],'Prazo operacional':r['prazo_operacional'],'Dias restantes':(date.fromisoformat(r['prazo_operacional'])-today).days if r['status']!='Respondida' else None,'Status':r['status']} for r in requests])
    if requests:
        req_map={r['protocolo']:r for r in requests}
        chosen=st.selectbox('Atualizar solicitação',list(req_map))
        current=req_map[chosen]
        with st.form('request_edit'):
            status=st.selectbox('Situação',['Aberta','Em análise','Respondida'],index=['Aberta','Em análise','Respondida'].index(current['status']))
            answer=st.text_area('Registro resumido da resposta (sem dados pessoais)',value=current['resposta'])
            if st.form_submit_button('Salvar'):
                execute('UPDATE requisicoes_titulares SET status=?,resposta=? WHERE id=?',(status,answer,current['id']))
                st.rerun()
