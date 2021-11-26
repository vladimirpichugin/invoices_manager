# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>
import datetime
import smtplib
import threading
import schedule

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
	pass


def invoice_receipt():
	from_addr = Settings.SMTP_RECEIPT_USER
	from_name = Settings.SMTP_RECEIPT_NAME

	invoices = storage.get_invoices()

	for invoice in invoices:
		if invoice.get('_informed_receipt'):
			continue

		paid_timestamp = int(invoice.get('paid_timestamp') or 0)

		if not paid_timestamp:
			continue

		paid_dt = datetime.datetime.fromtimestamp(paid_timestamp)

		time_diff = datetime.datetime.today() - paid_dt

		if time_diff.total_seconds() < 28800:
			payee = storage.get_client(invoice.get('payee').get('id'))
			payer = storage.get_client(invoice.get('payer').get('id'))

			delivery_report, to_addr, msg = MailInvoiceReceipt.make(
				invoice=invoice,
				payee=payee,
				payer=payer,
				from_addr=from_addr,
				from_name=from_name
			)

			try:
				send_message = Mail.send(
					user=from_addr,
					password=Settings.SMTP_ALERT_PASS,
					to_addr=to_addr,
					msg=msg
				)

				logger.debug(f'Send MAIL from <{from_addr}> to <{to_addr}>, response: {send_message}')

				invoice['_informed_receipt'] = True
				storage.save_invoice(invoice)

				logger.debug(f'MessageDeliveryReport: {delivery_report}')
				save = storage.save_report(delivery_report)
				logger.debug(f'Save MessageDeliveryReport: {save}')
			except smtplib.SMTPRecipientsRefused as e:
				raise NotificationDeliveryProblem('Can\'t send mail.') from e
			except Exception as e:
				raise NotificationDeliveryProblem('Can\'t init SMTP client.') from e


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
