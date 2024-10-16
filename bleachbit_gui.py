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

import random
import time
import threading

# third-party imports
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GObject  # nopep8

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
        "Passwords": {"path": "~/.config/edge/Passwords.{randint}", "desc": "Secret username and password"}
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


class BleachBitWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="Prototype of Next-Generation GUI for BleachBit")
        self.set_default_size(1000, 400)

        # Create a vertical box to hold the menubar, toolbar, and panes.
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(vbox)
        self.create_menubar(vbox)
        self.create_toolbar(vbox)

        # Split the window horizontally into two panes
        self.paned = Gtk.Paned()
        self.paned.set_position(200)
        self.paned.set_wide_handle(True)
        vbox.pack_start(self.paned, True, True, 0)
        self.create_options_pane(self.paned)
        self.create_wipe_free_space_pane()
        self.create_file_results_pane()
        self.show_right_pane(self.file_results_vbox)

        # Add status bar
        self.statusbar = Gtk.Statusbar()
        vbox.pack_start(self.statusbar, False, False, 0)

        # Coordinate the abort button
        self.abort_event = threading.Event()

        # Gracefully close any background threads.
        self.connect("destroy", lambda widget: self.abort_event.set())

    def create_menubar(self, vbox):
        """Create a menu bar"""
        menubar = Gtk.MenuBar()

        menu_items = [
            ("File", [
                ("Shred file", None),
                ("Shred folder", None),
                ("Wipe free space", None),
                ("Make chaff", None),
                ("Quit", None),
            ]),
            ("Edit", [
                ("Preferences", None)
            ]),
            ("Help", [
                ("System information", None),
                ("Help", None),
                ("About", None)
            ])
        ]
        for label, submenu_items in menu_items:
            menu = Gtk.Menu()
            for i, (submenu_label, submenu_func) in enumerate(submenu_items):
                item = Gtk.MenuItem()
                item.set_label(submenu_label)
                if submenu_func is not None:
                    item.connect("activate", submenu_func)
                menu.append(item)
            item = Gtk.MenuItem()
            item.set_label(label)
            item.set_submenu(menu)
            menubar.append(item)
        vbox.pack_start(menubar, False, False, 0)

    def create_options_pane(self, paned):
        """Create a pane for cleaning options

        The pane contains a search entry and a two-level TreeView.
        Example options are Firefox: History and Chrome: History.
        """
        # Create a vertical box to hold a search entry and a TreeView
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)

        # Create a search box to filter the options.
        self.search_entry = Gtk.SearchEntry(width_chars=20)
        self.search_entry.set_placeholder_text("Search")
        self.search_entry_text = None
        self.search_entry.connect("changed", self.on_search_entry_changed)

        vbox.pack_start(self.search_entry, False, False, 0)

        # Create a TreeView to display the available cleaning options
        self.treestore_options = Gtk.TreeStore(str, bool)
        self.treeview_options = Gtk.TreeView(model=self.treestore_options)
        self.option_filter = self.treestore_options.filter_new()
        self.option_filter.set_visible_func(self.on_search_changed_filter)
        self.treeview_options.set_model(self.option_filter)
        vbox.pack_start(self.treeview_options, True, True, 0)

        # Create columns for the options
        options_column = Gtk.TreeViewColumn("Option")
        options_renderer = Gtk.CellRendererText()
        options_column.pack_start(options_renderer, True)
        options_column.add_attribute(options_renderer, "text", 0)
        self.treeview_options.append_column(options_column)

        selected_column = Gtk.TreeViewColumn("Selected")
        selected_renderer = Gtk.CellRendererToggle()
        selected_renderer.connect("toggled", self.on_option_toggled)

        selected_column.pack_start(selected_renderer, True)
        selected_column.add_attribute(selected_renderer, "active", 1)
        self.treeview_options.append_column(selected_column)

        # Add some sample data
        self.populate_options_pane()

        paned.add1(vbox)

    def on_option_toggled(self, cell, path):
        """Callback for toggling an option (e.g., Chrome - Cache)

        Toggling a parent option also toggles all its children.
        When a child is toggled on, the parent is also toggled on.
        When a child is toggled off, the parent is also toggled off if all children are toggled off.
        """
        model = self.treeview_options.get_model()
        iter = model.get_iter(path)
        value = not model.get_value(iter, 1)
        model.set_value(iter, 1, value)

        # Update children
        if model.iter_has_child(iter):
            child_iter = model.iter_children(iter)
            while child_iter:
                model.set_value(child_iter, 1, value)
                child_iter = model.iter_next(child_iter)

        # Update parent
        parent_iter = model.iter_parent(iter)
        if parent_iter:
            child_iter = model.iter_children(parent_iter)
            has_active_child = False
            while child_iter:
                if model.get_value(child_iter, 1):
                    has_active_child = True
                    break
                child_iter = model.iter_next(child_iter)
            model.set_value(parent_iter, 1, has_active_child)

    def on_search_entry_changed(self, entry):
        """Callback function for user typing in the options search box."""
        self.search_entry_text = self.search_entry.get_text()
        self.option_filter.refilter()

    def on_search_changed_filter(self, model, iter, data):
        """Callback function for each row in the options TreeView.

        This is called for row to set its visibility.

         Logic is as follows:
         * If the search box is empty, show all rows.
         * Searches are case insenitive.
         * If the search box matches a child (e.g., cookies, cache), show this child and its parent. This may hide its brothers such searching for "cookie" will hide "cache."
         * If the search box matches a parent (e.g., Firefox, Chrome), show this parent and all its children. 
        """

        current_row = model.get_value(iter, 0)
        if not self.search_entry_text:
            return True
        if current_row.lower().find(self.search_entry_text.lower()) != -1:
            return True

        parent_iter = model.iter_parent(iter)
        if parent_iter is not None:
            parent_name = model.get_value(parent_iter, 0)
            if parent_name.lower().find(self.search_entry_text.lower()) != -1:
                return True
        # If the search box matches a child, show this child and its parent
        child_iter = model.iter_children(iter)
        while child_iter is not None:
            child_name = model.get_value(child_iter, 0)
            if child_name.lower().find(self.search_entry_text.lower()) != -1:
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
        toolbar = Gtk.Toolbar()
        toolbar.set_style(Gtk.ToolbarStyle.BOTH)  # Show text and icon.

        self.preview_button = Gtk.ToolButton(
            stock_id=Gtk.STOCK_REFRESH, label="Preview")
        self.preview_button.connect("clicked", lambda widget: threading.Thread(target=self.clean_files_worker, args=(False,)).start())
        toolbar.insert(self.preview_button, 0)

        self.clean_button = Gtk.ToolButton(stock_id=Gtk.STOCK_CLEAR, label="Clean")
        self.clean_button.connect("clicked", lambda widget: threading.Thread(target=self.clean_files_worker, args=(True,)).start())
        toolbar.insert(self.clean_button, 1)

        self.abort_button = Gtk.ToolButton(
            stock_id=Gtk.STOCK_STOP, label="Abort")
        self.abort_button.set_sensitive(False)
        self.abort_button.connect("clicked", lambda widget: self.abort_event.set())
        toolbar.insert(self.abort_button, 2)

        self.skip_list_button = Gtk.ToolButton(
            stock_id=Gtk.STOCK_ADD, label="Skip file")
        self.skip_list_button.connect("clicked", self.on_skip_file_clicked)
        self.skip_list_button.set_tooltip_text(
            "Always skip the selected files, so they are never cleaned.")
        toolbar.insert(self.skip_list_button, 3)
        self.skip_list_button.set_sensitive(False)

        self.wipe_free_space_button = Gtk.ToolButton(
            stock_id=Gtk.STOCK_DELETE, label="Wipe free space")
        self.wipe_free_space_button.connect("clicked", lambda widget: threading.Thread(target=self.wipe_free_space_worker).start())
        toolbar.insert(self.wipe_free_space_button, 4)

        vbox.pack_start(toolbar, False, False, 0)

    def create_file_results_pane(self):
        """Create a pane for search results

        The search pane contains a search box and a TreeView with list of files

        Args:
            paned (Gtk.Paned): The parent pane

        Returns:
            None
        """

        # Create a vertical box to hold the search entry and the scrolled window
        self.file_results_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)

        # Create a search box
        search_entry = Gtk.SearchEntry(width_chars=100)
        search_entry.set_placeholder_text("Search")
        search_entry.connect("changed", self.on_results_search_changed)
        self.file_results_vbox.pack_start(search_entry, False, False, 0)

        # Create a TreeView to display the cleaning results
        self.results_treeview = Gtk.TreeView()
        file_results_scrolled = Gtk.ScrolledWindow()
        file_results_scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        file_results_scrolled.add(self.results_treeview)
        self.file_results_vbox.pack_start(file_results_scrolled, True, True, 0)

        # Create a ListStore to hold the data
        self.results_liststore = Gtk.ListStore(str, str, str, int, str)
        self.results_treeview.set_model(self.results_liststore)

        # Create columns: cleaner, option, filename, file size, action.
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Cleaner", renderer, text=0)
        column.set_sort_column_id(0)
        self.results_treeview.append_column(column)

        column = Gtk.TreeViewColumn("Option", renderer, text=1)
        column.set_sort_column_id(1)
        self.results_treeview.append_column(column)

        column = Gtk.TreeViewColumn("Filename", renderer, text=2)
        column.set_sort_column_id(2)
        self.results_treeview.append_column(column)

        column = Gtk.TreeViewColumn("File size (B)", renderer, text=3)
        column.set_sort_column_id(3)
        column.set_cell_data_func(renderer, lambda column, cell, model, iter, data: cell.set_property('text', format_file_size(model.get_value(iter, 3))))
        self.results_treeview.append_column(column)

        column = Gtk.TreeViewColumn("Action", renderer, text=4)
        column.set_sort_column_id(4)
        self.results_treeview.append_column(column)

        # Allow user to select multple rows for whitelisting.
        self.results_treeview.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)

        # Add a context menu.
        self.results_treeview.connect("button-press-event",
                                      self.on_file_result_context_menu)

        self.results_treeview.get_selection().connect(
            "changed", self.on_selection_changed)

    def create_wipe_free_space_pane(self):
        """Create a pane for wiping free space

        Each row has columns: path name, free space (B), progress bar.
        This function creates a widget without displaying it.
        """

        self.wipe_free_space_liststore = Gtk.ListStore(str, GObject.TYPE_INT64, int)
        self.wipe_free_space_treeview = Gtk.TreeView(model=self.wipe_free_space_liststore)
        path_renderer = Gtk.CellRendererText()
        path_column = Gtk.TreeViewColumn("Path name", path_renderer, text=0)
        path_column.set_sort_column_id(0)
        self.wipe_free_space_treeview.append_column(path_column)

        space_renderer = Gtk.CellRendererText()
        space_column = Gtk.TreeViewColumn("Free space (B)", space_renderer, text=1)
        space_column.set_cell_data_func(space_renderer, lambda column, cell, model, iter, data: cell.set_property('text', format_file_size(model.get_value(iter, 1))))
        space_column.set_sort_column_id(1)
        self.wipe_free_space_treeview.append_column(space_column)

        progress_renderer = Gtk.CellRendererProgress()
        progress_column = Gtk.TreeViewColumn("Progress", progress_renderer, value=2)
        self.wipe_free_space_treeview.append_column(progress_column)

        self.wipe_free_scrolled = Gtk.ScrolledWindow()
        self.wipe_free_scrolled.add(self.wipe_free_space_treeview)

    def show_right_pane(self, right_pane_widget):
        assert hasattr(self, "wipe_free_scrolled")
        right_pane = self.paned.get_child2()
        if right_pane == right_pane_widget:
            return
        if right_pane:
            self.paned.remove(right_pane)
        self.paned.add2(right_pane_widget)
        self.show_all()

    def on_results_search_changed(self, entry):
        """Callback function for search box"""
        self.search_entry_text = entry.get_text()
        self.liststore_filter = self.results_liststore.filter_new()
        self.liststore_filter.set_visible_func(
            self.on_results_search_changed_filter)
        self.sorted_model = Gtk.TreeModelSort(model=self.liststore_filter)
        self.results_treeview.set_model(self.sorted_model)

    def on_results_search_changed_filter(self, model, iter, data):
        if not self.search_entry_text:
            return True
        for i in range(3):
            current_row = model.get_value(iter, i)
            if current_row.lower().find(self.search_entry_text.lower()) != -1:
                return True
        return False

    def on_selection_changed(self, selection):
        """Enable whitelist button on toolbar when 1+ rows are selected"""
        model, paths = selection.get_selected_rows()
        sensitive = len(paths) > 0
        self.skip_list_button.set_sensitive(sensitive)

    def on_copy_path_activated(self, widget, filenames):
        """Copy filename to clipboard"""
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        if len(filenames) == 1:
            self.statusbar.push(0, f"Copied {filenames[0]} to clipboard")
        else:
            self.statusbar.push(
                0, f"Copied {len(filenames)} filenames to clipboard")
        clipboard.set_text('\n'.join(filenames), -1)

    def on_file_result_context_menu(self, widget, event):
        """Show a context menu for file result"""
        # 3 is the right mouse button
        if not event.button == 3:
            return
        selection = self.results_treeview.get_selection()
        model, pathlist = selection.get_selected_rows()
        filenames = []
        for path in pathlist:
            tree_iter = model.get_iter(path)
            filenames.append(model.get_value(tree_iter, 2))
        menu = Gtk.Menu()
        copy_path_item = Gtk.MenuItem.new_with_label("Copy path")
        copy_path_item.connect(
            "activate", self.on_copy_path_activated, filenames)
        menu.append(copy_path_item)
        open_file_location_item = Gtk.MenuItem.new_with_label(
            "Open file location")
        menu.append(open_file_location_item)
        skip_item = Gtk.MenuItem.new_with_label("Always skip this file")
        skip_item.connect("activate", lambda _item: self.on_skip_file_clicked(filenames))
        menu.append(skip_item)
        menu.show_all()
        menu.popup(None, None, None, None, event.button, event.time)
        # True maintains selection of multiple rows.
        return True

    def clean_files_worker(self, is_delete=True):
        """In background thread, run a worker to populate the liststore

        This simulates a worker that cleans the system 
        """
        self.abort_event.clear()
        self.set_toolbar_buttons_working(True, True)
        self.show_right_pane(self.file_results_vbox)
        self.results_liststore.clear()
        for row in self.fake_cleaner_iterator(is_delete):
            if self.abort_event.is_set():
                break
            self.results_liststore.append(row)
        self.set_toolbar_buttons_working(False, True)

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
        self.set_toolbar_buttons_working(True, False)
        self.show_right_pane(self.wipe_free_scrolled)
        wipe_paths = ('/tmp', '~/.cache', '/mnt/external')
        min_size = 1 * 1024 * 1024  # 1 MB
        max_size = 4 * 1024 * 1024 * 1024 * 1024  # 4 TB
        self.wipe_free_space_liststore.clear()
        for wipe_path in wipe_paths:
            free_space_bytes = random.randint(min_size, max_size)
            self.wipe_free_space_liststore.append([wipe_path, free_space_bytes, False])

        for row in self.wipe_free_space_liststore:
            if self.abort_event.is_set():
                break
            path_rate = random.uniform(0.01, 0.1)
            for progress_percent in range(100):
                if self.abort_event.is_set():
                    break
                row[2] = progress_percent
                time.sleep(path_rate)

        self.set_toolbar_buttons_working(False, False)

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

    def on_skip_file_clicked(self, button):
        # Get the selected rows
        selection = self.results_treeview.get_selection()
        model, paths = selection.get_selected_rows()
        for path in paths:
            # Get the filename
            filename = model[path][2]

            print(f"Whitelisted: {filename}")
        if len(paths) == 1:
            self.statusbar.push(0, f"Whitelisted: {filename}")
        else:
            self.statusbar.push(0, f"Whitelisted {len(paths)} file(s)")


if __name__ == "__main__":
    # GObject.threads_init() # Not needed since 3.11
    win = BleachBitWindow()
    win.set_icon_from_file("bleachbit.png")
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
