#!/usr/bin/env python
import sqlite3
import os.path
import logging

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s: %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


DBFILE = "telegram_calendar.db"


def dbcreate():
    # TODO TryCatch drum herum bauen, damit auch ein False ausgegeben werden kann
    logger.info(f"DB doesnt exist - lets create this file: {DBFILE}")
    conn = sqlite3.connect(DBFILE)
    sql = "CREATE TABLE Calendar (Beschreibung TEXT, Termin NUMERIC);"
    cursor = conn.cursor()
    cursor.execute(sql)
    logger.info(f"SQL executed: {sql}")
    dbclose(conn)
    return True


def dbconnect():
    if not os.path.isfile(DBFILE):
        logger.info(f"DB path does not exist")
        if dbcreate():
            logger.info(f"DB creation was successful")
        else:
            return

    # Either file exists or was created
    # Let's connect to it
    try:
        conn = sqlite3.connect(DBFILE)
    except sqlite3.Error as e:
        logger.info(f"Exception: {e}")
        return
    return conn


def dbexec(sql):
    connection = dbconnect()
    logger.info(f"DB connection is {True if connection else False}")
    if connection:
        cursor = connection.cursor()
        cursor.execute(sql)
        dbclose(connection)
        return True
    return False


def dbexecmany(sql, data: list) -> bool:
    connection = dbconnect()
    logger.info(f"DB connection is {True if connection else False}")
    if connection:
        cursor = connection.cursor()
        cursor.executemany(sql, data)
        logger.info(f"SQL for new values executed: {sql}")
        logger.info(f"New values inserted - rows {len(data)}")
        connection.commit()
        dbclose(connection)
        return True
    return False


def dbfetch(sql):
    connection = dbconnect()
    if connection:
        cursor = connection.cursor()
        try:
            cursor.execute(sql)
        except sqlite3.OperationalError as e:
            print(e)
            dbclose(connection)
            return
        result = cursor.fetchall()
        dbclose(connection)
        return result
    return False


def dbclose(connection):
    if connection:
        connection.close()
        return True
    return False
