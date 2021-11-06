# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>
import time
import threading
import schedule

import manager


if __name__ == "__main__":
    manager.logger.debug("Initializing reminder..")

    console_thread = threading.Thread(target=manager.console)
    console_thread.setName('ConsoleThread')
    console_thread.daemon = True
    console_thread.start()

    schedule.every(10).minutes.do(manager.run_threaded, name='Reminder', func=manager.email_reminder).run()
    schedule.every().day.at('10:00').do(manager.run_threaded, name='Receipts', func=manager.email_receipts)

    # Поддерживать работу основного потока, пока поток демона жив.
    while True:
        try:
            if not console_thread.is_alive():
                manager.logger.error("ConsoleThread is not alive, shutting down..")
                break

            schedule.run_pending()

            time.sleep(1)
        except KeyboardInterrupt:
            manager.logger.info("Shutting down..")
            break
