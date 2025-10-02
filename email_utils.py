import requests

def send_email_resend(to, subject, body):
    api_key = 're_BREyAp2F_8LA1ZVmYKWs8EK6hkyzmBqPk'  # coloque via variável de ambiente em produção!
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    data = {
        "from": "Espelho Pessoal <noreply@espelho.app>",
        "to": [to],
        "subject": subject,
        "html": f"<p>{body}</p>"
    }

    response = requests.post("https://api.resend.com/emails", json=data, headers=headers)

    # Resend retorna 202 quando o envio foi aceito
    if response.status_code == 202:
        return True
    else:
        print("Erro ao enviar email:", response.status_code, response.text)
        return False
