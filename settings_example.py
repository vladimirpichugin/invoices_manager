# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>


class Settings:
    DEBUG = False

    MONGO = ''
    MONGO_DATABASE = ''
    MONGO_C_INVOICES = ''
    MONGO_C_CLIENTS = ''
    MONGO_C_MESSAGES = ''
    MONGO_C_AUTO_INVOICES = ''

    SMTP_SERVER_HOST = ''
    SMTP_SERVER_PORT = 0
    SMTP_CONN_TIMEOUT = 0
    SMTP_SSL_CAFILE = 'assets/cert.pem'

    SMTP_NAME = ''

    SMTP_RECEIPT_USER = ''
    SMTP_RECEIPT_PASS = ''
    SMTP_RECEIPT_HEADER_SERVICE = 'invoice_receipt'

    SMTP_ALERT_USER = ''
    SMTP_ALERT_PASS = ''
    SMTP_ALERT_HEADER_SERVICE = 'invoice_notify'

    PLACEHOLDERS = {
        'INVOICE_OBJECT': [
            'id', '_id', 'name', 'commission'
        ],
        'RECEIPT': [
            'id', '_id', 'name', 'total', 'discount', 'commission', 'paid',
            'payee', 'payer', 'date_created', 'date_due', 'date_paid', 'gateway', 'first_name', 'email',
            'preview', 'message_id', 'year'
        ],
        'NOTIFY': [
            'id', '_id', 'name', 'total',
            'date_created', 'date_due', 'date_paid', 'first_name', 'email',
            'preview', 'message_id', 'year'
        ]
    }

