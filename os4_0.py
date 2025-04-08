import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import os
import shutil
import time
import glob
import base64
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

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
EXECUTANTES_PREDEFINIDOS = ["Robson", "Guilherme", "Paulinho", "Equipe Completa"]

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

# Funções auxiliares
def carregar_config():
    """Carrega as configurações do arquivo config.json"""
    global GITHUB_REPO, GITHUB_FILEPATH, GITHUB_TOKEN, EMAIL_CONFIG
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE) as f:
                config = json.load(f)
                GITHUB_REPO = config.get('github_repo')
                GITHUB_FILEPATH = config.get('github_filepath')
                GITHUB_TOKEN = config.get('github_token')
                
                # Carrega configurações de email se existirem
                if 'email_config' in config:
                    EMAIL_CONFIG.update(config['email_config'])
    except Exception as e:
        st.error(f"Erro ao carregar configurações: {str(e)}")

def formatar_executantes(executantes):
    """Formata a lista de executantes para exibição"""
    if not executantes or pd.isna(executantes):
        return ""
    if isinstance(executantes, str):
        if ";" in executantes:
            return " e ".join(executantes.split(";"))
        return executantes
    return ""

def inicializar_arquivos():
    """Garante que todos os arquivos necessários existam e estejam válidos"""
    # Criar diretório de backups se não existir
    os.makedirs(BACKUP_DIR, exist_ok=True)
    
    # Carregar configurações
    carregar_config()
    
    # Verificar se temos configuração do GitHub e se o módulo está disponível
    usar_github = GITHUB_AVAILABLE and GITHUB_REPO and GITHUB_FILEPATH and GITHUB_TOKEN
    
    # Inicializar arquivo de ordens de serviço
    if not os.path.exists(LOCAL_FILENAME) or os.path.getsize(LOCAL_FILENAME) == 0:
        if usar_github:
            baixar_do_github()
        else:
            pd.DataFrame(columns=["ID", "Descrição", "Data", "Solicitante", "Local", 
                                "Tipo", "Status", "Executante", "Data Conclusão"]).to_csv(LOCAL_FILENAME, index=False)

# [...] (mantenha todas as outras funções auxiliares como baixar_do_github, enviar_para_github, fazer_backup, etc.)

def carregar_csv():
    """Carrega os dados do CSV local"""
    try:
        df = pd.read_csv(LOCAL_FILENAME)
        # Garante que as colunas importantes são strings
        df["Executante"] = df["Executante"].astype(str)
        df["Data Conclusão"] = df["Data Conclusão"].astype(str)
        return df
    except Exception as e:
        st.error(f"Erro ao ler arquivo local: {str(e)}")
        # Tenta carregar do backup
        backup = carregar_ultimo_backup()
        if backup:
            try:
                df = pd.read_csv(backup)
                df.to_csv(LOCAL_FILENAME, index=False)  # Restaura o arquivo principal
                return df
            except:
                pass
        
        return pd.DataFrame(columns=["ID", "Descrição", "Data", "Solicitante", "Local", 
                                   "Tipo", "Status", "Executante", "Data Conclusão"])

def salvar_csv(df):
    """Salva o DataFrame no arquivo CSV local e faz backup"""
    try:
        # Garante que os campos importantes são strings
        df["Executante"] = df["Executante"].astype(str)
        df["Data Conclusão"] = df["Data Conclusão"].astype(str)
        
        df.to_csv(LOCAL_FILENAME, index=False)
        fazer_backup()
        
        # Se configurado, envia para o GitHub
        if GITHUB_AVAILABLE and GITHUB_REPO and GITHUB_FILEPATH and GITHUB_TOKEN:
            enviar_para_github()
            
        return True
    except Exception as e:
        st.error(f"Erro ao salvar dados: {str(e)}")
        return False

