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
    conn = sqlite3.connect('projetos_cloud_v2.db', check_same_thread=False)
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

# --- CLASSE PDF CUSTOMIZADA (CORRIGIDA) ---
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
        self.set_font('Helvetica', 'B', 45)
        self.set_text_color(230, 230, 230) # Cinza muito claro
        # Correção do erro de rotação: usando contexto seguro
        with self.rotation(angle=45, x=105, y=155):
            self.text(x=40, y=155, txt="C O N F I D E N C I A L")
        self.set_text_color(0)

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
    pdf.cell(0, 8, f"Snaphost de: {data_versao}", 0, 1, 'L')
    
    # Radar Chart
    cat_data = df_projeto.groupby('categoria')['status'].mean() * 100
    img_buf = gerar_grafico_radar(cat_data.index, cat_data.values)
    pdf.image(img_buf, x=125, y=55, w=70)
    
    pdf.ln(5)
    pdf.set_font('Helvetica', 'B', 11)
    pdf.cell(0, 8, "PERFORMANCE POR CATEGORIA", 0, 1)
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
    
    # Tabela
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_fill_color(200, 200, 200)
    pdf.cell(90, 8, "Item", 1, 0, 'C', True)
    pdf.cell(20, 8, "Status", 1, 0, 'C', True)
    pdf.cell(40, 8, "Responsavel", 1, 0, 'C', True)
    pdf.cell(40, 8, "Data", 1, 1, 'C', True)
    
    pdf.set_font('Helvetica', '', 7)
    for _, row in df_projeto.iterrows():
        status_txt = "OK" if row['status'] == 1 else "PENDENTE"
        y_pre = pdf.get_y()
        pdf.multi_cell(90, 5, row['item'], 1, 'L')
        h = pdf.get_y() - y_pre
        pdf.set_xy(100, y_pre)
        pdf.cell(20, h, status_txt, 1, 0, 'C')
        pdf.cell(40, h, row['responsavel'], 1, 0, 'C')
        pdf.cell(40, h, row['data_atualizacao'][:10], 1, 1, 'C')

    return pdf.output(dest='S')

# --- ESTRUTURA ---
CHECKLIST_DATA = {
    "5.1. Nivel Operacional": [
        "Infraestrutura: Servidores, rede e terminais testados?",
        "Acesso: Usuarios com logins e passwords ativos?",
        "Capacitacao: Multiplicadores aptos a apoiar?",
        "Carga de Dados: Migracao critica concluida?"
    ],
    "5.2. Nivel Tatico": [
        "Simulacao Geral: Teste ponta a ponta realizado?",
        "Procedimentos: Manuais disponiveis nos setores?",
        "Contingencia: Plano de falhas testado?",
        "Bugs: Erros criticos resolvidos?"
    ],
    "5.3. Nivel Estrategico": [
        "Comunicacao: Publicos externos avisados?",
        "Suporte: Equipes de reforco garantidas?",
        "KPIs: Metricas de sucesso definidas?",
        "Veredicto: Autorizacao formal Go-NoGo?"
    ]
}

# --- INTERFACE STREAMLIT ---
st.sidebar.title("🚀 Go-Live Hub")
pagina = st.sidebar.radio("Navegacao:", ["📝 Novo Checklist", "🏛️ Hub de Inteligencia"])

if pagina == "📝 Novo Checklist":
    st.title("📝 Registrar Prontidao")
    col_p, col_r = st.columns(2)
    proj_n = col_p.text_input("Projeto", value="Hospital Digital")
    resp_n = col_r.text_input("Responsavel", value="GP_User")

    with st.form("f_check"):
        tabs = st.tabs(list(CHECKLIST_DATA.keys()))
        resps = {}
        for i, (cat, itens) in enumerate(CHECKLIST_DATA.items()):
            with tabs[i]:
                for it in itens:
                    c1, c2 = st.columns([3, 1])
                    st_it = c1.checkbox(it, key=f"c_{it}")
                    obs_it = c2.text_input("Obs", key=f"o_{it}", label_visibility="collapsed")
                    resps[it] = {"status": st_it, "cat": cat, "obs": obs_it}
        
        if st.form_submit_button("💾 Salvar Versao"):
            now = datetime.now()
            dt_s = now.strftime("%Y-%m-%d %H:%M:%S")
            v_id = now.strftime("%Y%m%d%H%M%S")
            c = conn.cursor()
            for it, d in resps.items():
                c.execute("INSERT INTO prontidao VALUES (?,?,?,?,?,?,?,?)",
                          (proj_n, d['cat'], it, 1 if d['status'] else 0, d['obs'], dt_s, resp_n, v_id))
            conn.commit()
            st.success("Checklist sincronizado com sucesso!")
            st.toast("Hub Atualizado!")

else:
    st.title("🏛️ Hub de Inteligencia e Historico")
    df_hub = pd.read_sql_query("SELECT * FROM prontidao", conn)

    if not df_hub.empty:
        proj_sel = st.selectbox("Selecione o Projeto:", df_hub['projeto'].unique())
        df_p = df_hub[df_hub['projeto'] == proj_sel]
        
        versoes = df_p[['data_atualizacao', 'versao_id']].drop_duplicates().sort_values(by='data_atualizacao', ascending=False)
        
        col_l, col_r = st.columns([1, 2])
        
        with col_l:
            v_date = st.radio("Versoes disponiveis:", versoes['data_atualizacao'].tolist())
            v_id = versoes[versoes['data_atualizacao'] == v_date]['versao_id'].values[0]
            df_v = df_p[df_p['versao_id'] == v_id]
            
            perc = df_v['status'].mean() * 100
            label, _, cor = get_farol(perc)
            st.markdown(f"""<div style="background-color:{cor}; padding:20px; border-radius:10px; color:black; text-align:center;">
                            <h3>{perc:.1f}%</h3><b>{label}</b></div>""", unsafe_allow_html=True)
            
            # Gerar PDF
            pdf_out = gerar_pdf_completo(df_v, proj_sel, v_date)
            st.download_button("📥 Baixar PDF desta Versao", data=bytes(pdf_out), 
                               file_name=f"Relatorio_{proj_sel}_{v_id}.pdf", mime="application/pdf", use_container_width=True)

        with col_r:
            cat_r = df_v.groupby('categoria')['status'].mean() * 100
            # 
            st.image(gerar_grafico_radar(cat_r.index, cat_r.values), caption=f"Mapa de Prontidao: {v_date}")
            
        st.divider()
        st.subheader("📈 Evolucao do Projeto")
        evol = df_p.groupby('data_atualizacao')['status'].mean() * 100
        st.line_chart(evol)
    else:
        st.info("Aguardando o primeiro registro no checklist.")
