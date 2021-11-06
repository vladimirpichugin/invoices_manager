# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>
import threading

import schedule

from utils import *

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


def email_reminder():
	#logger.debug('email_reminder. every 10 minutes')
	invoice = storage.get_invoice('625f3b94-dde5-4c46-a3e4-81a4efdc99a1')
	#logger.debug(invoice)


def email_receipts():
	logger.debug('email_receipts. at 10:00 AM')
	invoice = storage.get_invoice('625f3b94-dde5-4c46-a3e4-81a4efdc99a1')
	logger.debug(invoice)


def console():
	while True:
		cmd = input()
		cmd_args = cmd.split(' ')

		try:
			if cmd_args[0] == "invoice":
				logger.info("Find invoice by id {}".format(str(cmd_args[1])))
				for key, value in storage.get_invoice(cmd_args[1]).items():
					logger.info(f"{key}: {value}")
			elif cmd_args[0] == "client":
				logger.info("Find client by id {}".format(str(cmd_args[1])))
				logger.info(storage.get_client(cmd_args[1]))
			elif cmd_args[0] == "help":
				logger.info("Commands list: stop, invoice <id>, client <id>")
			elif cmd_args[0] == "stop":
				break
			elif cmd_args[0] == "tasks":
				for job in schedule.get_jobs():
					logger.info(f'Task: {job}')
					logger.info(f'Next run: {job.next_run}')
			else:
				logger.info("Command not found, commands list: /help")
		except IndexError:
			logger.error("Argument not found.")


def test():
	# \%(?P<tag>.+?)\/\%(?P<payload>[\s\S]*?)\%\/\%
	# (<!--(?P<open_tag>.+?)-->)(?P<payload>.+?)(<!--(?P<close_tag>.+?)-->)

	logger.debug(storage.get_invoice('625f3b94-dde5-4c46-a3e4-81a4efdc99a1'))
