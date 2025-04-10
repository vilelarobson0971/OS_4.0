import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import os
import shutil
import time
import glob
import base64
import json

# Configurações da página
st.set_page_config(
    page_title="Sistema de Ordens de Serviço",
    page_icon="🔧",
    layout="wide"
)

# Tenta importar o PyGithub com fallback
try:
    from github import Github
    GITHUB_AVAILABLE = True
except ImportError:
    GITHUB_AVAILABLE = False
    st.warning("Funcionalidade do GitHub não disponível (PyGithub não instalado)")

# Constantes
LOCAL_FILENAME = "ordens_servico4.0.csv"
BACKUP_DIR = "backups"
MAX_BACKUPS = 10
SENHA_SUPERVISAO = "king@2025"
CONFIG_FILE = "config.json"

# Executantes pré-definidos
EXECUTANTES_PREDEFINIDOS = ["Robson", "Guilherme", "Paulinho"]

# Variáveis globais para configuração do GitHub
GITHUB_REPO = None
GITHUB_FILEPATH = None
GITHUB_TOKEN = None

TIPOS_MANUTENCAO = {
    1: "Elétrica",
    2: "Mecânica",
    3: "Refrigeração",
    4: "Hidráulica",
    5: "Civil",
    6: "Instalação"
}

STATUS_OPCOES = {
    1: "Pendente",
    2: "Pausado",
    3: "Em execução",
    4: "Concluído"
}

# Funções auxiliares (manter todas as funções auxiliares originais aqui)
# ... [todas as funções auxiliares permanecem exatamente como no original] ...

