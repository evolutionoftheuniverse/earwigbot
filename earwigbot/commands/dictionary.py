# -*- coding: utf-8  -*-
#
# Copyright (C) 2009-2012 Ben Kurtovic <ben.kurtovic@verizon.net>
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

import re

from earwigbot import exceptions
from earwigbot.commands import Command

class Dictionary(Command):
    """Define words and stuff."""
    name = "dictionary"
    commands = ["dict", "dictionary", "define"]

    def process(self, data):
        if not data.args:
            self.reply(data, "what do you want me to define?")
            return

        term = " ".join(data.args)
        lang = self.bot.wiki.get_site().lang
        try:
            defined = self.define(term, lang)
        except exceptions.APIError:
            msg = "cannot find a {0}-language Wiktionary."
            self.reply(data, msg.format(lang))
        else:
            self.reply(data, defined.encode("utf8"))

    def define(self, term, lang, tries=2):
        try:
            site = self.bot.wiki.get_site(project="wiktionary", lang=lang)
        except exceptions.SiteNotFoundError:
            site = self.bot.wiki.add_site(project="wiktionary", lang=lang)

        page = site.get_page(term)
        try:
            entry = page.get()
        except (exceptions.PageNotFoundError, exceptions.InvalidPageError):
            if term.lower() != term and tries:
                return self.define(term.lower(), lang, tries - 1)
            if term.capitalize() != term and tries:
                return self.define(term.capitalize(), lang, tries - 1)
            return "no definition found."

        level, languages = self.get_languages(entry)
        if not languages:
            return u"couldn't parse {0}!".format(page.url)

        result = []
        for lang, section in sorted(languages.items()):
            definition = self.get_definition(section, level)
            result.append(u"({0}) {1}".format(lang, definition))
        return u"; ".join(result)

    def get_languages(self, entry, level=2):
        regex = r"(?:\A|\n)==\s*([a-zA-Z0-9_ ]*?)\s*==(?:\Z|\n)"
        split = re.split(regex, entry)
        if len(split) % 2 == 0:
            if level == 2:
                return self.get_languages(entry, level=3)
            else:
                return 3, None
            return 2, None

        split.pop(0)
        languages = {}
        for i in xrange(0, len(split), 2):
            languages[split[i]] = split[i + 1]
        return level, languages

    def get_definition(self, section, level):
        parts_of_speech = {
            "v.": "Verb",
            "n.": "Noun",
            "pron.": "Pronoun",
            "adj.": "Adjective",
            "adv.": "Adverb",
            "prep.": "Preposition",
            "conj.": "Conjunction",
            "inter.": "Interjection",
            "symbol": "Symbol",
            "suffix": "Suffix",
            "initialism": "Initialism",
            "phrase": "Phrase",
            "proverb": "Proverb",
            "prop. n.": "Proper noun",
            "abbr.": "\{\{abbreviation\}\}",
        }
        blocks = "=" * (level + 1)
        defs = []
        for part, fullname in parts_of_speech.iteritems():
            if re.search("{0}\s*{1}\s*{0}".format(blocks, fullname), section):
                regex = "{0}\s*{1}\s*{0}(.*?)(?:(?:{0})|\Z)"
                regex = regex.format(blocks, fullname)
                bodies = re.findall(regex, section, re.DOTALL)
                if bodies:
                    for body in bodies:
                        definition = self.parse_body(body)
                        if definition:
                            msg = u"\x02{0}\x0F {1}"
                            defs.append(msg.format(part, definition))

        return "; ".join(defs)

    def parse_body(self, body):
        substitutions = [
            ("<!--(.*?)-->", ""),
            ("\[\[(.*?)\|(.*?)\]\]", r"\2"),
            ("\{\{alternative spelling of\|(.*?)\}\}", r"Alternative spelling of \1."),
            ("\{\{synonym of\|(.*?)\}\}", r"Synonym of \1."),
        ]

        senses = []
        for line in body.splitlines():
            line = line.strip()
            if re.match("#\s*[^:*]", line):
                for regex, repl in substitutions:
                    line = re.sub(regex, repl, line)
                line = self.strip_templates(line)
                line = line[1:].replace("'''", "").replace("''", "")
                line = line.replace("[[", "").replace("]]", "")
                senses.append(line.strip())

        if not senses:
            return None
        if len(senses) == 1:
            return senses[0]

        result = []  # Number the senses incrementally
        for i, sense in enumerate(senses):
            result.append(u"{0}. {1}".format(i + 1, sense))
        return " ".join(result)

    def strip_templates(self, line):
        line = list(line)
        stripped = ""
        depth = 0
        while line:
            this = line.pop(0)
            if line:
                next = line[0]
            else:
                next = ""
            if this == "{" and next == "{":
                line.pop(0)
                depth += 1
            elif this == "}" and next == "}":
                line.pop(0)
                depth -= 1
            elif depth == 0:
                stripped += this
        return stripped