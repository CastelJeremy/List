# MIT License

# Copyright (c) 2023 Vlad Krupinski <mrvladus@yandex.ru>

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os
import json
import re
import shutil
import uuid

from gi.repository import GLib, Gio, Adw, Gtk
from __main__ import VERSION, APP_ID


def get_children(obj: Gtk.Widget) -> list[Gtk.Widget]:
    children: list[Gtk.Widget] = []
    child: Gtk.Widget = obj.get_first_child()
    while child:
        children.append(child)
        child = child.get_next_sibling()
    return children


class Animate:
    """Class for creating UI animations using Adw.Animation"""

    @classmethod
    def property(
        self,
        obj: Gtk.Widget,
        prop: str,
        val_from,
        val_to,
        time_ms: int,
    ) -> None:
        """Animate widget property"""

        def callback(value, _) -> None:
            obj.set_property(prop, value)

        animation = Adw.TimedAnimation.new(
            obj,
            val_from,
            val_to,
            time_ms,
            Adw.CallbackAnimationTarget.new(callback, None),
        )
        animation.play()

    @classmethod
    def scroll(
        self, win: Gtk.ScrolledWindow, scroll_down: bool = True, widget=None
    ) -> None:
        """Animate scrolling"""

        adj = win.get_vadjustment()

        def callback(value, _) -> None:
            adj.set_property("value", value)

        if not widget:
            # Scroll to the top or bottom
            scroll_to = adj.get_upper() if scroll_down else adj.get_lower()
        else:
            scroll_to = widget.get_allocation().height + adj.get_value()

        animation = Adw.TimedAnimation.new(
            win,
            adj.get_value(),
            scroll_to,
            250,
            Adw.CallbackAnimationTarget.new(callback, None),
        )
        animation.play()


class GSettings:
    """Class for accessing gsettings"""

    gsettings: Gio.Settings = None
    initialized: bool = False

    def _check_init(self):
        if not self.initialized:
            self.init()

    @classmethod
    def bind(self, setting: str, obj: Gtk.Widget, prop: str) -> None:
        self._check_init(self)
        self.gsettings.bind(setting, obj, prop, 0)

    @classmethod
    def get(self, setting: str):
        self._check_init(self)
        return self.gsettings.get_value(setting).unpack()

    @classmethod
    def set(self, setting: str, gvariant: str, value) -> None:
        self._check_init(self)
        self.gsettings.set_value(setting, GLib.Variant(gvariant, value))

    @classmethod
    def init(self) -> None:
        Log.debug("Initialize GSettings")
        self.initialized = True
        self.gsettings = Gio.Settings.new(APP_ID)


class Log:
    """Logging class"""

    data_dir: str = os.path.join(GLib.get_user_data_dir(), "list")
    log_file: str = os.path.join(data_dir, "log.txt")
    log_old_file: str = os.path.join(data_dir, "log.old.txt")

    @classmethod
    def init(self):
        # Create data dir
        if not os.path.exists(self.data_dir):
            os.mkdir(self.data_dir)
        # Copy old log
        if os.path.exists(self.log_file):
            os.rename(self.log_file, self.log_old_file)
        # Start new log
        self.debug("Starting Errands " + VERSION)

    @classmethod
    def debug(self, msg: str) -> None:
        print(f"\033[33;1m[DEBUG]\033[0m {msg}")
        self._log(self, f"[DEBUG] {msg}")

    @classmethod
    def error(self, msg: str) -> None:
        print(f"\033[31;1m[ERROR]\033[0m {msg}")
        self._log(self, f"[ERROR] {msg}")

    @classmethod
    def info(self, msg: str) -> None:
        print(f"\033[32;1m[INFO]\033[0m {msg}")
        self._log(self, f"[INFO] {msg}")

    def _log(self, msg: str) -> None:
        try:
            with open(self.log_file, "a") as f:
                f.write(msg + "\n")
        except OSError:
            self.error("Can't write to the log file")


class Markup:
    """Class for useful markup functions"""

    @classmethod
    def escape(self, text: str) -> str:
        return GLib.markup_escape_text(text)

    @classmethod
    def add_crossline(self, text: str) -> str:
        return f"<s>{text}</s>"

    @classmethod
    def rm_crossline(self, text: str) -> str:
        return text.replace("<s>", "").replace("</s>", "")

    @classmethod
    def find_url(self, text: str) -> str:
        """Convert urls to markup. Make sure to escape text before calling."""

        string = text
        urls = re.findall(r"(https?://\S+)", string)
        for url in urls:
            string = string.replace(url, f'<a href="{url}">{url}</a>')
        return string


