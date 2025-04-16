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
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def carregar_imagem(caminho_arquivo):
    with open(caminho_arquivo, "rb") as f:
        dados = f.read()
        encoded = base64.b64encode(dados).decode()
    return f"data:image/png;base64,{encoded}"

# Configurações da página
st.set_page_config(
    page_title="Sistema de Ordens de Serviço 4.0",
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
EMAIL_CONFIG_FILE = "email_config.json"

# Executantes pré-definidos
EXECUTANTES_PREDEFINIDOS = ["Robson", "Guilherme", "Paulinho"]

# Variáveis globais para configuração do GitHub
GITHUB_REPO = None
GITHUB_FILEPATH = None
GITHUB_TOKEN = None

# Variáveis globais para configuração de email
EMAIL_SENDER = None
EMAIL_PASSWORD = None
EMAIL_RECEIVER = "vilela.industria@gmail.com"

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

def carregar_config():
    """Carrega as configurações do GitHub e email dos arquivos de configuração"""
    global GITHUB_REPO, GITHUB_FILEPATH, GITHUB_TOKEN, EMAIL_SENDER, EMAIL_PASSWORD
    
    # Carrega configurações do GitHub
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE) as f:
                config = json.load(f)
                GITHUB_REPO = config.get('github_repo')
                GITHUB_FILEPATH = config.get('github_filepath')
                GITHUB_TOKEN = config.get('github_token')
    except Exception as e:
        st.error(f"Erro ao carregar configurações do GitHub: {str(e)}")
    
    # Carrega configurações de email
    try:
        if os.path.exists(EMAIL_CONFIG_FILE):
            with open(EMAIL_CONFIG_FILE) as f:
                email_config = json.load(f)
                EMAIL_SENDER = email_config.get('email_sender')
                EMAIL_PASSWORD = email_config.get('email_password')
    except Exception as e:
        st.error(f"Erro ao carregar configurações de email: {str(e)}")

