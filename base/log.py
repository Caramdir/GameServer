from config import app_log_path, DEVTEST
import logging
import logging.handlers

main_log = logging.getLogger("main_log")

if DEVTEST:
    main_log.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
else:
    main_log.setLevel(logging.INFO)
    ch = logging.handlers.RotatingFileHandler(app_log_path, maxBytes=1024*1024, backupCount=5)
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s -  %(levelname)s: %(message)s')

ch.setFormatter(formatter)
main_log.addHandler(ch)
main_log.propagate = False
