# -*- coding: utf-8  -*-

import re

from classes import BaseCommand
import config
import wiki

class Command(BaseCommand):
    """Get the number of pending AfC submissions, open redirect requests, and
    open file upload requests."""
    name = "status"
    hooks = ["join", "msg"]

    def check(self, data):
        commands = ["status", "count", "num", "number"]
        if data.is_command and data.command in commands:
            return True

        try:
            if data.line[1] == "JOIN" and data.chan == "#wikipedia-en-afc":
                if data.nick != config.irc["frontend"]["nick"]:
                    return True
        except IndexError:
            pass
        return False

    def process(self, data):
        self.site = wiki.get_site()
        self.site._maxlag = None

        if data.line[1] == "JOIN":
            status = " ".join(("\x02Current status:\x0F", self.get_status()))
            self.connection.notice(data.nick, status)
            return

        if data.args:
            action = data.args[0].lower()
            if action.startswith("sub") or action == "s":
                subs = self.count_submissions()
                msg = "there are \x0305{0}\x0301 pending AfC submissions (\x0302WP:AFC\x0301)."
                self.connection.reply(data, msg.format(subs))

            elif action.startswith("redir") or action == "r":
                redirs = self.count_redirects()
                msg = "there are \x0305{0}\x0301 open redirect requests (\x0302WP:AFC/R\x0301)."
                self.connection.reply(data, msg.format(redirs))

            elif action.startswith("file") or action == "f":
                files = self.count_redirects()
                msg = "there are \x0305{0}\x0301 open file upload requests (\x0302WP:FFU\x0301)."
                self.connection.reply(data, msg.format(files))

            elif action.startswith("agg") or action == "a":
                try:
                    agg_num = int(data.args[1])
                except IndexError:
                    agg_data = (self.count_submissions(),
                                self.count_redirects(), self.count_files())
                    agg_num = self.get_aggregate_number(agg_data)
                except ValueError:
                    msg = "\x0303{0}\x0301 isn't a number!"
                    self.connection.reply(data, msg.format(data.args[1]))
                    return
                aggregate = self.get_aggregate(agg_num)
                msg = "aggregate is \x0305{0}\x0301 (AfC {1})."
                self.connection.reply(data, msg.format(agg_num, aggregate))

            else:
                msg = "unknown argument: \x0303{0}\x0301. Valid args are 'subs', 'redirs', 'files', 'agg'."
                self.connection.reply(data, msg.format(data.args[0]))

        else:
            self.connection.reply(data, self.get_status())

    def get_status(self):
        subs = self.count_submissions()
        redirs = self.count_redirects()
        files = self.count_files()
        agg_num = self.get_aggregate_number((subs, redirs, files))
        aggregate = self.get_aggregate(agg_num)

        msg = "Articles for creation {0} (\x0302AFC\x0301: \x0305{1}\x0301; \x0302AFC/R\x0301: \x0305{2}\x0301; \x0302FFU\x0301: \x0305{3}\x0301)."
        return msg.format(aggregate, subs, redirs, files)

    def count_submissions(self):
        """Returns the number of open AFC submissions (count of CAT:PEND)."""
        cat = self.site.get_category("Pending AfC submissions")
        subs = len(cat.members(limit=500))

        # Remove [[Wikipedia:Articles for creation/Redirects]] and
        # [[Wikipedia:Files for upload]], which aren't real submissions:
        subs -= 2
        return subs

    def count_redirects(self):
        """Returns the number of open redirect submissions. Calculated as the
        total number of submissions minus the closed ones."""
        title = "Wikipedia:Articles for creation/Redirects"
        content = self.site.get_page(title).get()
        total = len(re.findall("^\s*==(.*?)==\s*$", content, re.MULTILINE))
        closed = content.lower().count("{{afc-c|b}}")
        redirs = total - closed
        return redirs

    def count_files(self):
        """Returns the number of open WP:FFU (Files For Upload) requests.
        Calculated as the total number of requests minus the closed ones."""
        content = self.site.get_page("Wikipedia:Files for upload").get()
        total = len(re.findall("^\s*==(.*?)==\s*$", content, re.MULTILINE))
        closed = content.lower().count("{{ifu-c|b}}")
        files = total - closed
        return files

    def get_aggregate(self, num):
        """Returns a human-readable AFC status based on the number of pending
        AFC submissions, open redirect requests, and open FFU requests. This
        does not match {{AFC status}} directly because my algorithm factors in
        WP:AFC/R and WP:FFU while the template only looks at the main
        submissions. My reasoning is that AFC/R and FFU are still part of
        the project, so even if there are no pending submissions, a backlog at
        FFU (for example) indicates that our work is *not* done and the
        project-wide backlog is most certainly *not* clear."""
        if num == 0:
            return "is \x02\x0303clear\x0301\x0F"
        elif num < 125:  # < 25 subs
            return "is \x0303almost clear\x0301"
        elif num < 200:  # < 40 subs
            return "is \x0312normal\x0301"
        elif num < 275:  # < 55 subs
            return "is \x0307lightly backlogged\x0301"
        elif num < 350:  # < 70 subs
            return "is \x0304backlogged\x0301"
        elif num < 500:  # < 100 subs
            return "is \x02\x0304heavily backlogged\x0301\x0F"
        else:  # >= 100 subs
            return "is \x02\x1F\x0304severely backlogged\x0301\x0F"

    def get_aggregate_number(self, (subs, redirs, files)):
        """Returns an 'aggregate number' based on the real number of pending
        submissions in CAT:PEND (subs), open redirect submissions in WP:AFC/R
        (redirs), and open files-for-upload requests in WP:FFU (files)."""
        num = (subs * 5) + (redirs * 2) + (files * 2)
        return num