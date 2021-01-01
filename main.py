#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This program is dedicated to the public domain under the CC0 license.

import csv
import datetime
import html
import json
import logging
import traceback
from db import *
from config import readconfig

# Datumsrechner
import pytz
from telegram import (
    Update,
    ParseMode,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    Updater,
    CallbackContext,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    Filters
)

# Enable logging
logging.basicConfig(
    filename='example.log', level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s: %(message)s',
)
logger = logging.getLogger(__name__)

# States
START, TERMINABFRAGE, NEUEDATEN = range(3)
BACK, END = range(10, 12)

# Read the config from JSON
config = readconfig()

# States
START, TERMINABFRAGE, NEUEDATEN = range(3)
BACK, END = range(10, 12)


def create_button(description: str, callback: Any) -> InlineKeyboardButton:
    return InlineKeyboardButton(description, callback_data=str(callback))


def create_keyboard(raw_data: List[List[List[Any]]]) -> List[List[InlineKeyboardButton]]:
    menu_neu = list()
    for raw_zeile in raw_data:
        zeile_neu = list()
        menu_neu.append(zeile_neu)

        for spalte_list in raw_zeile:
            zeile_neu.append(create_button(spalte_list[0], spalte_list[1]))
    return menu_neu


def start(update: Update, context: CallbackContext):
    keyboard = [
        [["Abfrage", TERMINABFRAGE], ["Neue Termine", NEUEDATEN]],
        [["Ende", END]]
    ]
    logger.info(f"User started conversation")
    logger.info(f"Username {update.message.from_user}")
    update.message.reply_text(
        "Womit kann ich helfen?",
        reply_markup=InlineKeyboardMarkup(create_keyboard(keyboard)))
    return START


def start_over(update: Update, context: CallbackContext):
    keyboard = [
        [["Abfrage", TERMINABFRAGE], ["Neue Termine", NEUEDATEN]],
        [["Ende", END]]
    ]
    # Answer query as usual
    query = update.callback_query
    query.answer()
    query.edit_message_text(
        text="Weißt ja, wie das geht...",
        reply_markup=InlineKeyboardMarkup(create_keyboard(keyboard)))
    return START