def dashboard():
    st.header("📊 Dashboard Analítico")
    df = carregar_csv()

    if df.empty:
        st.warning("Nenhuma OS cadastrada para análise.")
        return

    tab1, tab2, tab3, tab4 = st.tabs(["🔧 Tipos", "👥 Executantes", "📈 Status", "⏱️ Lead Time"])

    with tab1:
        st.subheader("Distribuição por Tipo de Manutenção")
        tipo_counts = df["Tipo"].value_counts()
        
        if not tipo_counts.empty:
            fig, ax = plt.subplots(figsize=(8, 6))
            
            # Gráfico de rosca
            wedges, texts, autotexts = ax.pie(
                tipo_counts.values,
                labels=tipo_counts.index,
                autopct='%1.1f%%',
                startangle=90,
                wedgeprops=dict(width=0.4),
                textprops={'fontsize': 12}
            )
            
            # Ajusta o tamanho da fonte dos valores
            for autotext in autotexts:
                autotext.set_fontsize(12)
                autotext.set_color('white')
            
            # Adiciona um círculo no meio para fazer o efeito rosca
            centre_circle = plt.Circle((0,0), 0.70, fc='white')
            ax.add_artist(centre_circle)
            
            # Move a legenda para a direita
            ax.legend(
                wedges,
                tipo_counts.index,
                title="Tipos",
                loc="center left",
                bbox_to_anchor=(1, 0, 0.5, 1)
            )
            
            ax.set_title("Distribuição por Tipo de Manutenção", fontsize=14)
            st.pyplot(fig)
        else:
            st.warning("Nenhum dado de tipo disponível")

    with tab2:
        st.subheader("OS por Executantes")
        # Combina os dois executantes para análise
        executantes = pd.concat([df["Executante1"], df["Executante2"]])
        executante_counts = executantes[executantes != ""].value_counts()
        
        if not executante_counts.empty:
            fig, ax = plt.subplots(figsize=(8, 6))
            
            # Gráfico de rosca
            wedges, texts, autotexts = ax.pie(
                executante_counts.values,
                labels=executante_counts.index,
                autopct='%1.1f%%',
                startangle=90,
                wedgeprops=dict(width=0.4),
                textprops={'fontsize': 12}
            )
            
            # Ajusta o tamanho da fonte dos valores
            for autotext in autotexts:
                autotext.set_fontsize(12)
                autotext.set_color('white')
            
            # Adiciona um círculo no meio para fazer o efeito rosca
            centre_circle = plt.Circle((0,0), 0.70, fc='white')
            ax.add_artist(centre_circle)
            
            # Move a legenda para a direita
            ax.legend(
                wedges,
                executante_counts.index,
                title="Executantes",
                loc="center left",
                bbox_to_anchor=(1, 0, 0.5, 1)
            )
            
            ax.set_title("OS por Executantes", fontsize=14)
            st.pyplot(fig)
        else:
            st.warning("Nenhuma OS atribuída a executantes")

    with tab3:
        st.subheader("Distribuição por Status")
        status_counts = df["Status"].value_counts()
        
        if not status_counts.empty:
            fig, ax = plt.subplots(figsize=(8, 6))
            
            # Gráfico de rosca
            wedges, texts, autotexts = ax.pie(
                status_counts.values,
                labels=status_counts.index,
                autopct='%1.1f%%',
                startangle=90,
                wedgeprops=dict(width=0.4),
                textprops={'fontsize': 12}
            )
            
            # Ajusta o tamanho da fonte dos valores
            for autotext in autotexts:
                autotext.set_fontsize(12)
                autotext.set_color('white')
            
            # Adiciona um círculo no meio para fazer o efeito rosca
            centre_circle = plt.Circle((0,0), 0.70, fc='white')
            ax.add_artist(centre_circle)
            
            # Move a legenda para a direita
            ax.legend(
                wedges,
                status_counts.index,
                title="Status",
                loc="center left",
                bbox_to_anchor=(1, 0, 0.5, 1)
            )
            
            ax.set_title("Distribuição por Status", fontsize=14)
            st.pyplot(fig)
        else:
            st.warning("Nenhum dado de status disponível")

    with tab4:
        st.subheader("Lead Time Médio por Tipo (horas)")
        lead_time_df = calcular_lead_time(df)
        
        if lead_time_df is not None and not lead_time_df.empty:
            # Ordena por lead time médio
            lead_time_df = lead_time_df.sort_values("Lead_Time_Medio_Horas", ascending=False)
            
            fig, ax = plt.subplots(figsize=(8, 6))
            
            # Gráfico de rosca
            wedges, texts, autotexts = ax.pie(
                lead_time_df["Lead_Time_Medio_Horas"],
                labels=lead_time_df["Tipo"],
                autopct=lambda p: f'{p * sum(lead_time_df["Lead_Time_Medio_Horas"])/100:.1f}h',
                startangle=90,
                wedgeprops=dict(width=0.4),
                textprops={'fontsize': 12}
            )
            
            # Ajusta o tamanho da fonte dos valores
            for autotext in autotexts:
                autotext.set_fontsize(12)
                autotext.set_color('white')
            
            # Adiciona um círculo no meio para fazer o efeito rosca
            centre_circle = plt.Circle((0,0), 0.70, fc='white')
            ax.add_artist(centre_circle)
            
            # Move a legenda para a direita
            ax.legend(
                wedges,
                lead_time_df["Tipo"],
                title="Tipos",
                loc="center left",
                bbox_to_anchor=(1, 0, 0.5, 1)
            )
            
            ax.set_title("Lead Time Médio por Tipo (horas)", fontsize=14)
            st.pyplot(fig)
            
            # Mostra a tabela com os dados
            st.dataframe(lead_time_df.set_index("Tipo"), use_container_width=True)
        else:
            st.warning("Nenhuma OS concluída disponível para cálculo de Lead Time")

# ... [restante das funções permanece exatamente como no original] ...

def main():
    # Inicializa arquivos e verifica consistência
    inicializar_arquivos()
    
    # Menu principal
    st.sidebar.title("Menu")
    opcao = st.sidebar.selectbox(
        "Selecione",
        [
            "🏠 Página Inicial",
            "📝 Cadastrar OS",
            "📋 Listar OS",
            "🔍 Buscar OS",
            "📊 Dashboard",
            "🔐 Supervisão"
        ]
    )

    # Navegação
    if opcao == "🏠 Página Inicial":
        pagina_inicial()
    elif opcao == "📝 Cadastrar OS":
        cadastrar_os()
    elif opcao == "📋 Listar OS":
        listar_os()
    elif opcao == "🔍 Buscar OS":
        buscar_os()
    elif opcao == "📊 Dashboard":
        dashboard()
    elif opcao == "🔐 Supervisão":
        pagina_supervisao()

    # Rodapé
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Sistema de Ordens de Serviço**")
    st.sidebar.markdown("Versão 4.0 com Múltiplos Executantes")
    st.sidebar.markdown("Desenvolvido por Robson Vilela")

if __name__ == "__main__":
    main()
