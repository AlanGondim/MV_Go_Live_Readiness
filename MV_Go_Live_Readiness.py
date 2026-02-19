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
    conn = sqlite3.connect('projetos_cloud_v2.db', check_same_thread=False)
    c = conn.cursor()
    # Adicionado campo 'versao_id' para rastrear snapshots
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
        self.cell(0, 5, f'Relatorio Gerado em: {datetime.now().strftime("%d/%m/%Y %H:%M")}', 0, 1, 'C')
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
    pdf.cell(0, 8, f"Versao Referente a: {data_versao}", 0, 1, 'L')
    
    pdf.ln(5)
    cat_data = df_projeto.groupby('categoria')['status'].mean() * 100
    img_buf = gerar_grafico_radar(cat_data.index, cat_data.values)
    pdf.image(img_buf, x=125, y=55, w=70)
    
    pdf.set_font('Helvetica', 'B', 11)
    pdf.cell(0, 8, "PERFORMANCE POR NIVEL", 0, 1)
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
    pdf.set_font('Helvetica', 'B', 11)
    pdf.cell(0, 8, "DETALHAMENTO E RASTREABILIDADE", 0, 1)
    
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_fill_color(200, 200, 200)
    pdf.cell(85, 8, "Item", 1, 0, 'C', True)
    pdf.cell(20, 8, "Status", 1, 0, 'C', True)
    pdf.cell(45, 8, "Evidencia", 1, 0, 'C', True)
    pdf.cell(40, 8, "Responsavel", 1, 1, 'C', True)
    
    pdf.set_font('Helvetica', '', 7)
    for _, row in df_projeto.iterrows():
        status_txt = "OK" if row['status'] == 1 else "PENDENTE"
        y_start = pdf.get_y()
        pdf.multi_cell(85, 5, row['item'], 1, 'L')
        h = pdf.get_y() - y_start
        pdf.set_xy(95, y_start)
        pdf.cell(20, h, status_txt, 1, 0, 'C')
        pdf.cell(45, h, str(row['observacao'])[:30], 1, 0, 'L')
        pdf.cell(40, h, row['responsavel'], 1, 1, 'C')

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

# --- NAVEGAÇÃO ---
st.sidebar.title("🚀 Sistema Go-Live")
pagina = st.sidebar.radio("Menu:", ["📝 Novo Checklist", "🏛️ Hub & Histórico"])

if pagina == "📝 Novo Checklist":
    st.title("📝 Atualizar Prontidão")
    projeto_nome = st.text_input("Nome do Projeto", value="Projeto Hospital Digital")
    responsavel = st.text_input("Responsável", value="GP_Responsavel")

    with st.form("checklist_form"):
        tabs = st.tabs(list(CHECKLIST_DATA.keys()))
        respostas = {}
        for i, (categoria, itens) in enumerate(CHECKLIST_DATA.items()):
            with tabs[i]:
                for item in itens:
                    c1, c2 = st.columns([2, 1])
                    status = c1.checkbox(item, key=f"chk_{item}")
                    obs = c2.text_input("Evidência", key=f"obs_{item}", label_visibility="collapsed")
                    respostas[item] = {"status": status, "categoria": categoria, "obs": obs}

        if st.form_submit_button("💾 Salvar Nova Versão no Hub"):
            dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            v_id = datetime.now().strftime("%Y%m%d%H%M%S") # ID único da versão
            c = conn.cursor()
            for item, d in respostas.items():
                c.execute("INSERT INTO prontidao VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                          (projeto_nome, d['categoria'], item, 1 if d['status'] else 0, d['obs'], dt, responsavel, v_id))
            conn.commit()
            st.success(f"✅ Versão de {dt} salva com sucesso!")
            st.toast("Dados sincronizados!", icon='🚀')

else:
    st.title("🏛️ Hub de Inteligência e Histórico")
    df_all = pd.read_sql_query("SELECT * FROM prontidao", conn)

    if not df_all.empty:
        projeto_sel = st.selectbox("Escolha o Projeto:", df_all['projeto'].unique())
        
        # Filtrar versões do projeto escolhido
        df_proj_total = df_all[df_all['projeto'] == projeto_sel]
        versoes = df_proj_total[['data_atualizacao', 'versao_id']].drop_duplicates().sort_values(by='data_atualizacao', ascending=False)
        
        col_hist, col_vis = st.columns([1, 2])
        
        with col_hist:
            st.subheader("📜 Versões Salvas")
            # Seleção da versão para visualização
            v_selecionada = st.radio("Selecione uma data para ver o farol:", 
                                     versoes['data_atualizacao'].tolist(), 
                                     index=0)
            
            v_id_sel = versoes[versoes['data_atualizacao'] == v_selecionada]['versao_id'].values[0]
            df_snapshot = df_proj_total[df_proj_total['versao_id'] == v_id_sel]
            
            # Métricas da Versão Selecionada
            p_perc = df_snapshot['status'].mean() * 100
            label, _, cor_hex = get_farol(p_perc)
            
            st.markdown(f"""
            <div style="background-color:{cor_hex}; padding:20px; border-radius:10px; border:2px solid #333; text-align:center; color:black;">
                <h4>Status em {v_selecionada[:10]}</h4>
                <h1>{p_perc:.1f}%</h1>
                <b>{label}</b>
            </div>
            """, unsafe_allow_html=True)
            
            # Botão de PDF para esta versão específica
            pdf_v = gerar_pdf_completo(df_snapshot, projeto_sel, v_selecionada)
            st.download_button(
                label="📥 Baixar PDF desta Versão",
                data=bytes(pdf_v),
                file_name=f"Relatorio_{projeto_sel}_{v_id_sel}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

        with col_vis:
            st.subheader("📊 Análise de Evolução")
            cat_radar = df_snapshot.groupby('categoria')['status'].mean() * 100
            fig_st = gerar_grafico_radar(cat_radar.index, cat_radar.values)
            st.image(fig_st, caption=f"Mapa de Prontidão - Versão: {v_selecionada}")
            
            with st.expander("Ver Detalhes da Trilha de Rastreabilidade"):
                st.table(df_snapshot[['categoria', 'item', 'status', 'responsavel']])

        st.divider()
        st.subheader("📈 Linha do Tempo de Performance")
        # Gráfico de linha mostrando a evolução do projeto ao longo das versões
        evolucao = df_proj_total.groupby('data_atualizacao')['status'].mean() * 100
        st.line_chart(evolucao)

    else:
        st.warning("O banco de dados está vazio. Crie o primeiro checklist.")
