# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>
import datetime
import smtplib
import threading
import schedule
import uuid

from utils import *
from utils.exceptions import NotificationDeliveryProblem

logger = init_logger()

logger.info("Initializing..")

try:
	logger.info("Initializing storage..")
	storage = Storage()
	logger.debug(f"MongoDB Server version: {storage.mongo_client.server_info()['version']}")
except Exception as e:
	logger.error('Storage crashed', exc_info=True)
	raise RuntimeError from e


def run_threaded(name, func):
	job_thread = threading.Thread(target=func)
	job_thread.setName(f'{name}Thread')
	job_thread.start()


def auto_invoice():
	pass


def invoice_notify():
	invoices = storage.get_invoices()

	for invoice in invoices:
		if invoice.get('status') != 'UNPAID':
			continue

		if not invoice.get('_informed_notify'):
			message = "notify"
			invoice_tag = '_informed_notify'
		else:
			continue
			#if not invoice.get('_informed_notify_unpaid'):
			#	message = "invoice.notify.mail.unpaid"
			#   invoice_tag =
			#elif not invoice.get('_informed_notify_unpaid_last'):
			#	message = "invoice.notify.mail.unpaid.last"
		    #   invoice_tag =

		ok = False
		try:
			mail_send, delivery_report = send_message(invoice=invoice, message=message)
			ok = True
			logger.debug(f"Notify was sent successfully, delivery report: {delivery_report} SMTP response: {mail_send}")
		except Exception:
			logger.error("Can't send notify, problems with SMTP client", exc_info=True)

		if ok:
			try:
				storage.save_report(delivery_report)
			except Exception:
				logger.error(f"Problems with saving notify delivery-report", exc_info=True)

			try:
				invoice[invoice_tag] = True
				storage.save_invoice(invoice)
			except Exception:
				logger.error(f"Problems with saving notify informed status", exc_info=True)


def invoice_receipt():
	invoices = storage.get_invoices()

	for invoice in invoices:
		if invoice.get('status') != 'PAID':
			continue

		paid_timestamp = int(invoice.get('paid_timestamp') or 0)

		if not paid_timestamp:
			continue

		if invoice.get('_informed_receipt'):
			continue

		paid_dt = datetime.datetime.fromtimestamp(paid_timestamp)

		time_diff = datetime.datetime.today() - paid_dt

		if time_diff.total_seconds() < 28800:
			ok = False
			try:
				mail_send, delivery_report = send_message(invoice=invoice, message='receipt')
				ok = True
				logger.debug(f"Receipt was sent successfully, delivery report: {delivery_report} SMTP response: {mail_send}")
			except Exception:
				logger.error("Can't send receipt, problems with SMTP client", exc_info=True)

			if ok:
				try:
					storage.save_report(delivery_report)
				except Exception:
					logger.error(f"Problems with saving receipt delivery-report", exc_info=True)

				try:
					invoice['_informed_receipt'] = True
					storage.save_invoice(invoice)
				except Exception:
					logger.error(f"Problems with saving receipt informed status", exc_info=True)


def send_message(invoice, message, service='email'):
	if service != 'email':
		return Warning('Unknown service')

	if message == 'receipt':
		from_addr = Settings.SMTP_RECEIPT_USER
		from_pass = Settings.SMTP_RECEIPT_PASS
		header_service = Settings.SMTP_RECEIPT_HEADER_SERVICE
	elif message == 'notify':
		from_addr = Settings.SMTP_ALERT_USER
		from_pass = Settings.SMTP_ALERT_PASS
		header_service = Settings.SMTP_ALERT_HEADER_SERVICE
	else:
		raise Warning('Unknown message type')

	message_id = str(uuid.uuid4())
	invoice_id = invoice.get('_id')

	payee = storage.get_client(invoice.get('payee').get('id'))
	payer = storage.get_client(invoice.get('payer').get('id'))

	to_addr, to_name, subject, html, plain = InvoiceMail.make(
		message_id=message_id, invoice=invoice, payee=payee, payer=payer, message_key=message
	)

	logger.debug(f"[message id:{message_id}] Preparing mail-{header_service} ({invoice_id})")

	headers = Mail.create_headers(message_id=message_id, invoice_id=invoice_id, service=header_service)

	multipart = Mail.create_multipart(from_addr, Settings.SMTP_NAME, to_addr, to_name, subject, html, plain, headers)
	msg = multipart.as_string()

	delivery_report = Mail.create_delivery_report(invoice_id, message_id, from_addr, to_addr, to_name, subject, headers)

	logger.info(f"[message id:{message_id}] Sending mail-{header_service} to <{to_addr}> ({invoice_id})`")

	response = Mail.send(
		user=from_addr,
		password=from_pass,
		to_addr=to_addr,
		msg=msg
	)

	logger.info(f"[message id:{message_id}] Sending mail-{header_service} to <{to_addr}> ({invoice_id})\nResponse: {response}")

	return response, delivery_report


def console():
	while True:
		try:
			cmd_args = input().split(' ')
			cmd = cmd_args[0]

			if cmd == "invoice":
				logger.info("Find invoice by id {}".format(str(cmd_args[1])))
				invoice = storage.get_invoice(cmd_args[1])

				for key, value in invoice.items():
					logger.info(f"{key}: {value}")
			elif cmd == "client":
				logger.info("Find client by id {}".format(str(cmd_args[1])))
				client = storage.get_client(cmd_args[1])

				for key, value in client.items():
					logger.info(f"{key}: {value}")
			elif cmd == "tasks":
				if schedule.get_jobs():
					for job in schedule.get_jobs():
						logger.info(f'Task: {job}')
						logger.info(f'Next run: {job.next_run}')
				else:
					logger.info('No tasks.')
			elif cmd == "test":
				logger.debug('Test invoice_receipt')
				invoice_receipt()
			elif cmd == "test2":
				logger.debug('Test invoice_notify')
				invoice_notify()
			elif cmd == "stop":
				break
			else:
				logger.info("Command not found")
		except Exception:
			logger.error("Exception in console", exc_info=True)
