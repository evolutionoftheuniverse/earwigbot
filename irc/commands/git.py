# -*- coding: utf-8  -*-

"""Commands to interface with the bot's git repository; use '!git help' for sub-command list."""

import shlex, subprocess
from config.irc_config import *

actions, data = None, None

def call(a, d):
    global actions, data
    actions, data = a, d

    if data.host not in ADMINS:
        actions.say(data.chan, "\x02%s\x0F: you must be a bot admin to use this command." % data.nick)
        return
    
    if not data.args:
        actions.say(data.chan, "\x02%s\x0F: no arguments provided." % data.nick)
        return

    if data.args[0] == "help":
        do_help()

    elif data.args[0] == "branch":
        do_branch()

    elif data.args[0] == "branches":
        do_branches()

    elif data.args[0] == "checkout":
        do_checkout()

    elif data.args[0] == "delete":
        do_delete()

    elif data.args[0] == "pull":
        do_pull()

    elif data.args[0] == "status":
        do_status()

    else: # they asked us to do something we don't know
        actions.say(data.chan, "\x02%s\x0F: unknown argument: \x0303%s\x0301." % (data.nick, data.args[0]))

def exec_shell(command):
    """execute a shell command and get the output"""
    command = shlex.split(command)
    result = subprocess.check_output(command, stderr=subprocess.STDOUT)
    return result

def do_help():
    """display all commands"""
    help_dict = {
        "branch": "get current branch",
        "branches": "get all branches",
        "checkout": "switch branches",
        "delete": "delete an old branch",
        "pull": "update everything from the remote server",
        "status": "check if we are out of date"
    }
    help = ""
    for key in help_dict.keys():
        help += "\x0303%s\x0301: (%s)," % (key, help_dict[key])
    help = help[:-1] # trim last comma

    actions.say(data.chan, "\x02%s\x0F: sub-commands are: %s." % (data.nick, help))

def do_branch():
    """get our current branch"""
    branch = exec_shell("git name-rev --name-only HEAD")
    branch = branch[:-1] # strip newline

    actions.say(data.chan, "\x02%s\x0F: currently on branch \x0302%s\x0301." % (data.nick, branch))

def do_branches():
    """get list of branches"""
    branches = exec_shell("git branch")

    branches = branches[:-1] # strip newline
    branches = branches.replace('\n* ', ', ') # cleanup extraneous characters
    branches = branches.replace('* ', ' ')
    branches = branches.replace('\n  ', ', ')
    branches = branches.strip()

    actions.say(data.chan, "\x02%s\x0F: branches: \x0302%s\x0301." % (data.nick, branches))

def do_checkout():
    """switch branches"""
    try:
        branch = data.args[1]
    except IndexError: # no branch name provided
        actions.say(data.chan, "\x02%s\x0F: switch to which branch?" % data.nick)
        return

    try:
        result = exec_shell("git checkout %s" % branch)
        if "Already on" in result:
            actions.say(data.chan, "\x02%s\x0F: already on \x0302%s\x0301!" % (data.nick, branch))
        else:
            actions.say(data.chan, "\x02%s\x0F: switched to branch \x0302%s\x0301." % (data.nick, branch))

    except subprocess.CalledProcessError: # git couldn't switch branches
        actions.say(data.chan, "\x02%s\x0F: branch \x0302%s\x0301 does not exist!" % (data.nick, branch))

def do_delete():
    """delete a branch, while making sure that we are not on it"""
    try:
        delete_branch = data.args[1]
    except IndexError: # no branch name provided
        actions.say(data.chan, "\x02%s\x0F: delete which branch?" % data.nick)
        return

    current_branch = exec_shell("git name-rev --name-only HEAD")
    current_branch = current_branch[:-1] # strip newline

    if current_branch == delete_branch:
        actions.say(data.chan, "\x02%s\x0F: you're currently on this branch; please checkout to a different branch before deleting." % data.nick)
        return

    exec_shell("git branch -d %s" % delete_branch)

    actions.say(data.chan, "\x02%s\x0F: branch \x0302%s\x0301 has been deleted locally." % (data.nick, delete_branch))

def do_pull():
    """pull from remote repository"""
    branch = exec_shell("git name-rev --name-only HEAD")
    branch = branch[:-1] # strip newline
    actions.say(data.chan, "\x02%s\x0F: pulling from remote (currently on \x0302%s\x0301)..." % (data.nick, branch))

    result = exec_shell("git pull")

    if "Already up-to-date." in result:
        actions.say(data.chan, "\x02%s\x0F: done; no new changes." % data.nick)
    else:
        actions.say(data.chan, "\x02%s\x0F: done; new changes merged." % data.nick)

def do_status():
    """check whether we have anything to pull"""
    result = exec_shell("git fetch --dry-run")
    if not result:
        actions.say(data.chan, "\x02%s\x0F: local copy is up-to-date with remote." % data.nick)
    else:
        actions.say(data.chan, "\x02%s\x0F: remote is ahead of local copy." % (data.nick))