def atualizar_os():
    st.header("🔄 Atualizar Ordem de Serviço")
    df = carregar_csv()

    nao_concluidas = df[df["Status"] != "Concluído"]
    if nao_concluidas.empty:
        st.warning("Nenhuma OS pendente")
        return

    os_id = st.selectbox("Selecione a OS", nao_concluidas["ID"])
    os_data = df[df["ID"] == os_id].iloc[0]

    with st.form("atualizar_form"):
        st.write(f"**Descrição:** {os_data['Descrição']}")
        st.write(f"**Solicitante:** {os_data['Solicitante']}")
        st.write(f"**Local:** {os_data['Local']}")

        col1, col2 = st.columns(2)
        with col1:
            # Campo para selecionar o tipo de serviço
            tipo_atual = str(os_data["Tipo"]) if pd.notna(os_data["Tipo"]) else ""
            tipo = st.selectbox(
                "Tipo de Serviço",
                [""] + list(TIPOS_MANUTENCAO.values()),
                index=0 if tipo_atual == "" else list(TIPOS_MANUTENCAO.values()).index(tipo_atual)
            )

            novo_status = st.selectbox(
                "Status*",
                list(STATUS_OPCOES.values()),
                index=list(STATUS_OPCOES.values()).index(os_data["Status"])
            )

            # Verifica se o executante atual está na lista de pré-definidos
            executante_atual = str(os_data["Executante"]) if pd.notna(os_data["Executante"]) else ""
            
            # Separa os executantes se existir múltiplos
            if ";" in executante_atual:
                executantes_selecionados = executante_atual.split(";")
            else:
                executantes_selecionados = [executante_atual] if executante_atual else []
            
            # Widget para seleção múltipla
            executantes = st.multiselect(
                "Executante(s)* (máx 2)",
                EXECUTANTES_PREDEFINIDOS,
                default=executantes_selecionados,
                max_selections=2
            )

        with col2:
            if novo_status != "Pendente":
                data_atual = datetime.now().strftime("%d/%m/%Y")
                data_conclusao = st.text_input(
                    "Data de atualização",
                    value=data_atual if pd.isna(os_data['Data Conclusão']) or os_data['Status'] == "Pendente" else str(
                        os_data['Data Conclusão']),
                    disabled=novo_status != "Concluído"
                )
            else:
                data_conclusao = st.text_input(
                    "Data de conclusão (DD/MM/AAAA ou DDMMAAAA)",
                    value=str(os_data['Data Conclusão']) if pd.notna(os_data['Data Conclusão']) else "",
                    disabled=True
                )

        submitted = st.form_submit_button("Atualizar OS")

        if submitted:
            if novo_status in ["Em execução", "Concluído"] and not executantes:
                st.error("Selecione pelo menos um executante para este status!")
            elif novo_status == "Concluído" and not data_conclusao:
                st.error("Informe a data de conclusão!")
            elif len(executantes) > 2:
                st.error("Selecione no máximo dois executantes!")
            else:
                # Formata os executantes (separados por ;)
                executantes_str = ";".join(executantes) if executantes else ""
                
                # Atualiza todos os campos relevantes
                df.loc[df["ID"] == os_id, "Status"] = novo_status
                df.loc[df["ID"] == os_id, "Executante"] = executantes_str
                df.loc[df["ID"] == os_id, "Tipo"] = tipo
                
                if novo_status == "Concluído":
                    df.loc[df["ID"] == os_id, "Data Conclusão"] = data_conclusao
                
                if salvar_csv(df):
                    st.success("OS atualizada com sucesso! Backup automático realizado.")
                    time.sleep(1)
                    st.rerun()

def listar_os():
    st.header("📋 Listagem Completa de OS")
    df = carregar_csv()

    if df.empty:
        st.warning("Nenhuma ordem de serviço cadastrada ainda.")
    else:
        # Cria uma cópia para exibição formatada
        df_display = df.copy()
        df_display['Executante'] = df_display['Executante'].apply(formatar_executantes)
        
        with st.expander("Filtrar OS"):
            col1, col2 = st.columns(2)
            with col1:
                filtro_status = st.selectbox("Status", ["Todos"] + list(STATUS_OPCOES.values()))
            with col2:
                filtro_tipo = st.selectbox("Tipo de Manutenção", ["Todos"] + list(TIPOS_MANUTENCAO.values()))

        if filtro_status != "Todos":
            df_display = df_display[df_display["Status"] == filtro_status]
        if filtro_tipo != "Todos":
            df_display = df_display[df_display["Tipo"] == filtro_tipo]

        st.dataframe(df_display, use_container_width=True)

# [...] (mantenha todas as outras funções como buscar_os, dashboard, etc.)

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
