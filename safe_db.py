# safe_db.py
from models import db, User
import logging

# Configura o log para registrar erros
logging.basicConfig(level=logging.ERROR)

def get_user_by_id(user_id):
    try:
        return User.query.get(user_id)
    except Exception as e:
        logging.error(f"Erro ao buscar usuário por ID ({user_id}): {e}")
        return None

def get_user_by_email(email):
    try:
        return User.query.filter_by(email=email).first()
    except Exception as e:
        logging.error(f"Erro ao buscar usuário por email ({email}): {e}")
        return None

def delete_user(user):
    try:
        db.session.delete(user)
        db.session.commit()
        return True
    except Exception as e:
        logging.error(f"Erro ao deletar usuário ({user.id}): {e}")
        db.session.rollback()
        return False

def update_user_password(user, new_password_hash):
    try:
        user.password = new_password_hash
        db.session.commit()
        return True
    except Exception as e:
        logging.error(f"Erro ao atualizar senha do usuário ({user.id}): {e}")
        db.session.rollback()
        return False

def update_user_profile(user, email=None, password_hash=None, photo_path=None):
    try:
        if email:
            user.email = email
        if password_hash:
            user.password = password_hash
        if photo_path:
            user.profile_photo = photo_path
        db.session.commit()
        return True
    except Exception as e:
        logging.error(f"Erro ao atualizar perfil do usuário ({user.id}): {e}")
        db.session.rollback()
        return False

def save_push_subscription(user, subscription_json):
    try:
        user.push_subscription = subscription_json
        db.session.commit()
        return True
    except Exception as e:
        logging.error(f"Erro ao salvar push subscription ({user.id}): {e}")
        db.session.rollback()
        return False
