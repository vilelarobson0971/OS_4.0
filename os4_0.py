import streamlit as st
import pywhatkit as kit
import datetime
import time

st.set_page_config(page_title="Envio WhatsApp com Python", layout="centered")

st.title("📱 Envio de Mensagem via WhatsApp")
st.markdown("Use o formulário abaixo para agendar o envio de uma mensagem no WhatsApp.")

numero = st.text_input("Número com DDI e DDD (Ex: +5543991492882)")
mensagem = st.text_area("Mensagem")
hora = st.number_input("Hora de envio (24h)", min_value=0, max_value=23, value=datetime.datetime.now().hour)
minuto = st.number_input("Minuto de envio", min_value=0, max_value=59, value=(datetime.datetime.now().minute + 2) % 60)

enviar = st.button("Agendar Envio")

if enviar:
    if numero and mensagem:
        try:
            st.success(f"Mensagem será enviada para {numero} às {hora:02d}:{minuto:02d}")
            kit.sendwhatmsg(numero, mensagem, hora, minuto)
        except Exception as e:
            st.error(f"Erro ao tentar enviar: {e}")
    else:
        st.warning("Preencha todos os campos.")