def enviar_email_notificacao(os_id, descricao, solicitante, local, urgente):
    """Envia email de notificação quando uma nova OS é aberta"""
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        st.error("Configurações de email não encontradas. Notificação não enviada.")
        return False
    
    try:
        # Configuração do email
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECEIVER
        msg['Subject'] = f"[OS {os_id}] Nova Ordem de Serviço Aberta - {'URGENTE' if urgente else 'Normal'}"
        
        # Corpo do email
        body = f"""
        <h2>Nova Ordem de Serviço Aberta</h2>
        <p><strong>ID:</strong> {os_id}</p>
        <p><strong>Descrição:</strong> {descricao}</p>
        <p><strong>Solicitante:</strong> {solicitante}</p>
        <p><strong>Local:</strong> {local}</p>
        <p><strong>Urgente:</strong> {'Sim' if urgente else 'Não'}</p>
        <p><strong>Data/Hora:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
        <br>
        <p>Acesse o sistema para mais detalhes.</p>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        # Conexão com o servidor SMTP do Gmail
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
            smtp.send_message(msg)
        
        return True
    except Exception as e:
        st.error(f"Erro ao enviar email de notificação: {str(e)}")
        return False

def converter_arquivo_antigo(df):
    """Converte o formato antigo (com 'Executante') para o novo (com 'Executante1' e 'Executante2')"""
    if 'Executante' in df.columns and 'Executante1' not in df.columns:
        df['Executante1'] = df['Executante']
        df['Executante2'] = ""
        df['Observações'] = ""  # Adiciona coluna de observações se não existir
        df.drop('Executante', axis=1, inplace=True)
    if 'Observações' not in df.columns:  # Garante que a coluna existe
        df['Observações'] = ""
    return df

def inicializar_arquivos():
    """Garante que todos os arquivos necessários existam e estejam válidos"""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    carregar_config()
    
    usar_github = GITHUB_AVAILABLE and GITHUB_REPO and GITHUB_FILEPATH and GITHUB_TOKEN
    
    if not os.path.exists(LOCAL_FILENAME) or os.path.getsize(LOCAL_FILENAME) == 0:
        if usar_github:
            baixar_do_github()
        else:
            df = pd.DataFrame(columns=["ID", "Descrição", "Data", "Hora Abertura", "Solicitante", "Local", 
                                     "Tipo", "Status", "Data Conclusão", "Hora Conclusão", "Executante1", "Executante2", "Urgente", "Observações"])
            df.to_csv(LOCAL_FILENAME, index=False)



def cadastrar_os():
    st.header("📝 Cadastrar Nova Ordem de Serviço")
    with st.form("cadastro_os_form", clear_on_submit=True):
        descricao = st.text_area("Descrição da atividade*")
        solicitante = st.text_input("Solicitante*")
        local = st.text_input("Local*")
        urgente = st.checkbox("Urgente")

        submitted = st.form_submit_button("Cadastrar OS")
        if submitted:
            if not descricao or not solicitante or not local:
                st.error("Preencha todos os campos obrigatórios (*)")
            else:
                df = carregar_csv()
                novo_id = int(df["ID"].max()) + 1 if not df.empty and not pd.isna(df["ID"].max()) else 1
                data_hora_utc = datetime.utcnow()
                data_hora_local = data_hora_utc - timedelta(hours=3)
                data_abertura = data_hora_local.strftime("%d/%m/%Y")
                hora_abertura = data_hora_local.strftime("%H:%M")
                
                nova_os = pd.DataFrame([{
                    "ID": novo_id,
                    "Descrição": descricao,
                    "Data": data_abertura,
                    "Hora Abertura": hora_abertura,
                    "Solicitante": solicitante,
                    "Local": local,
                    "Tipo": "",
                    "Status": "Pendente",
                    "Data Conclusão": "",
                    "Hora Conclusão": "",
                    "Executante1": "",
                    "Executante2": "",
                    "Urgente": "Sim" if urgente else "Não",
                    "Observações": ""
                }])

                df = pd.concat([df, nova_os], ignore_index=True)
                if salvar_csv(df):
                    # Envia email de notificação
                    if enviar_email_notificacao(novo_id, descricao, solicitante, local, urgente):
                        st.success("Ordem cadastrada com sucesso! Notificação enviada por email.")
                    else:
                        st.success("Ordem cadastrada com sucesso! (Falha no envio da notificação por email)")
                    
                    time.sleep(1)
                    st.rerun()


def configurar_github():
    st.header("⚙️ Configuração do GitHub e Email")
    global GITHUB_REPO, GITHUB_FILEPATH, GITHUB_TOKEN, EMAIL_SENDER, EMAIL_PASSWORD
    
    if not GITHUB_AVAILABLE:
        st.error("""Funcionalidade do GitHub não está disponível. 
                Para ativar, instale o pacote PyGithub com: 
                `pip install PyGithub`""")
    
    tab1, tab2 = st.tabs(["GitHub", "Email"])
    
    with tab1:
        with st.form("github_config_form"):
            repo = st.text_input("Repositório GitHub (user/repo)", value=GITHUB_REPO or "vilelarobson0971/OS_4.0")
            filepath = st.text_input("Caminho do arquivo no repositório", value=GITHUB_FILEPATH or "ordens_servico4.0.csv")
            token = st.text_input("Token de acesso GitHub", type="password", value=GITHUB_TOKEN or "")
            
            submitted = st.form_submit_button("Salvar Configurações GitHub")
            
            if submitted:
                if repo and filepath and token:
                    try:
                        g = Github(token)
                        g.get_repo(repo).get_contents(filepath)
                        
                        config = {
                            'github_repo': repo,
                            'github_filepath': filepath,
                            'github_token': token
                        }
                        
                        with open(CONFIG_FILE, 'w') as f:
                            json.dump(config, f)
                        
                        GITHUB_REPO = repo
                        GITHUB_FILEPATH = filepath
                        GITHUB_TOKEN = token
                        
                        st.success("Configurações do GitHub salvas e validadas com sucesso!")
                        
                        if baixar_do_github():
                            st.success("Dados sincronizados do GitHub!")
                        else:
                            st.warning("Configurações salvas, mas não foi possível sincronizar com o GitHub")
                            
                    except Exception as e:
                        st.error(f"Credenciais inválidas ou sem permissão: {str(e)}")
                else:
                    st.error("Preencha todos os campos para ativar a sincronização com GitHub")
    
    with tab2:
        st.info("Configure o email que enviará as notificações (usará SMTP do Gmail)")
        with st.form("email_config_form"):
            email_sender = st.text_input("Email remetente (Gmail)", value=EMAIL_SENDER or "")
            email_password = st.text_input("Senha do email (ou senha de app)", type="password", value=EMAIL_PASSWORD or "")
            
            submitted = st.form_submit_button("Salvar Configurações de Email")
            
            if submitted:
                if email_sender and email_password:
                    try:
                        # Testa a conexão com o servidor SMTP
                        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                            smtp.login(email_sender, email_password)
                        
                        email_config = {
                            'email_sender': email_sender,
                            'email_password': email_password
                        }
                        
                        with open(EMAIL_CONFIG_FILE, 'w') as f:
                            json.dump(email_config, f)
                        
                        EMAIL_SENDER = email_sender
                        EMAIL_PASSWORD = email_password
                        
                        st.success("Configurações de email salvas e validadas com sucesso!")
                        
                        # Envia email de teste
                        try:
                            msg = MIMEMultipart()
                            msg['From'] = email_sender
                            msg['To'] = EMAIL_RECEIVER
                            msg['Subject'] = "Teste de Notificação - Sistema OS 4.0"
                            msg.attach(MIMEText("Este é um email de teste para verificar a configuração do sistema de notificação.", 'plain'))
                            
                            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                                smtp.login(email_sender, email_password)
                                smtp.send_message(msg)
                            
                            st.success("Email de teste enviado com sucesso para vilela.industria@gmail.com!")
                        except Exception as e:
                            st.error(f"Email de teste não pôde ser enviado: {str(e)}")
                            
                    except Exception as e:
                        st.error(f"Credenciais de email inválidas: {str(e)}")
                else:
                    st.error("Preencha todos os campos para ativar as notificações por email")

def converter_arquivo_antigo(df):
    """Converte o formato antigo (com 'Executante') para o novo (com 'Executante1' e 'Executante2')"""
    if 'Executante' in df.columns and 'Executante1' not in df.columns:
        df['Executante1'] = df['Executante']
        df['Executante2'] = ""
        df['Observações'] = ""  # Adiciona coluna de observações se não existir
        df.drop('Executante', axis=1, inplace=True)
    if 'Observações' not in df.columns:  # Garante que a coluna existe
        df['Observações'] = ""
    return df

def inicializar_arquivos():
    """Garante que todos os arquivos necessários existam e estejam válidos"""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    carregar_config()
    
    usar_github = GITHUB_AVAILABLE and GITHUB_REPO and GITHUB_FILEPATH and GITHUB_TOKEN
    
    if not os.path.exists(LOCAL_FILENAME) or os.path.getsize(LOCAL_FILENAME) == 0:
        if usar_github:
            baixar_do_github()
        else:
            df = pd.DataFrame(columns=["ID", "Descrição", "Data", "Hora Abertura", "Solicitante", "Local", 
                                     "Tipo", "Status", "Data Conclusão", "Hora Conclusão", "Executante1", "Executante2", "Urgente", "Observações"])
            df.to_csv(LOCAL_FILENAME, index=False)

[... continue com todo o restante do código original ...]

def main():
    if 'notificacoes_limpas' not in st.session_state:
        st.session_state.notificacoes_limpas = False
        
    inicializar_arquivos()
    
    # Adiciona o JavaScript para recarregar a página a cada 10 minutos (600000 milissegundos)
    st.markdown("""
    <script>
    function checkReload() {
        // Verifica se estamos na página principal (não na área de supervisão)
        if (!window.location.href.includes('Supervis%C3%A3o')) {
            setTimeout(function() {
                window.location.reload();
            }, 600000); // 10 minutos = 600000 ms
        }
    }
    window.onload = checkReload;
    </script>
    """, unsafe_allow_html=True)
    
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

    st.sidebar.markdown("---")
    st.sidebar.markdown("**Sistema de Ordens de Serviço 4.0**")
    st.sidebar.markdown("Versão 2.5 com Múltiplos Executantes")
    st.sidebar.markdown("Desenvolvido por Robson Vilela")

if __name__ == "__main__":
    main()

