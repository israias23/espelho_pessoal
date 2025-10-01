from flask import Flask, redirect, url_for
from apscheduler.schedulers.background import BackgroundScheduler
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_change_this'
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
  # Use credenciais da plataforma
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# VAPID keys for web push (generate with pywebpush.generate_vapid_keys())
app.config['VAPID_PRIVATE_KEY'] = 'your_vapid_private_key_here'  # Substitua
app.config['VAPID_PUBLIC_KEY'] = 'your_vapid_public_key_here'    # Substitua
app.config['VAPID_CLAIMS'] = {"sub": "mailto:pontopessoal128@gmail.com"}

# Import and register blueprints
from auth import auth_bp, init_auth
from records import records_bp
app.register_blueprint(auth_bp)
app.register_blueprint(records_bp)

init_auth(app)  # Initialize login_manager

# Initialize SQLAlchemy with the app
from models import db
db.init_app(app)
with app.app_context():
    db.create_all()


# Scheduler for monthly reports and daily reminders
scheduler = BackgroundScheduler()
scheduler.start()

# Nova rota para o root URL (/) - redireciona para login
@app.route('/')
def root():
    return redirect(url_for('auth.login'))  # Ou 'records.dashboard' se preferir redirecionar para dashboard após login

if __name__ == '__main__':
    app.run(debug=True)
