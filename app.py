import os
from flask import Flask, render_template, request, jsonify
import mercadopago
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

# 1. CARREGAR CONFIGURAÇÕES ESCONDIDAS
load_dotenv()

ACCESS_TOKEN = os.getenv("MERCADOPAGO_TOKEN")
SDK = mercadopago.SDK(ACCESS_TOKEN)

app = Flask(__name__)

# 2. FUNÇÃO DE ENVIO AUTOMÁTICO DE E-MAIL
def enviar_email(destino):
    link_do_drive = "https://drive.google.com/drive/folders/1g6CsxamS8IC4YmmFYmTyzOIzLAYG1c2C?usp=drive_link"
    
    msg = EmailMessage()
    msg['Subject'] = "Acesso Liberado! Pack de Vídeos Premium"
    msg['From'] = "easypackvideo@gmail.com"
    msg['To'] = destino
    
    corpo = f"""
    Olá!
    
    Parabéns, seu pagamento foi confirmado com sucesso! 
    Aqui está o seu acesso exclusivo ao Pack de Vídeos Premium:
    
    {link_do_drive}
    
    Dúvidas? Basta responder a este e-mail.
    Equipe Easy Pack Video.
    """
    msg.set_content(corpo)
    
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        senha_email = os.getenv("EMAIL_PASSWORD")
        smtp.login('easypackvideo@gmail.com', senha_email)
        smtp.send_message(msg)

# 3. ROTAS DO SITE
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/comprar', methods=['POST'])
def comprar():
    email_cliente = request.form.get('email')
    
    payment_data = {
        "transaction_amount": 19.90,
        "description": "Pack de Vídeos Premium",
        "payment_method_id": "pix",
        "payer": {"email": email_cliente, "first_name": "Cliente", "last_name": "Premium"}
    }
    
    try:
        response = SDK.payment().create(payment_data)
        payment = response["response"]
        
        if "point_of_interaction" in payment:
            data = payment["point_of_interaction"]["transaction_data"]
            payment_id = payment["id"] # Pega o ID do pagamento gerado
            return render_template('pix.html', 
                                   qr_code_base64=data["qr_code_base64"], 
                                   copia_cola=data["qr_code"],
                                   payment_id=payment_id) # Envia o ID para a página
        return f"Erro ao processar pagamento: {payment}"
    except Exception as e:
        return f"Erro fatal no servidor: {str(e)}"

# ROTA NOVA: Verifica se o PIX foi pago para atualizar a tela do cliente
@app.route('/status/<payment_id>', methods=['GET'])
def verificar_status(payment_id):
    try:
        payment_info = SDK.payment().get(payment_id)
        status = payment_info['response']['status']
        return jsonify({'status': status})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# 4. WEBHOOK (Ouvinte do Mercado Pago para disparar o e-mail)
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if data.get('type') == 'payment':
        payment_id = data['data']['id']
        payment_info = SDK.get(payment_id) if hasattr(SDK, 'get') else SDK.payment().get(payment_id)
        
        if payment_info['response']['status'] == 'approved':
            email = payment_info['response']['payer']['email']
            enviar_email(email)
            print(f"Pagamento aprovado. E-mail enviado para: {email}")
            
    return '', 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)