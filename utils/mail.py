# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>
import smtplib
import time
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from email import utils as email_utils

from settings import Settings


class MailServer:
    @staticmethod
    def get_mail_server():
        context = ssl.create_default_context(
            purpose=ssl.Purpose.CLIENT_AUTH,
            cafile='cert.pem'
        )

        mail_srv = smtplib.SMTP_SSL(
            host=Settings.SMTP_HOST,
            port=Settings.SMTP_PORT,
            timeout=Settings.SMTP_TIMEOUT,
            context=context
        )

        mail_srv.login(
            user=Settings.SMTP_USERNAME,
            password=Settings.SMTP_PASSWORD
        )

        return mail_srv

    @staticmethod
    def get_payload(to_name, to_email, subject, placeholders):
        payload = MIMEMultipart('alternative')

        payload.set_charset('utf8')

        payload['X-Pichugin-Projects-Service'] = 'INVOICE_REMINDER'
        payload['Date'] = email_utils.formatdate(time.time())
        payload['Subject'] = Header(subject, "utf-8")
        payload['To'] = email_utils.formataddr((str(Header(to_name, 'utf-8')), to_email))
        payload['From'] = email_utils.formataddr((str(Header(Settings.FROM_NAME, 'utf-8')), Settings.FROM_EMAIL))
        #payload['X-Priority'] = '2 (High)'
        #payload['Importance'] = 'High'
        #payload['X-MSMail-Priority'] = 'High'

        templates = {
            'plain': open('mail_template.txt', 'r', encoding='utf8').read().strip(),
            'html': open('mail_template.html', 'r', encoding='utf8').read().strip()
        }

        for template_name, template in templates.items():
            for placeholder, value in placeholders.items():
                template = template.replace(f'%{placeholder}%', str(value))
            templates[template_name] = template

        plain = MIMEText(templates['plain'].encode('utf-8'), 'plain', 'UTF-8')
        html = MIMEText(templates['html'].encode('utf-8'), 'html', 'UTF-8')

        payload.attach(plain)
        payload.attach(html)

        return payload

    @staticmethod
    def get_placeholders():
        return ['id', '_id', 'name', 'payee', 'payer', 'first_name', 'date_created', 'date_paid', 'gateway', 'total', 'discount', 'commission', 'credit', 'sum', 'currency_left', 'currency_right', 'email', 'sub_subject', 'message_id', 'year']