class TaskUtils:
    """Task related functions"""

    @classmethod
    def generate_id(self) -> str:
        """Generate unique immutable id for task"""
        return str(uuid.uuid4())

    @classmethod
    def new_task(
        self,
        text: str,
        id: str = None,
        pid: str = "",
        cmpd: bool = False,
        dltd: bool = False,
    ) -> dict:
        return {
            "id": self.generate_id() if not id else id,
            "parent": pid,
            "text": text,
            "color": "",
            "completed": cmpd,
            "deleted": dltd,
        }


class UserData:
    """Class for accessing data file with user tasks"""

    data_dir: str = os.path.join(GLib.get_user_data_dir(), "list")
    default_data = {"version": VERSION, "tasks": []}
    initialized: bool = False

    @classmethod
    def init(self) -> None:
        Log.debug("Initialize user data")

        # Create data file if not exists
        if not os.path.exists(os.path.join(self.data_dir, "data.json")):
            with open(os.path.join(self.data_dir, "data.json"), "w+") as f:
                json.dump(self.default_data, f)
                Log.debug(
                    f"Create data file at: {os.path.join(self.data_dir, 'data.json')}"
                )
        self.initialized = True

        # Convert old formats
        if self.get()["version"] != VERSION:
            self.convert()
        # Create new file if old is corrupted
        if not self.validate(self.get()):
            Log.error(
                f"Data file is corrupted. Creating backup at {os.path.join(self.data_dir, 'data.old.json')}"
            )
            shutil.copy(
                os.path.join(self.data_dir, "data.json"),
                os.path.join(self.data_dir, "data.old.json"),
            )
            self.set(self.default_data)

    # Load user data from json
    @classmethod
    def get(self) -> dict:
        if not self.initialized:
            self.init()
        try:
            with open(os.path.join(self.data_dir, "data.json"), "r") as f:
                data: dict = json.load(f)
                return data
        except json.JSONDecodeError:
            Log.error(
                f"Can't read data file at: {os.path.join(self.data_dir, 'data.json')}"
            )

    # Save user data to json
    @classmethod
    def set(self, data: dict) -> None:
        with open(os.path.join(self.data_dir, "data.json"), "w") as f:
            json.dump(data, f, indent=4)

    # Validate data json
    @classmethod
    def validate(self, data: str | dict) -> bool:
        Log.debug("Validating data file")
        if type(data) == dict:
            val_data = data
        # Validate JSON
        else:
            try:
                val_data = json.loads(data)
            except json.JSONDecodeError:
                Log.error("Data file is not JSON")
                return False
        # Validate schema
        for key in ["version", "tasks"]:
            if not key in val_data:
                Log.error(f"Data file is not valid. Key doesn't exists: '{key}'")
                return False
        # Validate tasks
        if val_data["tasks"]:
            for task in val_data["tasks"]:
                for key in ["id", "parent", "text", "color", "completed", "deleted"]:
                    if not key in task:
                        Log.error(
                            f"Data file is not valid. Key doesn't exists: '{key}'"
                        )
                        return False
        Log.debug("Data file is valid")
        return True

    # Port tasks from older versions (for updates)
    @classmethod
    def convert(self) -> None:
        Log.debug("Converting data file")

        data: dict = self.get()
        ver: str = data["version"]

        # Versions 44.6.x
        if ver.startswith("44.6"):
            new_tasks: list[dict] = []
            for task in data["tasks"]:
                new_task = {
                    "id": task["id"],
                    "parent": "",
                    "text": task["text"],
                    "color": task["color"],
                    "completed": task["completed"],
                    "deleted": "history" in data and task["id"] in data["history"],
                }
                new_tasks.append(new_task)
                if task["sub"] != []:
                    for sub in task["sub"]:
                        new_sub = {
                            "id": sub["id"],
                            "parent": task["id"],
                            "text": sub["text"],
                            "color": "",
                            "completed": sub["completed"],
                            "deleted": "history" in data
                            and sub["id"] in data["history"],
                        }
                        new_tasks.append(new_sub)
            data["tasks"] = new_tasks
            if "history" in data:
                del data["history"]

        data["version"] = VERSION
        UserData.set(data)
