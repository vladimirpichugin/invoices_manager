# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>
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


def email_alert():
	#logger.debug('email_reminder. every 10 minutes')
	invoice = storage.get_invoice('4d0c6355-dd6f-4a38-814c-8050280eca25')
	#logger.debug(invoice)


def email_receipt():
	invoice = storage.get_invoice('4d0c6355-dd6f-4a38-814c-8050280eca25')
	payee = storage.get_client(invoice.get('payee').get('id'))
	payer = storage.get_client(invoice.get('payer').get('id'))

	mail_delivery_report, from_addr, to_addr, msg = MailInvoiceReceipt.paid(
		invoice=invoice,
		payee=payee,
		payer=payer
	)

	try:
		mail_client = Mail.get_mail_client()
		mail_client.login(user=Settings.SMTP_RECEIPT_USER, password=Settings.SMTP_RECEIPT_PASS)
	except Exception as e:
		raise NotificationDeliveryProblem('Can\'t init SMTP client.') from e

	try:
		send_message = mail_client.sendmail(from_addr, to_addr, msg)
		logger.debug(f'Send MAIL from <{from_addr}> to <{to_addr}>, response: {send_message}')
	except smtplib.SMTPRecipientsRefused as e:
		raise NotificationDeliveryProblem('Can\'t send mail.') from e
	finally:
		mail_client.quit()

	logger.debug(f'MessageDeliveryReport: {mail_delivery_report}')
	save = storage.save_report(mail_delivery_report)
	logger.debug(f'Save MessageDeliveryReport: {save}')


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
				logger.debug('Test email_receipt')
				email_receipt()
			elif cmd == "test2":
				logger.debug('Test email_alert')
				email_alert()
			elif cmd == "stop":
				break
			else:
				logger.info("Command not found")
		except Exception:
			logger.error("Exception in console", exc_info=True)
