#!/usr/bin/python3
# vim: ts=4:sw=4:expandtab

# BleachBit
# Copyright (C) 2008-2024 Andrew Ziem
# https://www.bleachbit.org
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""


FIXME:
* Feature to deselect individual items in preview results #3 https://github.com/bleachbit/wishlist/issues/3
* Feature to select all cleaning options
* Show multiple warnings at once when enabling cleaning options

"""

# standard library imports
import os
import random
import sys
import time
import threading

# Force the font renderer backend.  Must be set early, before GTK/Pango initialise.
os.environ["PANGOCAIRO_BACKEND"] = "fc"

# third-party imports
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk, Gio, GLib, GObject  # nopep8

cleaner_data = {
    "Chrome": {
        "Cache": {"path": "~/.cache/chrome/{randint}", "desc": "Temporary files"},
        "History": {"path": "~/.config/chrome/History.{randint}", "desc": "Sites you visited"},
        "Cookies": {"path": "~/.config/chrome/Cookies.{randint}", "desc": "Cookies are delicious treats"},
        "Passwords": {"path": "~/.config/chrome/Passwords.{randint}", "desc": "Secret username and password"}
    },
    "Firefox": {
        "Cache": {"path": "~/.config/firefox/Cache.{randint}", "desc": "Temporary files"},
        "History": {"path": "~/.config/firefox/History.{randint}", "desc": "Sites you visited"},
        "Cookies": {"path": "~/.config/firefox/Cookies.{randint}", "desc": "Cookies are delicious treats"},
        "Passwords": {"path": "~/.config/firefox/Passwords.{randint}", "desc": "Secret username and password"}
    },
    "Edge": {
        "Cache": {"path": "~/.config/edge/Cache.{randint}", "desc": "Temporary files"},
        "History": {"path": "~/.config/edge/History.{randint}", "desc": "Sites you visited"},
        "Cookies": {"path": "~/.config/edge/Cookies.{randint}", "desc": "Cookies are delicious treats"},
        "Passwords": {"path": "~/.config/edge/Passwords.{randint}", "desc": "Secret username and password"},
        "GPU Cache": {"path": "~/.config/edge/GPUCache.{randint}", "desc": "GPU rendering cache"},
    },
    "System": {
        "Cache": {"path": "~/.cache/{service_name}/{randint}", "desc": "System Cache"},
        "Logs": {"path": "/var/log/{service_name}/{randint}.log", "desc": "System Logs"},
        "Temporary files": {"path": "/tmp/{service_name}/{randint}.tmp", "desc": "System Temporary files"}
    }
}


def format_file_size(size):
    if size < 1024:
        return f"{size} B"
    elif size < 1024 ** 2:
        return f"{size / 1024:.2f} KB"
    elif size < 1024 ** 3:
        return f"{size / 1024 ** 2:.2f} MB"
    elif size < 1024 ** 4:
        return f"{size / 1024 ** 3:.2f} GB"
    elif size < 1024 ** 5:
        return f"{size / 1024 ** 4:.2f} TB"
    else:
        return f"{size / 1024 ** 5:.2f} PB"


class BleachBitWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app,
                         title="Prototype of Next-Generation GUI for BleachBit",
                         default_width=1000, default_height=400)

        # Create a vertical box to hold the menubar, toolbar, and panes.
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_child(vbox)
        self.create_menubar(vbox)
        self.create_toolbar(vbox)

        # Split the window horizontally into two panes
        self.paned = Gtk.Paned()
        self.paned.set_position(200)
        self.paned.set_wide_handle(True)
        self.paned.set_vexpand(True)
        vbox.append(self.paned)
        self.create_options_pane(self.paned)
        self.create_wipe_free_space_pane()
        self.create_file_results_pane()
        self.show_right_pane(self.file_results_vbox)

        # Add status bar (Gtk.Statusbar removed in GTK4; use a label)
        self.statusbar = Gtk.Label(xalign=0.0)
        self.statusbar.add_css_class("statusbar")
        vbox.append(self.statusbar)

        # Coordinate the abort button
        self.abort_event = threading.Event()

        # Gracefully close any background threads.
        self.connect("close-request", self._on_close_request)

    def _on_close_request(self, _window):
        self.abort_event.set()
        return False  # allow the window to close

    def create_menubar(self, vbox):
        """Create a menu bar using Gio.Menu (GTK4 replacement for Gtk.MenuBar)"""
        menubar_model = Gio.Menu()

        file_menu = Gio.Menu()
        file_menu.append("Shred file", "win.shred-file")
        file_menu.append("Shred folder", "win.shred-folder")
        file_menu.append("Wipe free space", "win.wipe-free-space")
        file_menu.append("Make chaff", "win.make-chaff")
        file_menu.append("Quit", "app.quit")
        menubar_model.append_submenu("File", file_menu)

        edit_menu = Gio.Menu()
        edit_menu.append("Preferences", "win.preferences")
        menubar_model.append_submenu("Edit", edit_menu)

        help_menu = Gio.Menu()
        help_menu.append("System information", "win.system-info")
        help_menu.append("Help", "win.help")
        help_menu.append("About", "win.about")
        menubar_model.append_submenu("Help", help_menu)

        menubar = Gtk.PopoverMenuBar(menu_model=menubar_model)
        vbox.append(menubar)

        # Register placeholder actions so menu items are not grayed out.
        for name in ("shred-file", "shred-folder", "wipe-free-space",
                      "make-chaff", "preferences", "system-info", "help", "about"):
            action = Gio.SimpleAction(name=name)
            self.add_action(action)

    def create_options_pane(self, paned):
        """Create a pane for cleaning options

        The pane contains a search entry and a two-level TreeView.
        Example options are Firefox: History and Chrome: History.
        """
        # Create a vertical box to hold a search entry and a TreeView
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)

        # Create a search box to filter the options.
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search")
        self.options_search_entry_text = None
        self.search_entry.connect("search-changed", self.on_options_search_entry_changed)

        vbox.append(self.search_entry)

        # Create a TreeView to display the available cleaning options
        self.treestore_options = Gtk.TreeStore(str, bool)
        self.option_filter = Gtk.TreeModelFilter(child_model=self.treestore_options)
        self.option_filter.set_visible_func(self.on_options_search_changed_filter)
        self.treeview_options = Gtk.TreeView(model=self.option_filter)
        self.treeview_options.set_vexpand(True)

        # Create scrolled window for options
        options_scrolled = Gtk.ScrolledWindow()
        options_scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        options_scrolled.set_child(self.treeview_options)
        options_scrolled.set_vexpand(True)
        vbox.append(options_scrolled)

        # Create columns for the options
        options_column = Gtk.TreeViewColumn(title="Option")
        options_renderer = Gtk.CellRendererText()
        options_column.pack_start(options_renderer, True)
        options_column.add_attribute(options_renderer, "text", 0)
        self.treeview_options.append_column(options_column)

        selected_column = Gtk.TreeViewColumn(title="Selected")
        selected_renderer = Gtk.CellRendererToggle()
        selected_renderer.connect("toggled", self.on_option_toggled)

        selected_column.pack_start(selected_renderer, True)
        selected_column.add_attribute(selected_renderer, "active", 1)
        self.treeview_options.append_column(selected_column)

        # Add some sample data
        self.populate_options_pane()

        paned.set_start_child(vbox)

    def on_option_toggled(self, _cell, path):
        """Callback for toggling an option (e.g., Chrome - Cache)

        Toggling a parent option also toggles all its children.
        When a child is toggled on, the parent is also toggled on.
        When a child is toggled off, the parent is also toggled off if all children are toggled off.
        """
        filter_model = self.option_filter
        child_path = filter_model.convert_path_to_child_path(Gtk.TreePath.new_from_string(path))
        model = self.treestore_options
        iter = model.get_iter(child_path)
        value = not model[iter][1]
        model[iter][1] = value

        # Update children
        if model.iter_has_child(iter):
            child_iter = model.iter_children(iter)
            while child_iter:
                model[child_iter][1] = value
                child_iter = model.iter_next(child_iter)

        # Update parent
        parent_iter = model.iter_parent(iter)
        if parent_iter:
            child_iter = model.iter_children(parent_iter)
            has_active_child = False
            while child_iter:
                if model[child_iter][1]:
                    has_active_child = True
                    break
                child_iter = model.iter_next(child_iter)
            model[parent_iter][1] = has_active_child

    def on_options_search_entry_changed(self, _entry):
        """Callback function for user typing in the options search box."""
        self.options_search_entry_text = self.search_entry.get_text()
        self.option_filter.refilter()

    def on_options_search_changed_filter(self, model, iter, _data):
        """Callback function for each row in the options TreeView.

        This is called for row to set its visibility.

         Logic is as follows:
         * If the search box is empty, show all rows.
         * Searches are case insenitive.
         * If the search box matches a child (e.g., cookies, cache), show this child and its parent. This may hide its brothers such searching for "cookie" will hide "cache."
         * If the search box matches a parent (e.g., Firefox, Chrome), show this parent and all its children.
        """

        current_row = model[iter][0]
        if not self.options_search_entry_text:
            return True
        search_lower = self.options_search_entry_text.lower()
        if search_lower in current_row.lower():
            return True

        parent_iter = model.iter_parent(iter)
        if parent_iter is not None:
            parent_name = model[parent_iter][0]
            if search_lower in parent_name.lower():
                return True
        # If the search box matches a child, show this child and its parent
        child_iter = model.iter_children(iter)
        while child_iter is not None:
            child_name = model[child_iter][0]
            if search_lower in child_name.lower():
                return True
            child_iter = model.iter_next(child_iter)
        return False

    def populate_options_pane(self):
        """Create example cleaners and options

        This is example data for demonstration.
        """
        for parent, children in cleaner_data.items():
            parent_iter = self.treestore_options.append(None, [parent, True])
            for child in children:
                self.treestore_options.append(parent_iter, [child, True])

    def create_toolbar(self, vbox):
        """Create the main toolbar with buttons"""
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        toolbar.add_css_class("toolbar")

        self.preview_button = Gtk.Button(label="Preview", icon_name="view-refresh-symbolic")
        self.preview_button.connect("clicked", lambda widget: threading.Thread(
            target=self.clean_files_worker, args=(False,)).start())
        toolbar.append(self.preview_button)

        self.clean_button = Gtk.Button(label="Clean", icon_name="edit-clear-all-symbolic")
        self.clean_button.connect("clicked", lambda widget: threading.Thread(
            target=self.clean_files_worker, args=(True,)).start())
        toolbar.append(self.clean_button)

        self.abort_button = Gtk.Button(label="Abort", icon_name="process-stop-symbolic")
        self.abort_button.set_sensitive(False)
        self.abort_button.connect("clicked", lambda widget: self.abort_event.set())
        toolbar.append(self.abort_button)

        self.skip_list_button = Gtk.Button(label="Skip file", icon_name="list-add-symbolic")
        self.skip_list_button.connect("clicked", self.on_skip_file_clicked)
        self.skip_list_button.set_tooltip_text(
            "Always skip the selected files, so they are never cleaned.")
        toolbar.append(self.skip_list_button)
        self.skip_list_button.set_sensitive(False)

        self.wipe_free_space_button = Gtk.Button(label="Wipe free space", icon_name="edit-delete-symbolic")
        self.wipe_free_space_button.connect("clicked", lambda widget: threading.Thread(
            target=self.wipe_free_space_worker).start())
        toolbar.append(self.wipe_free_space_button)

        vbox.append(toolbar)

    def create_file_results_pane(self):
        """Create a pane for file cleaning results

        The results pane contains a search box and a TreeView with list of files
        """

        # Create a vertical box to hold the search entry and the scrolled window
        self.file_results_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)

        # Create a search box
        search_entry = Gtk.SearchEntry()
        search_entry.set_placeholder_text("Search")
        search_entry.set_hexpand(True)
        search_entry.connect("search-changed", self.on_results_search_changed)
        self.file_results_vbox.append(search_entry)

        # Create a TreeView to display the cleaning results
        self.results_treeview = Gtk.TreeView()
        file_results_scrolled = Gtk.ScrolledWindow()
        file_results_scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        file_results_scrolled.set_child(self.results_treeview)
        file_results_scrolled.set_vexpand(True)
        self.file_results_vbox.append(file_results_scrolled)

        # Create a ListStore to hold the data
        self.results_liststore = Gtk.ListStore(str, str, str, int, str)
        self.results_treeview.set_model(self.results_liststore)

        # Create columns: cleaner, option, filename, file size, action.
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(title="Cleaner", cell_renderer=renderer, text=0)
        column.set_sort_column_id(0)
        self.results_treeview.append_column(column)

        column = Gtk.TreeViewColumn(title="Option", cell_renderer=renderer, text=1)
        column.set_sort_column_id(1)
        self.results_treeview.append_column(column)

        column = Gtk.TreeViewColumn(title="Filename", cell_renderer=renderer, text=2)
        column.set_sort_column_id(2)
        self.results_treeview.append_column(column)

        size_renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(title="File size (B)", cell_renderer=size_renderer)
        column.set_sort_column_id(3)
        column.set_cell_data_func(size_renderer, lambda column, cell, model, iter,
                                  data: cell.set_property('text', format_file_size(model[iter][3])))
        self.results_treeview.append_column(column)

        action_renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(title="Action", cell_renderer=action_renderer, text=4)
        column.set_sort_column_id(4)
        self.results_treeview.append_column(column)

        # Allow user to select multple rows for whitelisting.
        selection = self.results_treeview.get_selection()
        selection.set_mode(Gtk.SelectionMode.MULTIPLE)

        # Add a context menu via GestureClick (replaces button-press-event).
        gesture = Gtk.GestureClick(button=3)  # right-click
        gesture.connect("pressed", self.on_file_result_context_menu)
        self.results_treeview.add_controller(gesture)

        selection = self.results_treeview.get_selection()
        selection.connect("changed", self.on_selection_changed)

    def create_wipe_free_space_pane(self):
        """Create a pane for wiping free space

        Each row has columns: path name, free space (B), progress bar.
        This function creates a widget without displaying it.
        """

        self.wipe_free_space_liststore = Gtk.ListStore(str, GObject.TYPE_INT64, int)
        self.wipe_free_space_treeview = Gtk.TreeView(model=self.wipe_free_space_liststore)
        path_renderer = Gtk.CellRendererText()
        path_column = Gtk.TreeViewColumn(title="Path name", cell_renderer=path_renderer, text=0)
        path_column.set_sort_column_id(0)
        self.wipe_free_space_treeview.append_column(path_column)

        space_renderer = Gtk.CellRendererText()
        space_column = Gtk.TreeViewColumn(title="Free space (B)", cell_renderer=space_renderer)
        space_column.set_cell_data_func(space_renderer, lambda column, cell, model, iter,
                                        data: cell.set_property('text', format_file_size(model[iter][1])))
        space_column.set_sort_column_id(1)
        self.wipe_free_space_treeview.append_column(space_column)

        progress_renderer = Gtk.CellRendererProgress()
        progress_column = Gtk.TreeViewColumn(title="Progress", cell_renderer=progress_renderer, value=2)
        self.wipe_free_space_treeview.append_column(progress_column)

        self.wipe_free_scrolled = Gtk.ScrolledWindow()
        self.wipe_free_scrolled.set_child(self.wipe_free_space_treeview)

    def show_right_pane(self, right_pane_widget):
        assert hasattr(self, "wipe_free_scrolled")
        right_pane = self.paned.get_end_child()
        if right_pane == right_pane_widget:
            return
        self.paned.set_end_child(right_pane_widget)

    def on_results_search_changed(self, entry):
        """Callback function for search box in results pane"""
        self.results_search_entry_text = entry.get_text()
        self.results_liststore_filter = self.results_liststore.filter_new()
        self.results_liststore_filter.set_visible_func(
            self.on_results_search_changed_filter)
        self.sorted_model = Gtk.TreeModelSort(model=self.results_liststore_filter)
        self.results_treeview.set_model(self.sorted_model)

    def on_results_search_changed_filter(self, model, iter, _data):
        """
        Filter function for results liststore. Returns True if row should be
        visible, False if it should be hidden.
        """
        if not self.results_search_entry_text:
            return True
        search_lower = self.results_search_entry_text.lower()
        for i in range(3):
            # Compare text in search box to text in columns 0,1,2.
            current_row = model[iter][i]
            if search_lower in current_row.lower():
                return True
        return False

    def on_selection_changed(self, selection):
        """Enable whitelist button on toolbar when 1+ rows are selected"""
        _model, paths = selection.get_selected_rows()
        sensitive = len(paths) > 0
        self.skip_list_button.set_sensitive(sensitive)

    def on_copy_path_activated(self, filenames):
        """Copy filename to clipboard"""
        clipboard = self.get_display().get_clipboard()
        text = '\n'.join(filenames)
        clipboard.set(text)
        if len(filenames) == 1:
            self.statusbar.set_text(f"Copied {filenames[0]} to clipboard")
        else:
            self.statusbar.set_text(f"Copied {len(filenames)} filenames to clipboard")

    def on_file_result_context_menu(self, _gesture, _n_press, x, y):
        """Show a context menu for file result"""
        selection = self.results_treeview.get_selection()
        model, pathlist = selection.get_selected_rows()
        if not pathlist:
            return
        filenames = []
        for path in pathlist:
            tree_iter = model.get_iter(path)
            filenames.append(model[tree_iter][2])

        menu_model = Gio.Menu()
        menu_model.append("Copy path", "win.copy-path")
        menu_model.append("Open file location", "win.open-file-location")
        menu_model.append("Always skip this file", "win.skip-file")

        # Create temporary actions for this context menu invocation.
        copy_action = Gio.SimpleAction(name="copy-path")
        copy_action.connect("activate", lambda action, param: self.on_copy_path_activated(filenames))
        self.add_action(copy_action)

        skip_action = Gio.SimpleAction(name="skip-file")
        skip_action.connect("activate", lambda action, param: self.on_skip_file_clicked(filenames))
        self.add_action(skip_action)

        open_action = Gio.SimpleAction(name="open-file-location")
        self.add_action(open_action)

        popover = Gtk.PopoverMenu(menu_model=menu_model)
        popover.set_parent(self.results_treeview)
        rect = Gdk.Rectangle()
        rect.x, rect.y, rect.width, rect.height = int(x), int(y), 1, 1
        popover.set_pointing_to(rect)
        popover.popup()

    def clean_files_worker(self, is_delete=True):
        """In background thread, run a worker to populate the liststore

        This simulates a worker that cleans the system
        """
        self.abort_event.clear()
        GLib.idle_add(self.set_toolbar_buttons_working, True, True)
        GLib.idle_add(self.show_right_pane, self.file_results_vbox)
        GLib.idle_add(self.results_liststore.clear)
        for row in self.fake_cleaner_iterator(is_delete):
            if self.abort_event.is_set():
                break
            GLib.idle_add(self.results_liststore.append, row)
        GLib.idle_add(self.set_toolbar_buttons_working, False, True)

    def fake_cleaner_iterator(self, is_delete=True):
        """Simulate a worker iterator that cleans the system"""
        num_files = random.randint(5, 100)
        for _ in range(num_files):

            cleaner_name = random.choice(list(cleaner_data.keys()))
            option_name = random.choice(
                list(cleaner_data[cleaner_name].keys()))
            data = cleaner_data[cleaner_name][option_name]
            service_name = random.choice([
                "pancake-flipper",
                "unicorn-tracker",
                "robot-reporter",
                "cloud-catcher",
                "whale-watcher",
                "dragon-dreamer",
                "octopus-oracle",
                "penguin-patrol",
                "koala-keeper",
                "zebra-zapper",
                "taco-teller"])
            filename = data["path"].format(randint=str(random.randint(0, 100)), service_name=service_name)
            size = random.randint(0, int(2e9))
            result_random = random.random()
            if is_delete:
                if result_random < 0.05:
                    result = "error"
                elif result_random < 0.15:
                    result = "deleted"
                else:
                    result = "shred"
            else:
                result = ""

            # Sleep simulates waiting for disk I/O.
            # Delete is slower than preview.
            sleep_time_sec = random.uniform(0.01, 0.2)
            if not is_delete:
                sleep_time_sec = sleep_time_sec/10
            time.sleep(sleep_time_sec)
            yield [cleaner_name, option_name, filename, size, result]

    def wipe_free_space_worker(self):
        """Runs as a background thread to wipe free space"""
        GLib.idle_add(self.set_toolbar_buttons_working, True, False)
        GLib.idle_add(self.show_right_pane, self.wipe_free_scrolled)
        wipe_paths = ('/tmp', '~/.cache', '/mnt/external')
        min_size = 1 * 1024 * 1024  # 1 MB
        max_size = 4 * 1024 * 1024 * 1024 * 1024  # 4 TB
        GLib.idle_add(self.wipe_free_space_liststore.clear)
        for wipe_path in wipe_paths:
            free_space_bytes = random.randint(min_size, max_size)
            GLib.idle_add(self.wipe_free_space_liststore.append,
                          [wipe_path, free_space_bytes, 0])

        # Wait briefly for idle_add calls above to complete before iterating.
        time.sleep(0.1)

        for row in self.wipe_free_space_liststore:
            if self.abort_event.is_set():
                break
            path_rate = random.uniform(0.01, 0.1)
            for progress_percent in range(100):
                if self.abort_event.is_set():
                    break
                GLib.idle_add(self._set_row_progress, row.path, progress_percent)
                time.sleep(path_rate)

        GLib.idle_add(self.set_toolbar_buttons_working, False, False)

    def _set_row_progress(self, path, progress_percent):
        """Set progress on a wipe-free-space row from the main thread."""
        try:
            iter = self.wipe_free_space_liststore.get_iter(path)
            self.wipe_free_space_liststore[iter][2] = progress_percent
        except ValueError:
            pass

    def set_toolbar_buttons_working(self, is_working, is_files_mode):
        """Set the toolbar buttons to a working state or not

        is_working: True if the system is working; False if ready for user input
        is_files_mode: True if the file results pane is showing
        """
        self.abort_event.clear()
        self.abort_button.set_sensitive(is_working)
        self.preview_button.set_sensitive(not is_working)
        self.clean_button.set_sensitive(not is_working)
        self.wipe_free_space_button.set_sensitive(not is_working)
        self.skip_list_button.set_sensitive(not is_working and is_files_mode)

    def on_skip_file_clicked(self, _button):
        # Get the selected rows
        selection = self.results_treeview.get_selection()
        model, paths = selection.get_selected_rows()
        filenames = []
        for path in paths:
            # Get the filename
            filename = model[path][2]
            filenames.append(filename)
            print(f"Whitelisted: {filename}")
        if len(filenames) == 1:
            self.statusbar.set_text(f"Whitelisted: {filenames[0]}")
        elif len(filenames) > 1:
            self.statusbar.set_text(f"Whitelisted {len(filenames)} file(s)")


class BleachBitApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.bleachbit.BleachBit",
                         flags=Gio.ApplicationFlags.DEFAULT_FLAGS)

    def do_activate(self):
        win = BleachBitWindow(self)
        settings = Gtk.Settings.get_default()
        if settings:
            settings.set_property('gtk-application-prefer-dark-theme', True)
        win.present()

    def do_startup(self):
        Gtk.Application.do_startup(self)
        quit_action = Gio.SimpleAction(name="quit")
        quit_action.connect("activate", lambda action, param: self.quit())
        self.add_action(quit_action)


if __name__ == "__main__":
    app = BleachBitApp()
    app.run(sys.argv)
