# -*- coding: utf-8  -*-
#
# Copyright (C) 2009-2012 by Ben Kurtovic <ben.kurtovic@verizon.net>
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is 
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from earwigbot.commands import BaseCommand

class Command(BaseCommand):
    """Voice, devoice, op, or deop users in the channel."""
    name = "chanops"

    def check(self, data):
        commands = ["chanops", "voice", "devoice", "op", "deop"]
        if data.is_command and data.command in commands:
            return True
        return False

    def process(self, data):
        if data.command == "chanops":
            msg = "available commands are !voice, !devoice, !op, and !deop."
            self.connection.reply(data, msg)
            return

        if data.host not in self.config.irc["permissions"]["admins"]:
            msg = "you must be a bot admin to use this command."
            self.connection.reply(data, msg)
            return

        # If it is just !op/!devoice/whatever without arguments, assume they
        # want to do this to themselves:
        if not data.args:
            target = data.nick
        else:
            target = data.args[0]

        msg = " ".join((data.command, data.chan, target))
        self.connection.say("ChanServ", msg)
