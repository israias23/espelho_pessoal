from flask import Blueprint, request, render_template, redirect, url_for, flash, send_file
from flask_login import login_required, current_user
from models import db, Record, User
from datetime import datetime, timedelta
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import openpyxl
from flask_paginate import Pagination, get_page_args
from collections import defaultdict
from auth import send_email_resend as send_email, send_push_notification
from flask import current_app as app
from cloudinary_utils import upload_image_to_cloudinary
import requests
from tempfile import NamedTemporaryFile

records_bp = Blueprint('records', __name__)

def send_monthly_report():
    with app.app_context():
        for user in User.query.all():
            now = datetime.now()
            start_of_month = now.replace(day=1).strftime('%Y-%m-%d')
            records = Record.query.filter_by(user_id=user.id).filter(Record.date >= start_of_month).all()
            if not records:
                continue
            temp_pdf = f'temp_report_{user.id}.pdf'
            generate_professional_pdf(temp_pdf, records, user.name, user.company, now.strftime('%B %Y'))
            send_email(user.email, 'Relatório Mensal de Horas', 'Seu relatório mensal está anexado.', temp_pdf)
            os.remove(temp_pdf)

def daily_reminder():
    with app.app_context():
        for user in User.query.all():
            send_push_notification(user, 'Lembrete do Espelho de ponto pessoal', "Não se esqueça de registrar sua entrada hoje!")

def calculate_hours(records):
    daily_hours = defaultdict(timedelta)
    daily_data = defaultdict(list)
    for rec in records:
        daily_data[rec.date].append(rec)
    for date, day_records in daily_data.items():
        day_records.sort(key=lambda r: datetime.strptime(r.time, '%H:%M:%S'))
        entries = [r for r in day_records if r.type == 'Entrada']
        exits = [r for r in day_records if r.type == 'Saída']
        total_breaks = sum(r.break_duration for r in day_records) / 60.0
        min_pairs = min(len(entries), len(exits))
        for i in range(min_pairs):
            entry_time = datetime.strptime(f"{date} {entries[i].time}", '%Y-%m-%d %H:%M:%S')
            exit_time = datetime.strptime(f"{date} {exits[i].time}", '%Y-%m-%d %H:%M:%S')
            daily_hours[date] += (exit_time - entry_time)
        daily_hours[date] -= timedelta(hours=total_breaks)
    return {date: hours.total_seconds() / 3600 for date, hours in daily_hours.items()}

def generate_professional_pdf(filename, records, user_name, company, month_year=None):
    doc = SimpleDocTemplate(filename, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    title_text = f"Registros de pontos de {user_name} em {company}"
    if month_year:
        title_text += f" ({month_year})"
    elements.append(Paragraph(title_text, styles['Title']))
    elements.append(Paragraph("", styles['Normal']))
    daily_data = defaultdict(list)
    daily_hours = calculate_hours(records)
    for rec in records:
        daily_data[rec.date].append(rec)
    for date, day_records in sorted(daily_data.items()):
        elements.append(Paragraph(f"Data: {date} - Horas total: {daily_hours.get(date, 0):.2f}", styles['Heading2']))
        data = [['Horário', 'Tipo', 'Anotação', 'Intervalo', 'Local', 'Registro']]
        for rec in sorted(day_records, key=lambda r: r.time):
            loc = rec.location if rec.location else 'N/A'
            if loc != 'N/A':
                lat, lon = loc.split(',')
                loc = f"{float(lat):.4f}, {float(lon):.4f}"
            photo_cell = 'N/A'
            if rec.photo_path:
                try:
                    img_data = requests.get(rec.photo_path).content
                    photo_cell = Image(BytesIO(img_data), width=45, height=45)
                except Exception as e:
                    print(f"PDF image error: {e}")
            data.append([rec.time, rec.type.capitalize(), rec.note or 'N/A', rec.break_duration, loc, photo_cell])
        table = Table(data, colWidths=[60, 60, 100, 80, 100, 60])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 20),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(table)
        elements.append(Paragraph("", styles['Normal']))
    doc.build(elements)

@records_bp.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    if request.method == 'POST':
        photo = request.files.get('photo')
        entry_type = request.form.get('type')
        note = request.form.get('note')
        break_duration = request.form.get('break_duration')
        location = request.form.get('location')
        if not photo or not entry_type:
            flash('Foto e tipo são obrigatórios.', 'error')
            return redirect(url_for('records.dashboard'))
        now = datetime.now()
        date = now.strftime('%Y-%m-%d')
        time = now.strftime('%H:%M:%S')
        filename = f"{date}_{time}"
        photo_url = upload_image_to_cloudinary(photo.stream, filename)
        record = Record(user_id=current_user.id, date=date, time=time, type=entry_type, note=note,
                        break_duration=int(break_duration) if break_duration else 0,
                        location=location, photo_path=photo_url)
        db.session.add(record)
        db.session.commit()
        flash('Registro salvo com sucesso!', 'success')
    all_records = Record.query.filter_by(user_id=current_user.id).all()
    daily_hours = calculate_hours(all_records)
    page, per_page, offset = get_page_args(page_parameter='page', per_page_parameter='per_page')
    per_page = 10
    total = len(all_records)
    records = all_records[offset: offset + per_page]
    pagination = Pagination(page=page, per_page=per_page, total=total, css_framework='bootstrap5')
    return render_template('dashboard.html', records=records, pagination=pagination, daily_hours=daily_hours, vapid_public_key=app.config['VAPID_PUBLIC_KEY'])

@records_bp.route('/calendar')
@login_required
def calendar():
    records = Record.query.filter_by(user_id=current_user.id).all()
    events = [{'title': f"{rec.type} at {rec.time}", 'start': f"{rec.date}T{rec.time}", 'description': rec.note} for rec in records]
    return render_template('calendar.html', events=events)

@records_bp.route('/download_pdf')
@login_required
def download_pdf():
    records = Record.query.filter_by(user_id=current_user.id).all()
    buffer = BytesIO()
    generate_professional_pdf(buffer, records, current_user.name, current_user.company)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name='records.pdf', mimetype='application/pdf')

@records_bp.route('/download_excel')
@login_required
def download_excel():
    records = Record.query.filter_by(user_id=current_user.id).all()
    daily_hours = calculate_hours(records)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(['Empresa', current_user.company])
    ws.append(['Data', 'Horário', 'Tipo', 'Anotação', 'Intervalo', 'Local', 'Registro', 'Horas Diárias'])
    row = 3
    last_date = None
    for rec in records:
        daily_h = daily_hours.get(rec.date, 0) if rec.date != last_date else ''
        ws.append([rec.date, rec.time, rec.type, rec.note, rec.break_duration, rec.location, rec.photo_path, daily_h])
        if rec.photo_path:
            try:
                img_data = requests.get(rec.photo_path).content
                with NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                    tmp.write(img_data)
                    tmp.flush()
                    img = openpyxl.drawing.image.Image(tmp.name)
                    img.width = 100
                    img.height = 100
                    ws.add_image(img, f'H{row}')
            except Exception as e:
                print(f"Excel image error: {e}")

