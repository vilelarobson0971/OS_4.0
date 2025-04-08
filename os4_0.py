import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

def enviar_backup_email(destinatario):
    """Envia o arquivo atual como anexo por email"""
    try:
        # Configurações do servidor SMTP (exemplo para Gmail)
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        email_remetente = "seuemail@gmail.com"
        senha = "sua_senha_app"  # Use senha de app para Gmail

        # Criar mensagem
        msg = MIMEMultipart()
        msg['From'] = email_remetente
        msg['To'] = destinatario
        msg['Subject'] = f"Backup Ordens de Serviço - {datetime.now().strftime('%d/%m/%Y %H:%M')}"

        # Corpo do email
        body = "Backup automático do sistema de ordens de serviço em anexo."
        msg.attach(MIMEText(body, 'plain'))

        # Anexar arquivo
        filename = LOCAL_FILENAME
        attachment = open(filename, "rb")

        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename= {filename}")
        msg.attach(part)

        # Enviar email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(email_remetente, senha)
        server.sendmail(email_remetente, destinatario, msg.as_string())
        server.quit()
        
        return True
    except Exception as e:
        st.error(f"Erro ao enviar email: {str(e)}")
        return False