def start_abfrage(update: Update, context: CallbackContext):
    # Answer query as usual
    query = update.callback_query
    query.answer()
    keyboard = list()
    for liste in config["Texte"].values():  # type: List[str, str]
        # liste: ["Restabfall", "Leerung: Restabfall"]
        keyboard.append([create_button(liste[0], liste[1])])
    query.edit_message_text(
        text="Welche Art denn?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return TERMINABFRAGE


def do_abfrage(update: Update, context: CallbackContext):
    # Answer query as usual
    query = update.callback_query
    query.answer()
    keyboard = [[create_button("zurück", BACK)]]

    # Get Today
    heute = (datetime.datetime.today()).strftime("%Y%m%d")
    beschreibung = "*" if query.data == config["Texte"]["Egal"][1] else query.data
    sql = f"""SELECT Termin  
          FROM Calendar 
          WHERE 
          Beschreibung = '{beschreibung}' AND
          Termin > {heute}
          ORDER BY Termin ASC
          LIMIT 1"""
    result = dbfetch(sql)

    if not result:
        erg = f"Abfrage ergab kein Ergebnis - keine Termine mehr übrig oder Fehler.\n\n{sql}"
    else:
        resultday = datetime.datetime.strptime(str(result[0][0]), "%Y%m%d")
        erg = f"""Die nächste Abholung ist am {resultday.strftime('%A, %d.%m.%Y')}\n
              Das sind noch {((resultday - datetime.datetime.today()).days + 1)} Tage"""
    query.edit_message_text(
        text=erg,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return NEUEDATEN


def daily_message(context: CallbackContext):
    #  context.bot.sendMessage(chat_id=context.job.context, text="Hey")
    #  context.bot.sendMessage(chat_id=DEVELOPER_CHAT_ID, text="Hey")
    morgen = (datetime.datetime.today() + datetime.timedelta(days=1)).strftime("%Y%m%d")
    sql = f"SELECT Beschreibung FROM Calendar WHERE Termin={morgen}"
    logger.info(f"SQL was {sql}")
    result = dbfetch(sql)

    for uid in config["User"]["User"]:
        if len(result) > 0:
            # Jedem User, der oben in der Variable steht, eine Nachricht schicken
            for r in result:
                message = f"Morgen wird abgeholt: {r[0]}"
                logger.info(f"Send message to {uid} - message: {message}")
                context.bot.send_message(chat_id=uid, text=message)
        else:
            message = "++ nichts zu tun ++"
            logger.info(f"Send message to {uid} - message: {message}")
            context.bot.send_message(chat_id=uid, text=message)


def start_dateninput(update: Update, context: CallbackContext):
    # Answer query as usual
    query = update.callback_query
    logger.info(f"Anfrage von {query.from_user}...")
    query.answer()
    keyboard = [[create_button("zurück", BACK)]]
    query.edit_message_text(
        text="Schick mir bitte die CSV-Datei...",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return NEUEDATEN


def do_dateninput(update: Update, context: CallbackContext):
    # CSV download
    # Delete content of database
    # Insert new values into database
    keyboard = [[create_button("zurück", BACK)]]

    # Download CSV
    datafile = update.message.document.get_file()
    datafile.download("newdata.csv")

    # Delete old data
    sql = "DELETE FROM Calendar;"
    logger.info(f"SQL was {sql}")
    dbexec(sql)

    # Start reading csv
    with open("newdata.csv", mode="r") as csv_file:
        # Read content
        # Comma is default delimiter
        dr = csv.DictReader(csv_file)
        to_db = [(i["Beschreibung"], i["Termin"]) for i in dr]

        # Insert into DB
        sql = "INSERT INTO Calendar (Beschreibung, Termin) VALUES (?, ?);"
        result = dbexecmany(sql, to_db)
    message = "Datenbasis wurde aktualisiert!" if result else "Fehler bei der Aktualisierung"
    update.message.reply_text(
        text=message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return NEUEDATEN


def cancel(update: Update, context: CallbackContext):
    # Reacts to inlinekeyboardbutton -> query
    query = update.callback_query
    query.answer()
    query.edit_message_text(text="Bis dann!")
    return ConversationHandler.END


def end(update: Update, context: CallbackContext):
    # Reacts to /end -> Send independent message
    update.message.reply_text("Bis dann!")
    return ConversationHandler.END


def main():
    # Create the var updater of Updater
    updater = Updater(config["Bot"]["Token"])

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Build the commands...
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start, Filters.user(config["User"]["User"]))],
        states={
            START: [
                CallbackQueryHandler(start_abfrage, pattern="^" + str(TERMINABFRAGE) + "$"),
                CallbackQueryHandler(start_dateninput, pattern="^" + str(NEUEDATEN) + "$"),
                CallbackQueryHandler(cancel, pattern="^" + str(END) + "$"),
            ],
            TERMINABFRAGE: [CallbackQueryHandler(do_abfrage)],
            NEUEDATEN: [
                MessageHandler(Filters.document.mime_type("text/csv"), do_dateninput),
                CallbackQueryHandler(start_over, pattern="^" + str(BACK) + "$"),
            ],
        },
        fallbacks=[CommandHandler("end", end)],
    )

    # ...register them
    dp.add_handler(conv_handler)
    # ...and the error handler
    dp.add_error_handler(error_handler)

    # Create daily job
    t = datetime.time(19, 0, 0, tzinfo=pytz.timezone("Europe/Berlin"))
    updater.job_queue.run_daily(daily_message, t)

    # Start the Bot
    updater.start_polling(config["Bot"]["PollingTime"])

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


def error_handler(update: Update, context: CallbackContext):
    """Log the error and send a telegram message to notify the developer."""
    # Log the error before we do anything else, so we can see it even if something breaks.
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

    # traceback.format_exception returns the usual python message about an exception, but as a
    # list of strings rather than a single string, so we have to join them together.
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb = ''.join(tb_list)

    message = (
        'An exception was raised while handling an update\n'
        '<pre>update = {}</pre>\n\n'
        '<pre>context.chat_data = {}</pre>\n\n'
        '<pre>context.user_data = {}</pre>\n\n'
        '<pre>{}</pre>'
    ).format(
        html.escape(json.dumps(update.to_dict(), indent=2, ensure_ascii=False)),
        html.escape(str(context.chat_data)),
        html.escape(str(context.user_data)),
        html.escape(tb),
    )

    # Finally, send the message
    context.bot.send_message(
        chat_id=config["Texte"]["Developer"],
        text=message, parse_mode=ParseMode.HTML)


if __name__ == "__main__":
    main()
