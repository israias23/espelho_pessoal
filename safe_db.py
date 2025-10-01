# safe_db.py
from models import db, User
import logging

def get_user_by_id(user_id):
    try:
        return User.query.get(user_id)
    except Exception as e:
        logging.error(f"Erro ao buscar usuário {user_id}: {e}")
        return None

def delete_user(user):
    try:
        db.session.delete(user)
        db.session.commit()
        return True
    except Exception as e:
        logging.error(f"Erro ao deletar usuário: {e}")
        db.session.rollback()
        return False
