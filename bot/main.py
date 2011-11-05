#! /usr/bin/env python
# -*- coding: utf-8  -*-

"""
EarwigBot's Core

This should not be run directly; the wrapper in "earwigbot.py" is preferred,
but it should work fine alone, as long as you enter the password-unlock key at
the initial hidden prompt if one is needed.

The core is essentially responsible for starting the various bot components
(irc, scheduler, etc) and making sure they are all happy. An explanation of the
different components follows:

EarwigBot has three components that can run independently of each other: an IRC
front-end, an IRC watcher, and a wiki scheduler.
* The IRC front-end runs on a normal IRC server and expects users to interact
  with it/give it commands.
* The IRC watcher runs on a wiki recent-changes server and listens for edits.
  Users cannot interact with this part of the bot.
* The wiki scheduler runs wiki-editing bot tasks in separate threads at
  user-defined times through a cron-like interface.

There is a "priority" system here:
1. If the IRC frontend is enabled, it will run on the main thread, and the IRC
   watcher and wiki scheduler (if enabled) will run on separate threads.
2. If the wiki scheduler is enabled, it will run on the main thread, and the
   IRC watcher (if enabled) will run on a separate thread.
3. If the IRC watcher is enabled, it will run on the main (and only) thread.
Else, the bot will stop, as no components are enabled.
"""

import logging
import threading
import time

import config
import frontend
import tasks
import watcher

f_conn = None
w_conn = None

def irc_watcher(f_conn=None):
    """Function to handle the IRC watcher as another thread (if frontend and/or
    scheduler is enabled), otherwise run as the main thread."""
    global w_conn
    while 1:  # restart the watcher component if it breaks (and nothing else)
        w_conn = watcher.get_connection()
        w_conn.connect()
        try:
            watcher.main(w_conn, f_conn)
        except:
            logging.exception("Watcher had an error")
        time.sleep(5)  # sleep a bit before restarting watcher
        logging.warn("Watcher has stopped; restarting component")

def wiki_scheduler():
    """Function to handle the wiki scheduler as another thread, or as the
    primary thread if the IRC frontend is not enabled."""
    while 1:
        time_start = time.time()
        now = time.gmtime(time_start)

        tasks.schedule(now)

        time_end = time.time()
        time_diff = time_start - time_end
        if time_diff < 60:  # sleep until the next minute
            time.sleep(60 - time_diff)

def irc_frontend():
    """If the IRC frontend is enabled, make it run on our primary thread, and
    enable the wiki scheduler and IRC watcher on new threads if they are
    enabled."""
    global f_conn

    logging.info("Starting IRC frontend")
    f_conn = frontend.get_connection()
    frontend.startup(f_conn)

    if "wiki_schedule" in config.components:
        logging.info("Starting wiki scheduler")
        tasks.load()
        t_scheduler = threading.Thread(target=wiki_scheduler)
        t_scheduler.name = "wiki-scheduler"
        t_scheduler.daemon = True
        t_scheduler.start()

    if "irc_watcher" in config.components:
        logging.info("Starting IRC watcher")
        t_watcher = threading.Thread(target=irc_watcher, args=(f_conn,))
        t_watcher.name = "irc-watcher"
        t_watcher.daemon = True
        t_watcher.start()

    frontend.main()

    if "irc_watcher" in config.components:
        w_conn.close()
    f_conn.close()

def run():
    config.load()
    try:
        # Wait for our password decrypt key from the bot's wrapper, then
        # decrypt passwords:
        key = raw_input()
    except EOFError:
        pass
    else:
        config.decrypt(key)

    enabled = config.components

    if "irc_frontend" in enabled:
        # Make the frontend run on our primary thread if enabled, and enable
        # additional components through that function
        irc_frontend()

    elif "wiki_schedule" in enabled:
        # Run the scheduler on the main thread, but also run the IRC watcher on
        # another thread iff it is enabled
        logging.info("Starting wiki scheduler")
        tasks.load()
        if "irc_watcher" in enabled:
            logging.info("Starting IRC watcher")
            t_watcher = threading.Thread(target=irc_watcher)
            t_watcher.name = "irc-watcher"
            t_watcher.daemon = True
            t_watcher.start()
        wiki_scheduler()

    elif "irc_watcher" in enabled:
        # The IRC watcher is our only enabled component, so run its function
        # only and don't worry about anything else:
        logging.info("Starting IRC watcher")
        irc_watcher()

    else:  # Nothing is enabled!
        logging.critical("No bot parts are enabled; stopping")
        exit(1)

if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        logging.critical("KeyboardInterrupt: stopping main bot loop")
        exit(1)
