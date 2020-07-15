import sublime
import sublime_plugin
from .http import *
import os
import threading
import urllib.request
import subprocess
from urllib import parse

stand_config = None
my_config = None


def get_config(key):
    global stand_config, my_config
    if stand_config is None:
        stand_config = sublime.load_settings("Preferences.sublime-settings")
    if my_config is None:
        my_config = sublime.load_settings("MyMarkdown.sublime-settings")
    val = stand_config.get(key)
    if val is None:
        val = my_config.get(key)
    return val


def sendmd(view):
    name = view.file_name()
    if name is not None and not name.lower().endswith(tuple(get_config("suffix"))):
        return
    reg = sublime.Region(0, view.size())
    txt = view.substr(reg)
    req = urllib.request.urlopen(
        "http://127.0.0.1:7865/pmd?name=" + parse.quote(name), bytes(txt, "utf-8"))
    req.close()


class MdPreviewCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        # Open preview
        try:
            handle = MyHandle([os.path.dirname(os.path.realpath(__file__)), ])
            server = HttpServer('0.0.0.0', 7865)
            server.setHandle(handle)
            threading.Thread(target=server.run).start()
        except Exception as e:
            pass
        subprocess.Popen('start "" "http://127.0.0.1:7865"', shell=True)
        sendmd(self.view)


class MarkdownListener(sublime_plugin.EventListener):

    def on_modified_async(self, view):
        # 视图发生变化时调用
        sendmd(view)
