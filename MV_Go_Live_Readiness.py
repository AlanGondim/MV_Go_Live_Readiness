import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from fpdf import FPDF
import io

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Go-Live Readiness Pro", layout="wide", page_icon="🚀")

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
        # Usando 'Arial' ou 'Helvetica' (padrões do FPDF)
        self.set_font('Helvetica', 'B', 12)
        self.cell(0, 10, 'Relatorio de Prontidao Go-Live (Readiness Report)', 0, 1, 'C')
        self.ln(5)

def gerar_pdf(df, projeto, percentual):
    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Cabeçalho do Projeto
    pdf.set_fill_color(200, 220, 255)
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(0, 10, f"Projeto: {projeto}", 1, 1, 'L', 1)
    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 10, f"Status Global: {percentual:.1f}%", 1, 1, 'L', 1)
    pdf.cell(0, 10, f"Data do Relatorio: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 1, 1, 'L', 1)
    pdf.ln(10)
    
    # Cabeçalho da Tabela
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(90, 8, "Item", 1, 0, 'C')
    pdf.cell(30, 8, "Status", 1, 0, 'C')
    pdf.cell(70, 8, "Observacoes", 1, 1, 'C')
    
    # Conteúdo
    pdf.set_font("Helvetica", size=8)
    for _, row in df.iterrows():
        status_txt = "CONCLUIDO" if row['status'] == 1 else "PENDENTE"
        obs_txt = str(row['observacao']) if row['observacao'] else "-"
        
        # Lógica para Multi-célula (ajusta altura dinamicamente)
        curr_x = pdf.get_x()
        curr_y = pdf.get_y()
        
        pdf.multi_cell(90, 8, row['item'], 1)
        next_y = pdf.get_y()
        alt_celula = next_y - curr_y
        
        pdf.set_xy(curr_x + 90, curr_y)
        pdf.cell(30, alt_celula, status_txt, 1, 0, 'C')
        pdf.cell(70, alt_celula, obs_txt, 1, 1, 'L')
    
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

# --- INTERFACE ---
st.title("🚀 Go-Live Readiness Tracker")

projeto_nome = st.sidebar.text_input("Nome do Projeto", value="Projeto Hospital Digital")
responsavel = st.sidebar.text_input("Responsável", value="GP_Responsavel")

# Buscar dados para preencher o form
df_atual = pd.read_sql_query(f"SELECT * FROM prontidao WHERE projeto='{projeto_nome}'", conn)

with st.form("checklist_form"):
    st.subheader("📝 Atualização de Status")
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

    if st.form_submit_button("💾 Salvar Alterações na Nuvem"):
        c = conn.cursor()
        dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("DELETE FROM prontidao WHERE projeto=?", (projeto_nome,))
        for item, d in respostas.items():
            c.execute("INSERT INTO prontidao VALUES (?, ?, ?, ?, ?, ?, ?)",
                      (projeto_nome, d['categoria'], item, 1 if d['status'] else 0, d['obs'], dt, responsavel))
        conn.commit()
        st.success("Dados salvos com sucesso!")
        st.rerun()

# --- DASHBOARD ---
st.divider()
df_view = pd.read_sql_query(f"SELECT * FROM prontidao WHERE projeto='{projeto_nome}'", conn)

if not df_view.empty:
    total = len(df_view)
    concluido = df_view['status'].sum()
    perc = (concluido / total) * 100

    m1, m2, m3 = st.columns([1, 1, 1])
    m1.metric("Prontidão Global", f"{perc:.1f}%")
    m2.progress(perc / 100)
    
    # Botão de PDF
    pdf_bytes = gerar_pdf(df_view, projeto_nome, perc)
    m3.download_button(
        label="📥 Baixar Relatório PDF",
        data=bytes(pdf_bytes),
        file_name=f"Readiness_{projeto_nome}.pdf",
        mime="application/pdf"
    )

    c1, c2 = st.columns(2)
    chart_data = df_view.groupby('categoria')['status'].mean() * 100
    c1.bar_chart(chart_data)
    c2.write("### Histórico de Atualização")
    c2.dataframe(df_view[['data_atualizacao', 'responsavel']].drop_duplicates())

    st.subheader("🔍 Detalhamento dos Itens")
    st.dataframe(df_view[['categoria', 'item', 'status', 'observacao']].style.applymap(
        lambda x: 'background-color: #d4edda' if x == 1 else 'background-color: #f8d7da', subset=['status']
    ), use_container_width=True)
else:
    st.info("Inicie o preenchimento para gerar o dashboard.")
