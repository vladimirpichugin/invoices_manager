# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>


class Settings:
    DEBUG = False

    MONGO = ''
    MONGO_DATABASE = 'invoices'
    MONGO_C_INVOICES = 'invoices'
    MONGO_C_CLIENTS = 'clients'
    MONGO_C_MESSAGES = 'messages'
    MONGO_C_AUTO_INVOICES = 'auto_invoices'

    SMTP_SERVER_HOST = 'mail.pichug.in'
    SMTP_SERVER_PORT = 465
    SMTP_CONN_TIMEOUT = 5
    SMTP_SSL_CAFILE = 'assets/cert.pem'

    SMTP_NAME = 'Vladimir Pichugin'

    SMTP_RECEIPT_USER = 'receipt@pichug.in'
    SMTP_RECEIPT_PASS = ''
    SMTP_RECEIPT_HEADER_SERVICE = 'invoice_receipt'

    SMTP_ALERT_USER = 'receipt@pichug.in'
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

    INVOICE_TEMPLATE = {
        'currency': 'RUB',
        'status': None,
        'created': None,
        'due': None,
        'payer': None,
        'payee': None,
        'gateways': [],
        'items': [],
        'transactions': [],
        '_hidden': False,
        '_version': 2,
        'name': None,
        'paid_timestamp': None
    }

