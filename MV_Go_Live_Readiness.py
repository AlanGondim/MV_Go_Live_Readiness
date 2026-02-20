import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from fpdf import FPDF
import matplotlib.pyplot as plt
import numpy as np
import io

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Hub de Inteligencia: Go-Live", layout="wide", page_icon="🚀")

# --- BANCO DE DADOS ---
def init_db():
    conn = sqlite3.connect('projetos_cloud_v3.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS prontidao 
                 (projeto TEXT, categoria TEXT, item TEXT, status INTEGER, 
                  observacao TEXT, data_atualizacao TEXT, responsavel TEXT, versao_id TEXT)''')
    conn.commit()
    return conn

conn = init_db()

# --- FUNÇÕES DE APOIO ---
def get_farol(percentual):
    if percentual >= 90:
        return "PRONTO", (0, 128, 0), "#d4edda"
    elif percentual >= 70:
        return "ATENCAO", (255, 165, 0), "#fff3cd"
    else:
        return "CRITICO", (255, 0, 0), "#f8d7da"

def gerar_grafico_radar(categorias, valores):
    labels = [c.replace("Nivel ", "") for c in categorias]
    stats = list(valores)
    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    stats += stats[:1]
    angles += angles[:1]
    
    fig, ax = plt.subplots(figsize=(4, 4), subplot_kw=dict(polar=True))
    ax.fill(angles, stats, color='skyblue', alpha=0.4)
    ax.plot(angles, stats, color='blue', linewidth=2)
    ax.set_yticklabels([])
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=8)
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', transparent=True)
    plt.close(fig)
    return buf

# --- CLASSE PDF CUSTOMIZADA (CORREÇÃO DEFINITIVA DA ROTAÇÃO) ---
class PDF_Executivo(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 14)
        self.set_text_color(44, 62, 80)
        self.cell(0, 10, 'HUB DE INTELIGENCIA - RELATORIO ESTRATEGICO GO-LIVE', 0, 1, 'C')
        self.set_font('Helvetica', 'I', 9)
        self.cell(0, 5, f'Gerado em: {datetime.now().strftime("%d/%m/%Y %H:%M")}', 0, 1, 'C')
        self.ln(10)
        self.line(10, 28, 200, 28)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, f'Pagina {self.page_no()}', 0, 0, 'C')

    def draw_watermark(self):
        """Usa local_context para garantir que a rotação não quebre o restante do PDF."""
        self.set_font('Helvetica', 'B', 50)
        self.set_text_color(230, 230, 230)
        with self.local_context():
            # Rotate em torno do centro da página A4 (105, 148)
            self.rotate(45, x=105, y=148)
            self.text(x=35, y=148, txt="C O N F I D E N C I A L")

    def desenhar_farol(self, x, y, r, g, b):
        self.set_fill_color(r, g, b)
        self.ellipse(x, y, 4, 4, 'F')

def gerar_pdf_completo(df_projeto, nome_projeto, data_versao):
    pdf = PDF_Executivo(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    pdf.draw_watermark()
    
    percentual = df_projeto['status'].mean() * 100
    label, rgb_cor, _ = get_farol(percentual)
    
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(0, 10, f"PROJETO: {nome_projeto.upper()}", 1, 1, 'L', fill=True)
    pdf.set_font('Helvetica', 'I', 10)
    pdf.cell(0, 8, f"Snapshot de: {data_versao}", 0, 1, 'L')
    
    # Adicionar Radar Chart
    cat_data = df_projeto.groupby('categoria')['status'].mean() * 100
    img_buf = gerar_grafico_radar(cat_data.index, cat_data.values)
    pdf.image(img_buf, x=130, y=50, w=65)
    
    pdf.ln(5)
    pdf.set_font('Helvetica', 'B', 11)
    pdf.cell(0, 8, "DESEMPENHO POR NIVEL", 0, 1)
    pdf.set_font('Helvetica', '', 10)
    for cat, val in cat_data.items():
        pdf.cell(100, 7, f"- {cat}: {val:.1f}%", 0, 1)
    
    pdf.ln(5)
    pdf.desenhar_farol(11, pdf.get_y() + 3, *rgb_cor)
    pdf.set_xy(16, pdf.get_y())
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(*rgb_cor)
    pdf.cell(0, 10, f"STATUS GERAL: {label} ({percentual:.1f}%)", 0, 1)
    pdf.set_text_color(0)
    
    pdf.ln(25)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(0, 8, "TRILHA DE RASTREABILIDADE", 0, 1)
    
    # Tabela de Itens
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_fill_color(200, 200, 200)
    pdf.cell(90, 8, "Item", 1, 0, 'C', True)
    pdf.cell(20, 8, "Status", 1, 0, 'C', True)
    pdf.cell(40, 8, "Responsavel", 1, 0, 'C', True)
    pdf.cell(40, 8, "Data", 1, 1, 'C', True)
    
    pdf.set_font('Helvetica', '', 7)
    for _, row in df_projeto.iterrows():
        status_txt = "OK" if row['status'] == 1 else "PENDENTE"
        y_ini = pdf.get_y()
        pdf.multi_cell(90, 5, row['item'], 1, 'L')
        h = pdf.get_y() - y_ini
        pdf.set_xy(100, y_ini)
        pdf.cell(20, h, status_txt, 1, 0, 'C')
        pdf.cell(40, h, row['responsavel'], 1, 0, 'C')
        pdf.cell(40, h, row['data_atualizacao'][:10], 1, 1, 'C')

    return pdf.output(dest='S')

# --- LOGICA DA INTERFACE ---
CHECKLIST_DATA = {
    "5.1. Nivel Operacional": ["Infraestrutura ok?", "Acessos ok?", "Capacitacao ok?", "Dados migrados?"],
    "5.2. Nivel Tatico": ["Simulacao Geral?", "Manuais disponiveis?", "Contingencia?", "Bugs críticos?"],
    "5.3. Nivel Estrategico": ["Comunicacao ok?", "Suporte garantido?", "KPIs definidos?", "Go-NoGo aprovado?"]
}

st.sidebar.title("🚀 Go-Live System")
menu = st.sidebar.radio("Navegar:", ["📝 Novo Registro", "🏛️ Hub & Historico"])

if menu == "📝 Novo Registro":
    st.title("📝 Atualizar Checklist")
    p_nome = st.text_input("Nome do Projeto", value="Projeto Alpha")
    p_resp = st.text_input("Responsavel", value="Admin")
    
    with st.form("main_form"):
        tabs = st.tabs(list(CHECKLIST_DATA.keys()))
        results = {}
        for i, (cat, itens) in enumerate(CHECKLIST_DATA.items()):
            with tabs[i]:
                for it in itens:
                    c1, c2 = st.columns([3, 1])
                    chk = c1.checkbox(it, key=f"c_{it}")
                    obs = c2.text_input("Evidência", key=f"o_{it}", label_visibility="collapsed")
                    results[it] = {"status": chk, "cat": cat, "obs": obs}
        
        if st.form_submit_button("💾 Salvar Snapshot"):
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            vid = datetime.now().strftime("%Y%m%d%H%M%S")
            cur = conn.cursor()
            for it, d in results.items():
                cur.execute("INSERT INTO prontidao VALUES (?,?,?,?,?,?,?,?)", 
                           (p_nome, d['cat'], it, 1 if d['status'] else 0, d['obs'], ts, p_resp, vid))
            conn.commit()
            st.success(f"Snapshot {vid} salvo com sucesso!")

else:
    st.title("🏛️ Hub de Inteligencia")
    df_hub = pd.read_sql_query("SELECT * FROM prontidao", conn)
    
    if not df_hub.empty:
        proj_sel = st.selectbox("Projeto:", df_hub['projeto'].unique())
        df_p = df_hub[df_hub['projeto'] == proj_sel]
        
        versoes = df_p[['data_atualizacao', 'versao_id']].drop_duplicates().sort_values(by='data_atualizacao', ascending=False)
        
        col1, col2 = st.columns([1, 2])
        with col1:
            v_escolhida = st.selectbox("Escolha a Versao:", versoes['data_atualizacao'].tolist())
            vid_sel = versoes[versoes['data_atualizacao'] == v_escolhida]['versao_id'].values[0]
            df_v = df_p[df_p['versao_id'] == vid_sel]
            
            p_final = df_v['status'].mean() * 100
            label, _, cor = get_farol(p_final)
            st.markdown(f"<div style='background-color:{cor}; padding:20px; border-radius:10px; color:black; text-align:center;'><h2>{p_final:.1f}%</h2><b>{label}</b></div>", unsafe_allow_html=True)
            
            pdf_data = gerar_pdf_completo(df_v, proj_sel, v_escolhida)
            st.download_button("📥 Baixar PDF (Snaphot)", data=bytes(pdf_data), file_name=f"Relatorio_{vid_sel}.pdf", mime="application/pdf")

        with col2:
            st.subheader("Análise Dimensional")
            # 
            cat_perf = df_v.groupby('categoria')['status'].mean() * 100
            st.image(gerar_grafico_radar(cat_perf.index, cat_perf.values))

        st.divider()
        st.subheader("📈 Linha do Tempo")
        evol = df_p.groupby('data_atualizacao')['status'].mean() * 100
        st.line_chart(evol)
    else:
        st.info("Nenhum dado encontrado.")
