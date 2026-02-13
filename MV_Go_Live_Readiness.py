import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from fpdf import FPDF
import io

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Hub de Inteligência: Go-Live", layout="wide", page_icon="🚀")

# --- BANCO DE DADOS (Persistência e Rastreabilidade) ---
def init_db():
    conn = sqlite3.connect('projetos_cloud.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS prontidao 
                 (projeto TEXT, categoria TEXT, item TEXT, status INTEGER, 
                  observacao TEXT, data_atualizacao TEXT, responsavel TEXT)''')
    conn.commit()
    return conn

conn = init_db()

# --- CLASSE E FUNÇÃO PARA PDF ---
class PDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 12)
        self.cell(0, 10, 'Relatorio de Prontidao Go-Live (Readiness Report)', 0, 1, 'C')
        self.ln(5)

def gerar_pdf(df, projeto, percentual):
    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_fill_color(200, 220, 255)
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(0, 10, f"Projeto: {projeto}", 1, 1, 'L', 1)
    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 10, f"Status Global: {percentual:.1f}%", 1, 1, 'L', 1)
    pdf.cell(0, 10, f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 1, 1, 'L', 1)
    pdf.ln(10)
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(90, 8, "Item", 1, 0, 'C')
    pdf.cell(30, 8, "Status", 1, 0, 'C')
    pdf.cell(70, 8, "Observacoes", 1, 1, 'C')
    pdf.set_font("Helvetica", size=8)
    for _, row in df.iterrows():
        status_txt = "CONCLUIDO" if row['status'] == 1 else "PENDENTE"
        curr_x, curr_y = pdf.get_x(), pdf.get_y()
        pdf.multi_cell(90, 8, row['item'], 1)
        next_y = pdf.get_y()
        alt = next_y - curr_y
        pdf.set_xy(curr_x + 90, curr_y)
        pdf.cell(30, alt, status_txt, 1, 0, 'C')
        pdf.cell(70, alt, str(row['observacao']), 1, 1, 'L')
    return pdf.output()

# --- LÓGICA DE NEGÓCIO ---
CHECKLIST_DATA = {
    "5.1. Nível Operacional": [
        "Infraestrutura: Servidores, rede e terminais testados no local de uso?",
        "Acesso: Todos os usuários têm login e passwords ativos?",
        "Capacitação: 100% dos Multiplicadores aptos a apoiar os colegas?",
        "Carga de Dados: Informações críticas migradas com sucesso?"
    ],
    "5.2. Nível Tático": [
        "Simulação Geral: Teste ponta a ponta realizado com sucesso?",
        "Procedimentos (SOPs): Manuais disponíveis para consulta nos setores?",
        "Plano de Contingência: Equipe treinada para falhas de rede/sistema?",
        "Pendências Críticas: Bugs de alta prioridade 100% resolvidos?"
    ],
    "5.3. Nível Estratégico": [
        "Comunicação Institucional: Públicos externos avisados da transição?",
        "Suporte de Gestão: Equipes de reforço garantidas para Operação Assistida?",
        "Critérios de Sucesso: KPIs definidos (ex: tempo de espera, faturamento)?",
        "Veredicto Final (Go/No-Go): Autorização formal do Comitê Diretor?"
    ]
}

# --- NAVEGAÇÃO ---
st.sidebar.title("🎮 Navegação")
pagina = st.sidebar.radio("Ir para:", ["📝 Checklist de Projeto", "🏛️ Hub de Portfólio (IA)"])

if pagina == "📝 Checklist de Projeto":
    st.title("🚀 Go-Live Readiness")
    projeto_nome = st.sidebar.text_input("Nome do Projeto", value="Projeto Hospital Digital")
    responsavel = st.sidebar.text_input("Responsável Atual", value="GP_Responsavel")

    df_atual = pd.read_sql_query(f"SELECT * FROM prontidao WHERE projeto='{projeto_nome}'", conn)

    with st.form("checklist_form"):
        tabs = st.tabs(list(CHECKLIST_DATA.keys()))
        respostas = {}
        for i, (categoria, itens) in enumerate(CHECKLIST_DATA.items()):
            with tabs[i]:
                for item in itens:
                    item_ant = df_atual[df_atual['item'] == item]
                    def_stat = bool(item_ant['status'].iloc[0]) if not item_ant.empty else False
                    def_obs = item_ant['observacao'].iloc[0] if not item_ant.empty else ""
                    c1, c2 = st.columns([2, 1])
                    status = c1.checkbox(item, value=def_stat, key=f"chk_{item}")
                    obs = c2.text_input("Evidência", value=def_obs, key=f"obs_{item}", label_visibility="collapsed")
                    respostas[item] = {"status": status, "categoria": categoria, "obs": obs}

        if st.form_submit_button("💾 Salvar/Atualizar no Hub"):
            dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            c = conn.cursor()
            c.execute("DELETE FROM prontidao WHERE projeto=?", (projeto_nome,))
            for item, d in respostas.items():
                c.execute("INSERT INTO prontidao VALUES (?, ?, ?, ?, ?, ?, ?)",
                          (projeto_nome, d['categoria'], item, 1 if d['status'] else 0, d['obs'], dt, responsavel))
            conn.commit()
            st.success("Dados enviados ao Hub com sucesso!")
            st.rerun()

    # Dashboard Individual
    st.divider()
    df_view = pd.read_sql_query(f"SELECT * FROM prontidao WHERE projeto='{projeto_nome}'", conn)
    if not df_view.empty:
        perc = (df_view['status'].sum() / len(df_view)) * 100
        m1, m2, m3 = st.columns([1, 1, 1])
        m1.metric("Prontidão Individual", f"{perc:.1f}%")
        m2.progress(perc/100)
        pdf_bytes = gerar_pdf(df_view, projeto_nome, perc)
        m3.download_button("📥 Baixar PDF do Projeto", data=bytes(pdf_bytes), file_name=f"{projeto_nome}.pdf")
        st.dataframe(df_view[['categoria', 'item', 'status', 'observacao']].style.applymap(
            lambda x: 'background-color: #d4edda' if x == 1 else 'background-color: #f8d7da', subset=['status']
        ), use_container_width=True)

else:
    # --- HUB DE INTELIGÊNCIA ---
    st.title("🏛️ Hub de Inteligência e Rastreabilidade")
    df_hub = pd.read_sql_query("SELECT * FROM prontidao", conn)

    if not df_hub.empty:
        # KPI Cards do Hub
        num_projetos = df_hub['projeto'].nunique()
        prontidao_media = (df_hub['status'].sum() / len(df_hub)) * 100
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total de Projetos no Hub", num_projetos)
        c2.metric("Média de Prontidão (Portfólio)", f"{prontidao_media:.1f}%")
        c3.info("Base de Dados: Cloud SQL Ativa")

        st.subheader("📊 Saúde do Portfólio")
        # Gráfico comparativo entre projetos
        chart_hub = df_hub.groupby('projeto')['status'].mean() * 100
        st.bar_chart(chart_hub)

        st.subheader("📑 Registro Geral de Artefatos")
        st.write("Consulte aqui a última versão de cada item de cada projeto cadastrado.")
        
        # Filtro de Busca
        search = st.text_input("Filtrar Hub por Nome de Projeto ou Responsável")
        filtered_df = df_hub[df_hub['projeto'].str.contains(search, case=False) | 
                             df_hub['responsavel'].str.contains(search, case=False)]
        
        st.dataframe(filtered_df.sort_values(by="data_atualizacao", ascending=False), use_container_width=True)
        
        # Auditoria de Mudanças
        with st.expander("🕵️ Ver Histórico de Auditoria"):
            st.table(df_hub[['projeto', 'data_atualizacao', 'responsavel']].drop_duplicates())
    else:
        st.warning("O Hub ainda está vazio. Cadastre o primeiro projeto para gerar inteligência.")
