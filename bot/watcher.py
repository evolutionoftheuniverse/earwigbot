# -*- coding: utf-8  -*-

"""
EarwigBot's IRC Watcher Component

The IRC watcher runs on a wiki recent-changes server and listens for edits.
Users cannot interact with this part of the bot. When an event occurs, we run
it through rules.py's process() function, which can result in wiki bot tasks
being started (located in tasks/) or messages being sent to channels on the IRC
frontend.
"""

import config
from classes import Connection, RC, BrokenSocketException
import rules

frontend_conn = None

def get_connection():
    """Return a new Connection() instance with connection information.

    Don't actually connect yet.
    """
    cf = config.irc["watcher"]
    connection = Connection(cf["host"], cf["port"], cf["nick"], cf["ident"],
            cf["realname"])
    return connection

def main(connection, f_conn=None):
    """Main loop for the Watcher IRC Bot component.
    
    get_connection() should have already been called and the connection should
    have been started with connection.connect(). Accept the frontend connection
    as well as an optional parameter in order to send messages directly to
    frontend IRC channels.
    """
    global frontend_conn
    frontend_conn = f_conn
    read_buffer = str()

    while 1:
        try:
            read_buffer = read_buffer + connection.get()
        except BrokenSocketException:
            return

        lines = read_buffer.split("\n")
        read_buffer = lines.pop()

        for line in lines:
            _process_message(line)

def _process_message(line):
    """Process a single message from IRC."""
    line = line.strip().split()

    if line[1] == "PRIVMSG":
        chan = line[2]

        # Ignore messages originating from channels not in our list, to prevent
        # someone PMing us false data:
        if chan not in config.irc["watcher"]["channels"]:
            continue

        msg = ' '.join(line[3:])[1:]
        rc = RC(msg)  # new RC object to store this event's data
        rc.parse()  # parse a message into pagenames, usernames, etc.
        process_rc(rc)  # report to frontend channels or start tasks

    # If we are pinged, pong back to the server:
    elif line[0] == "PING":
        msg = " ".join(("PONG", line[1]))
        connection.send(msg)

    # When we've finished starting up, join all watcher channels:
    elif line[1] == "376":
        for chan in config.irc["watcher"]["channels"]:
            connection.join(chan)

def process_rc(rc):
    """Process a recent change event from IRC (or, an RC object).

    The actual processing is configurable, so we don't have that hard-coded
    here. We simply call rules's process() function and expect a list of
    channels back, which we report the event data to.
    """
    chans = rules.process(rc)
    if chans and frontend_conn:
        pretty = rc.get_pretty()
        for chan in chans:
            frontend_conn.say(chan, pretty)
