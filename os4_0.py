import pywhatkit as kit
import datetime

print('Teste de envio de notificações')
# Número do WhatsApp com código do país (Ex: Brasil é +55)
numero = "+5543991492882"  # Substitua pelo número desejado
mensagem = "Olá! Esta é uma mensagem automática enviada pelo Python 😄"

# Horário para envio (formato 24h, com no mínimo 1-2 minutos de antecedência)
hora = datetime.datetime.now().hour
minuto = datetime.datetime.now().minute + 2  # Enviar em 2 minutos

# Enviar mensagem
kit.sendwhatmsg(numero, mensagem, hora, minuto)
