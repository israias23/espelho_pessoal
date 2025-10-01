import requests
import resend

def send_email_resend(to, subject, body):
    api_key = 're_BREyAp2F_8LA1ZVmYKWs8EK6hkyzmBqPk'  # substitua pela sua chave
    headers = {
        'Authorization': f'Bearer ' + api_key,
        'Content-Type': 'application/json'
    }
    data = {
        "from": "Espelho Pessoal <noreply@espelho.app>",
        "to": [to],
        "subject": subject,
        "html": f"<p>{body}</p>"
    }
    response = requests.post("https://api.resend.com/emails", json=data, headers=headers)
    return response.status_code == 200
