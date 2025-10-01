from flask import Blueprint, request, render_template, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from models import db, User
from datetime import datetime, timedelta, timezone
import random
import os
import uuid
import json
from pywebpush import webpush, WebPushException
from flask import current_app as app
from safe_db import (
    get_user_by_id,
    get_user_by_email,
    delete_user,
    update_user_password,
    update_user_profile,
    save_push_subscription
)
from email_utils import send_email_resend

auth_bp = Blueprint('auth', __name__)
login_manager = LoginManager()
login_manager.login_view = 'auth.login'

def init_auth(flask_app):
    login_manager.init_app(flask_app)

@login_manager.user_loader
def load_user(user_id):
    return get_user_by_id(user_id)

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
        try:
            db.session.add(user)
            db.session.commit()
            flash('Cadastro efetuado! Acesse a conta.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash('Erro ao registrar usuário.', 'error')
    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = get_user_by_email(email)
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
        user = get_user_by_email(email)
        if user:
            code = str(random.randint(100000, 999999))
            session['reset_code'] = code
            session['reset_email'] = email
            session['reset_time'] = datetime.now(timezone.utc)
            if send_email_resend(email, 'Código de Redefinição de Senha', f'Seu código é: {code} (expira em 10 minutos)'):
                flash('Código enviado para seu e-mail.', 'success')
            else:
                flash('Erro ao enviar e-mail. Tente novamente mais tarde.', 'error')
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
            user = get_user_by_email(email)
            hashed_pw = generate_password_hash(new_password)
            if update_user_password(user, hashed_pw):
                session.pop('reset_code', None)
                session.pop('reset_email', None)
                session.pop('reset_time', None)
                flash('Senha atualizada!', 'success')
                return redirect(url_for('auth.login'))
            else:
                flash('Erro ao atualizar senha.', 'error')
        else:
            flash('Código inválido.', 'error')
    return render_template('reset_password.html')

@auth_bp.route('/update_profile', methods=['GET', 'POST'])
@login_required
def update_profile():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        photo = request.files.get('profile_photo')
        hashed_pw = generate_password_hash(password) if password else None
        photo_path = None
        if photo:
            filename = f"profile_{uuid.uuid4()}.jpg"
            photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            photo.save(photo_path)
        if update_user_profile(current_user, email=email, password_hash=hashed_pw, photo_path=photo_path):
            flash('Seus dados foram salvos!', 'success')
        else:
            flash('Erro ao atualizar perfil.', 'error')
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
            send_email_resend(current_user.email, 'Confirmação de Exclusão de Conta', 'Sua conta foi deletada.')
            if delete_user(current_user):
                logout_user()
                session.clear()
                flash('Sua conta foi deletada.', 'success')
                return redirect(url_for('auth.login'))
            else:
                flash('Erro ao excluir conta.', 'error')
        else:
            flash('Código inválido.', 'error')
    else:
        code = str(random.randint(100000, 999999))
        session['delete_code'] = code
        session['delete_time'] = datetime.now(timezone.utc)
        if send_email_resend(current_user.email, 'Código de Exclusão de Conta', f'Seu código é: {code} (expira em 10 minutos)'):
            flash('Código enviado para seu e-mail.', 'success')
        else:
            flash('Erro ao enviar e-mail.', 'error')
    return render_template('delete_account.html')

@auth_bp.route('/subscribe_push', methods=['POST'])
@login_required
def subscribe_push():
    subscription = request.json
    subscription_json = json.dumps(subscription)
    if save_push_subscription(current_user, subscription_json):
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Erro ao salvar push subscription'}), 500

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

send_email = send_email_resend #compatibilidade com outros módulos

