# -*- coding: utf-8 -*-
import logging
from sys import argv

# Logging
if "-v" in argv or "--verbose" in argv:
    LOGLEVEL = logging.DEBUG
else:
    LOGLEVEL = logging.WARNING

logging.basicConfig(
    filename="logfile.log",
    format="%(asctime)s - %(name)s - %(levelname)s - %(funcName)s: %(message)s",
    level=LOGLEVEL)

logger = logging.getLogger("Müllbot")


def section_logger(sectionname: str) -> logging.Logger:
    new_logger = logging.getLogger(sectionname)
    return new_logger
