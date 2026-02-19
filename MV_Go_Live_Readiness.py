import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from fpdf import FPDF
import matplotlib.pyplot as plt
import numpy as np
import io

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
        return "PRONTO", (0, 128, 0), "#d4edda"
    elif percentual >= 70:
        return "ATENCAO", (255, 165, 0), "#fff3cd"
    else:
        return "CRITICO", (255, 0, 0), "#f8d7da"

def gerar_grafico_radar(categorias, valores):
    labels = list(categorias)
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

# --- CLASSE PDF CUSTOMIZADA ---
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
        self.set_font('Helvetica', 'B', 50)
        self.set_text_color(240, 240, 240)
        with self.rotation(45, x=105, y=155):
            self.text(45, 155, "C O N F I D E N C I A L")
        self.set_text_color(0)

    def desenhar_farol(self, x, y, r, g, b):
        self.set_fill_color(r, g, b)
        self.ellipse(x, y, 4, 4, 'F')

def gerar_pdf_completo(df_projeto, nome_projeto):
    pdf = PDF_Executivo(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    pdf.draw_watermark()
    
    # 1. Cabeçalho
    percentual = df_projeto['status'].mean() * 100
    label, rgb_cor, _ = get_farol(percentual)
    
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(0, 10, f"PROJETO: {nome_projeto.upper()}", 1, 1, 'L', fill=True)
    
    # 2. Resumo e Radar
    pdf.ln(5)
    pdf.set_font('Helvetica', 'B', 11)
    pdf.cell(0, 8, "RESUMO DE PERFORMANCE POR NIVEL", 0, 1)
    
    cat_data = df_projeto.groupby('categoria')['status'].mean() * 100
    img_buf = gerar_grafico_radar(cat_data.index, cat_data.values)
    pdf.image(img_buf, x=125, y=45, w=70)
    
    pdf.set_font('Helvetica', '', 10)
    for cat, val in cat_data.items():
        pdf.cell(100, 7, f"- {cat}: {val:.1f}%", 0, 1)
    
    pdf.ln(5)
    curr_y = pdf.get_y() + 3
    pdf.desenhar_farol(11, curr_y, *rgb_cor)
    pdf.set_xy(16, pdf.get_y())
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(*rgb_cor)
    pdf.cell(0, 10, f"STATUS GERAL: {label} ({percentual:.1f}%)", 0, 1)
    pdf.set_text_color(0)
    
    pdf.ln(20) 
    
    # 3. Trilha de Rastreabilidade
    pdf.set_font('Helvetica', 'B', 11)
    pdf.cell(0, 8, "TRILHA DE RASTREABILIDADE E EVIDENCIAS", 0, 1)
    
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_fill_color(200, 200, 200)
    pdf.cell(85, 8, "Item / Entrega", 1, 0, 'C', True)
    pdf.cell(20, 8, "Status", 1, 0, 'C', True)
    pdf.cell(45, 8, "Evidencia/Obs", 1, 0, 'C', True)
    pdf.cell(40, 8, "Data/Resp", 1, 1, 'C', True)
    
    pdf.set_font('Helvetica', '', 7)
    for _, row in df_projeto.iterrows():
        status_txt = "CONCLUIDO" if row['status'] == 1 else "PENDENTE"
        x_start, y_start = pdf.get_x(), pdf.get_y()
        
        pdf.multi_cell(85, 5, row['item'], 1, 'L')
        h = pdf.get_y() - y_start
        
        pdf.set_xy(x_start + 85, y_start)
        pdf.cell(20, h, status_txt, 1, 0, 'C')
        pdf.cell(45, h, str(row['observacao'])[:35], 1, 0, 'L')
        data_limpa = str(row['data_atualizacao'])[:10]
        pdf.multi_cell(40, h/2 if h > 10 else h, f"{row['responsavel']}\n{data_limpa}", 1, 'C')

    return pdf.output(dest='S')

# --- ESTRUTURA DO CHECKLIST ---
CHECKLIST_DATA = {
    "5.1. Nivel Operacional": [
        "Infraestrutura: Servidores, rede e terminais testados no local de uso?",
        "Acesso: Todos os usuarios tem login e passwords ativos?",
        "Capacitacao: 100% dos Multiplicadores aptos a apoiar os colegas?",
        "Carga de Dados: Informacoes criticas migradas com sucesso?"
    ],
    "5.2. Nivel Tatico": [
        "Simulacao Geral: Teste ponta a ponta realizado com sucesso?",
        "Procedimentos (SOPs): Manuais disponiveis para consulta nos setores?",
        "Plano de Contingencia: Equipe treinada para falhas de rede/sistema?",
        "Pendencias Criticas: Bugs de alta prioridade 100% resolvidos?"
    ],
    "5.3. Nivel Estrategico": [
        "Comunicacao Institucional: Publicos externos avisados da transicao?",
        "Suporte de Gestao: Equipes de reforco garantidas para Operacao Assistida?",
        "Criterios de Sucesso: KPIs definidos (ex: tempo de espera, faturamento)?",
        "Veredicto Final (Go/No-Go): Autorizacao formal do Comite Diretor?"
    ]
}

# --- NAVEGAÇÃO STREAMLIT ---
st.sidebar.title("🎮 Menu Principal")
pagina = st.sidebar.radio("Selecione a Visão:", ["📝 Atualizar Checklist", "🏛️ Hub de Inteligência"])

if pagina == "📝 Atualizar Checklist":
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

        if st.form_submit_button("💾 Enviar para o Hub"):
            dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            c = conn.cursor()
            c.execute("DELETE FROM prontidao WHERE projeto=?", (projeto_nome,))
            for item, d in respostas.items():
                c.execute("INSERT INTO prontidao VALUES (?, ?, ?, ?, ?, ?, ?)",
                          (projeto_nome, d['categoria'], item, 1 if d['status'] else 0, d['obs'], dt, responsavel))
            conn.commit()
            
            # --- MENSAGEM DE SUCESSO APRIMORADA ---
            st.toast(f"Checklist do {projeto_nome} enviado com sucesso!", icon='✅')
            st.success(f"**Sucesso!** O checklist do projeto '{projeto_nome}' foi sincronizado com o Hub de Inteligência.")
            st.info(f"📅 Data da Versão: {dt} | Responsável: {responsavel}")
            
            if st.button("Ir para o Hub agora"):
                st.switch_page(pagina="🏛️ Hub de Inteligência")

else:
    # --- HUB DE INTELIGÊNCIA ---
    st.title("🏛️ Hub de Inteligência (Farol de Prontidão)")
    df_hub = pd.read_sql_query("SELECT * FROM prontidao", conn)

    if not df_hub.empty:
        projs = df_hub['projeto'].unique()
        cols = st.columns(len(projs) if len(projs) <= 4 else 4)
        
        for i, proj in enumerate(projs):
            df_p = df_hub[df_hub['projeto'] == proj]
            p_perc = df_p['status'].mean() * 100
            label, _, cor_hex = get_farol(p_perc)
            emoji = "🟢" if "PRONTO" in label else "🟡" if "ATENCAO" in label else "🔴"
            
            with cols[i % 4]:
                st.markdown(f"""
                <div style="background-color:{cor_hex}; padding:15px; border-radius:10px; border:1px solid #999; text-align:center; color:black; min-height:150px;">
                    <small>{proj}</small><h3>{p_perc:.1f}%</h3><b>{emoji} {label}</b>
                </div>
                """, unsafe_allow_html=True)
                
                pdf_bytes = gerar_pdf_completo(df_p, proj)
                st.download_button(
                    label=f"📥 Relatório PDF",
                    data=bytes(pdf_bytes),
                    file_name=f"Relatorio_GoLive_{proj}.pdf",
                    mime="application/pdf",
                    key=f"pdf_{proj}",
                    use_container_width=True
                )

        st.divider()
        st.subheader("📊 Analise Multidimensional (Radar)")
        p_escolhido = st.selectbox("Selecione o projeto para visualizacao:", projs)
        df_radar = df_hub[df_hub['projeto'] == p_escolhido]
        cat_radar = df_radar.groupby('categoria')['status'].mean() * 100
        
        # 
        fig_st = gerar_grafico_radar(cat_radar.index, cat_radar.values)
        st.image(fig_st, caption=f"Mapa de Prontidao: {p_escolhido}", width=500)

    else:
        st.warning("O Hub está vazio. Preencha o checklist para começar.")
