# auth.py (mantido como está, sem alterações necessárias para o erro atual)
from flask import Blueprint, request, render_template, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from models import db, User
from datetime import datetime, timedelta, timezone
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import os
import uuid
import json
from pywebpush import webpush, WebPushException
from flask import current_app as app
from safe_db import get_user_by_id

user = get_user_by_id(user_id)
if not user:
    flash('Erro interno ao buscar usuário.', 'error')
    return redirect(url_for('auth.login'))


auth_bp = Blueprint('auth', __name__)

login_manager = LoginManager()
login_manager.login_view = 'auth.login'

def init_auth(flask_app):
    login_manager.init_app(flask_app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def send_email(to, subject, body, attachment_path=None):
    from_email = 'pontopessoal128@gmail.com'
    password = 'anmo cdis mims skfa'
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    if attachment_path:
        with open(attachment_path, 'rb') as f:
            part = MIMEApplication(f.read(), Name=os.path.basename(attachment_path))
        part['Content-Disposition'] = f'attachment; filename="{os.path.basename(attachment_path)}"'
        msg.attach(part)
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(from_email, password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        company = request.form.get('company')
        if not all([name, email, password, company]):
            flash('Todos os campos são obrigatórios.', 'error')
            return render_template('register.html')
        if len(password) < 8:
            flash('Senha deve conter mais de 8 caracteres', 'error')
            return render_template('register.html')
        hashed_pw = generate_password_hash(password)
        user = User(name=name, email=email, password=hashed_pw, company=company)
        db.session.add(user)
        db.session.commit()
        flash('Cadastro efetuado! Acesse a conta.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Conectado!', 'success')
            return redirect(url_for('records.dashboard'))
        flash('Email ou senha não confere!.', 'error')
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Desconectado.', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            code = str(random.randint(100000, 999999))
            session['reset_code'] = code
            session['reset_email'] = email
            session['reset_time'] = datetime.now(timezone.utc)
            if send_email(email, 'Código de Redefinição de Senha', f'Seu código de redefinição é: {code} (expira em 10 minuots)'):
                flash('Código de redefinição enviado para o seu e-mail.', 'success')
            else:
                flash('Falha ao enviar para email. Entre em contato com suporte.', 'error')
            return redirect(url_for('auth.reset_password'))
        flash('Email não encontrado.', 'error')
    return render_template('forgot_password.html')

@auth_bp.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        code = request.form.get('code')
        new_password = request.form.get('password')
        if 'reset_code' in session and code == session['reset_code']:
            if datetime.now(timezone.utc) - session['reset_time'] > timedelta(minutes=10):
                flash('Código expirado! Solicite outro.', 'error')
                return redirect(url_for('auth.forgot_password'))
            email = session['reset_email']
            user = User.query.filter_by(email=email).first()
            user.password = generate_password_hash(new_password)
            db.session.commit()
            session.pop('reset_code', None)
            session.pop('reset_email', None)
            session.pop('reset_time', None)
            flash('Senha atulaizada!', 'success')
            return redirect(url_for('auth.login'))
        flash('Código inválido.', 'error')
    return render_template('reset_password.html')

@auth_bp.route('/update_profile', methods=['GET', 'POST'])
@login_required
def update_profile():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        photo = request.files.get('profile_photo')
        if email:
            current_user.email = email
        if password:
            current_user.password = generate_password_hash(password)
        if photo:
            filename = f"profile_{uuid.uuid4()}.jpg"
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            photo.save(path)
            current_user.profile_photo = path
        db.session.commit()
        flash('Seus dados foram salvos!', 'success')
        return redirect(url_for('records.dashboard'))
    return render_template('update_profile.html')

@auth_bp.route('/delete_account', methods=['GET', 'POST'])
@login_required
def delete_account():
    if request.method == 'POST':
        code = request.form.get('code')
        if 'delete_code' in session and code == session['delete_code']:
            if datetime.now(timezone.utc) - session['delete_time'] > timedelta(minutes=10):
                flash('Código expirado! Solicite outro.', 'error')
                return render_template('delete_account.html')
            send_email(current_user.email, 'Confirmação de Exclusão de Conta', 'Sua conta foi deletada.')
            db.session.delete(current_user)
            db.session.commit()
            logout_user()
            session.clear()
            flash('Sua conta foi deletada.', 'success')
            return redirect(url_for('auth.login'))
        flash('Invalid code.', 'error')
    else:
        code = str(random.randint(100000, 999999))
        session['delete_code'] = code
        session['delete_time'] = datetime.now(timezone.utc)
        if send_email(current_user.email, 'Código de Exclusão de Conta', f'Seu código de exclusão é: {code} (expira em 10 minutos)'):
            flash('Código de exclusão enviado para o seu e-mail.', 'success')
        else:
            flash('Falha ao enviar email.', 'error')
    return render_template('delete_account.html')

@auth_bp.route('/subscribe_push', methods=['POST'])
@login_required
def subscribe_push():
    subscription = request.json
    current_user.push_subscription = json.dumps(subscription)
    db.session.commit()
    return jsonify({'success': True})

def send_push_notification(user, title, body):
    if user.push_subscription:
        subscription = json.loads(user.push_subscription)
        try:
            webpush(
                subscription_info=subscription,
                data=json.dumps({'title': title, 'body': body}),
                vapid_private_key=app.config['VAPID_PRIVATE_KEY'],
                vapid_claims=app.config['VAPID_CLAIMS']
            )
        except WebPushException as e:
            print(f"Push error: {e}")
