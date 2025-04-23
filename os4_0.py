import streamlit as st
import pywhatkit as pwk
import time

# Configuração da página do Streamlit
st.set_page_config(
    page_title="Enviador de Mensagens WhatsApp",
    page_icon="📱",
    layout="centered"
)

# Título da aplicação
st.title("📱 Enviar Mensagem pelo WhatsApp")

# Entrada de dados do usuário
with st.form("whatsapp_form"):
    phone_number = st.text_input("Número de telefone (com código do país):", placeholder="Ex: +5543991492882")
    message = st.text_area("Mensagem:", placeholder="Digite sua mensagem aqui...")
    hour = st.number_input("Hora (0-23):", min_value=0, max_value=23, value=0)
    minute = st.number_input("Minuto (0-59):", min_value=0, max_value=59, value=0)
    
    submit_button = st.form_submit_button("Agendar Envio")

# Quando o formulário é submetido
if submit_button:
    if not phone_number or not message:
        st.warning("Por favor, preencha todos os campos!")
    else:
        try:
            # Envia a mensagem
            pwk.sendwhatmsg(phone_number, message, hour, minute)
            
            # Mostra mensagem de sucesso
            st.success(f"Mensagem agendada para {hour:02d}:{minute:02d}!")
            st.balloons()
            
            # Adiciona um pequeno delay e abre o WhatsApp Web
            time.sleep(10)
            pwk.open_web()
            
        except Exception as e:
            st.error(f"Ocorreu um erro: {e}")
            st.info("Certifique-se de que: \n1. O número está no formato correto \n2. Você está logado no WhatsApp Web \n3. O horário é futuro")

# Rodapé
st.markdown("---")
st.markdown("ℹ️ Este aplicativo requer que você esteja logado no WhatsApp Web.")
st.markdown("⚠️ O número deve incluir o código do país (ex: +55 para Brasil).")
