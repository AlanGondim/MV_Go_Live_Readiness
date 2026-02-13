import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from fpdf import FPDF

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Hub de Inteligência: Go-Live", layout="wide", page_icon="🚀")

# --- BANCO DE DADOS ---
def init_db():
    conn = sqlite3.connect('projetos_cloud.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS prontidao 
                 (projeto TEXT, categoria TEXT, item TEXT, status INTEGER, 
                  observacao TEXT, data_atualizacao TEXT, responsavel TEXT)''')
    conn.commit()
    return conn

conn = init_db()

# --- FUNÇÕES DE APOIO ---
def get_farol(percentual):
    if percentual >= 90:
        return "🟢 PRONTO", "#d4edda"
    elif percentual >= 70:
        return "🟡 ATENÇÃO", "#fff3cd"
    else:
        return "🔴 CRÍTICO", "#f8d7da"

class PDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 12)
        self.cell(0, 10, 'Relatorio de Prontidao Go-Live', 0, 1, 'C')
        self.ln(5)

def gerar_pdf(df, projeto, percentual):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(0, 10, f"Projeto: {projeto} | Status: {get_farol(percentual)[0]}", 1, 1, 'L')
    pdf.ln(10)
    pdf.set_font("Helvetica", size=8)
    for _, row in df.iterrows():
        status = "OK" if row['status'] == 1 else "PENDENTE"
        pdf.multi_cell(0, 8, f"[{status}] {row['categoria']} - {row['item']}", 1)
    return pdf.output()

# --- ESTRUTURA DO CHECKLIST ---
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
st.sidebar.title("🎮 Menu Principal")
pagina = st.sidebar.radio("Selecione a Visão:", ["📝 Atualizar Checklist", "🏛️ Hub de Inteligência"])

if pagina == "📝 Atualizar Checklist":
    st.title("🚀 Go-Live Readiness Tracker")
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

        if st.form_submit_button("💾 Enviar para o Hub"):
            dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            c = conn.cursor()
            c.execute("DELETE FROM prontidao WHERE projeto=?", (projeto_nome,))
            for item, d in respostas.items():
                c.execute("INSERT INTO prontidao VALUES (?, ?, ?, ?, ?, ?, ?)",
                          (projeto_nome, d['categoria'], item, 1 if d['status'] else 0, d['obs'], dt, responsavel))
            conn.commit()
            st.success("Dados salvos!")
            st.rerun()

else:
    # --- HUB DE INTELIGÊNCIA ---
    st.title("🏛️ Hub de Inteligência (Farol de Prontidão)")
    df_hub = pd.read_sql_query("SELECT * FROM prontidao", conn)

    if not df_hub.empty:
        # --- FAROL GLOBAL POR PROJETO ---
        st.subheader("🚩 Status Geral do Portfólio")
        projs = df_hub['projeto'].unique()
        cols = st.columns(len(projs) if len(projs) <= 4 else 4)
        
        for i, proj in enumerate(projs):
            df_p = df_hub[df_hub['projeto'] == proj]
            p_perc = df_p['status'].mean() * 100
            label, cor = get_farol(p_perc)
            with cols[i % 4]:
                st.markdown(f"""
                <div style="background-color:{cor}; padding:20px; border-radius:10px; border:1px solid #ccc; text-align:center;">
                    <h4 style="color:black; margin:0;">{proj}</h4>
                    <h2 style="color:black; margin:10px 0;">{p_perc:.1f}%</h2>
                    <b style="color:black;">{label}</b>
                </div>
                """, unsafe_allow_html=True)

        # --- COMPARATIVO LADO A LADO ---
        st.divider()
        st.subheader("⚖️ Comparativo de Performance")
        p1 = st.selectbox("Projeto A", projs, index=0)
        p2 = st.selectbox("Projeto B", projs, index=min(1, len(projs)-1))

        df_p1 = df_hub[df_hub['projeto'] == p1]
        df_p2 = df_hub[df_hub['projeto'] == p2]
        
        comp_data = pd.DataFrame({
            p1: df_p1.groupby('categoria')['status'].mean() * 100,
            p2: df_p2.groupby('categoria')['status'].mean() * 100
        })
        st.bar_chart(comp_data)

        # --- TABELA DE AUDITORIA ---
        st.divider()
        st.subheader("🕵️ Trilha de Rastreabilidade")
        st.dataframe(df_hub.sort_values(by="data_atualizacao", ascending=False), use_container_width=True)
    else:
        st.warning("O Hub está vazio.")
