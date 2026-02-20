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
    conn = sqlite3.connect('projetos_cloud_final.db', check_same_thread=False)
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

# --- CLASSE PDF COM ROTAÇÃO COMPATÍVEL (VERSÃO UNIVERSAL) ---
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
        """Método de rotação compatível com versões antigas e novas da FPDF2."""
        self.set_font('Helvetica', 'B', 50)
        self.set_text_color(235, 235, 235)
        
        # Salvando o estado atual e aplicando rotação manual
        angle = 45
        x, y = 105, 148 # Centro da página
        
        # O comando 'rotate' sem o 'with' funciona na maioria das versões
        # Caso o rotate falhe, o texto sairá horizontal, mas o app não quebrará.
        try:
            with self.rotation(angle, x, y):
                self.text(x=35, y=y, txt="C O N F I D E N C I A L")
        except:
            # Fallback para caso a função de rotação falte completamente
            self.text(x=35, y=y, txt="CONFIDENCIAL (DRAFT)")
            
        self.set_text_color(0) # Reset cor

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
    pdf.cell(0, 8, f"Snapshot da Versao: {data_versao}", 0, 1, 'L')
    
    # Inserção do Radar Chart
    cat_data = df_projeto.groupby('categoria')['status'].mean() * 100
    img_buf = gerar_grafico_radar(cat_data.index, cat_data.values)
    pdf.image(img_buf, x=130, y=55, w=65)
    
    pdf.ln(5)
    pdf.set_font('Helvetica', 'B', 11)
    pdf.cell(0, 8, "DISTRIBUICAO POR NIVEL", 0, 1)
    pdf.set_font('Helvetica', '', 10)
    for cat, val in cat_data.items():
        pdf.cell(100, 7, f"- {cat}: {val:.1f}%", 0, 1)
    
    pdf.ln(5)
    pdf.desenhar_farol(11, pdf.get_y() + 3, *rgb_cor)
    pdf.set_xy(16, pdf.get_y())
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(*rgb_cor)
    pdf.cell(0, 10, f"FAROL GERAL: {label} ({percentual:.1f}%)", 0, 1)
    pdf.set_text_color(0)
    
    pdf.ln(25)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(0, 8, "TRILHA DE RASTREABILIDADE", 0, 1)
    
    # Cabeçalho Tabela
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(90, 8, "Item", 1, 0, 'C', True)
    pdf.cell(20, 8, "Status", 1, 0, 'C', True)
    pdf.cell(40, 8, "Responsavel", 1, 0, 'C', True)
    pdf.cell(40, 8, "Data", 1, 1, 'C', True)
    
    pdf.set_font('Helvetica', '', 7)
    for _, row in df_projeto.iterrows():
        status_txt = "OK" if row['status'] == 1 else "PENDENTE"
        y_topo = pdf.get_y()
        pdf.multi_cell(90, 5, row['item'], 1, 'L')
        h = pdf.get_y() - y_topo
        pdf.set_xy(100, y_topo)
        pdf.cell(20, h, status_txt, 1, 0, 'C')
        pdf.cell(40, h, row['responsavel'], 1, 0, 'C')
        pdf.cell
