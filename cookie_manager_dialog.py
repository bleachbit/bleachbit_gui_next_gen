#!/usr/bin/env python3
"""
Copyright (C) 2025 by Andrew Ziem. All rights reserved.
"""

# standard import
import json
import os
from urllib.parse import urlparse

# third-party import
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk



URI_LIST_TARGET = 0
TEXT_TARGET = 1


class CookieManagerDialog(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Manage Cookies to Keep")
        self.set_default_size(600, 500)
        self.set_border_width(10)
        self.set_position(Gtk.WindowPosition.CENTER)

        # Main vertical box
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(vbox)

        # Instructions label
        instructions = Gtk.Label()
        instructions.set_markup("<b>Select the cookies you want to keep when cleaning cookies across all your browsers.</b>\n<small>Drag a URL from your browser into this window to allow that site's cookies automatically.</small>")
        instructions.set_line_wrap(True)
        instructions.set_xalign(0)  # Left align
        vbox.pack_start(instructions, False, False, 0)

        # Chrome-only notification
        chrome_notification = Gtk.Label()
        chrome_notification.set_markup("<i>Note: Currently only Google Chrome is supported.</i>")
        chrome_notification.set_line_wrap(True)
        chrome_notification.set_xalign(0)  # Left align
        vbox.pack_start(chrome_notification, False, False, 0)

        # Search box
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        vbox.pack_start(search_box, False, False, 0)

        search_label = Gtk.Label(label="Search:")
        search_box.pack_start(search_label, False, False, 0)

        self.search_entry = Gtk.Entry()
        self.search_entry.set_placeholder_text("Filter cookies...")
        self.search_entry.connect("changed", self.on_search_changed)
        search_box.pack_start(self.search_entry, True, True, 0)

        # Create scrollable window for cookie list
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        vbox.pack_start(scrolled, True, True, 0)

        # Create cookie list store: checkbox, domain, name
        self.cookie_store = Gtk.ListStore(bool, str, str)

        # Create filter for the list store
        self.cookie_filter = self.cookie_store.filter_new()
        self.cookie_filter.set_visible_func(self.filter_cookies)

        # Create the TreeView
        self.treeview = Gtk.TreeView(model=self.cookie_filter)
        self.treeview.set_rules_hint(True)  # Alternating row colors

        # Create columns
        renderer_toggle = Gtk.CellRendererToggle()
        renderer_toggle.connect("toggled", self.on_cell_toggled)
        column_toggle = Gtk.TreeViewColumn("", renderer_toggle, active=0)
        self.treeview.append_column(column_toggle)

        renderer_text = Gtk.CellRendererText()
        column_domain = Gtk.TreeViewColumn("Domain", renderer_text, text=1)
        column_domain.set_sort_column_id(1)
        column_domain.set_resizable(True)
        column_domain.set_expand(True)
        self.treeview.append_column(column_domain)

        renderer_text2 = Gtk.CellRendererText()
        column_name = Gtk.TreeViewColumn("Name", renderer_text2, text=2)
        column_name.set_sort_column_id(2)
        column_name.set_resizable(True)
        self.treeview.append_column(column_name)

        # Enable drag-and-drop for URLs
        targets = [
            Gtk.TargetEntry.new('text/uri-list', 0, URI_LIST_TARGET),
            Gtk.TargetEntry.new('text/plain', 0, TEXT_TARGET),
        ]
        self.treeview.drag_dest_set(Gtk.DestDefaults.ALL, targets, Gdk.DragAction.COPY)
        self.treeview.connect("drag-data-received", self.on_drag_data_received)

        scrolled.add(self.treeview)

        # Button box
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        button_box.set_halign(Gtk.Align.END)
        vbox.pack_start(button_box, False, False, 0)

        # Stat label
        self.stat_label = Gtk.Label()
        self.update_stat_label()
        button_box.pack_start(self.stat_label, True, True, 0)

        # Select all / Deselect all buttons
        self.select_all_btn = Gtk.Button.new_with_label("Select All")
        self.select_all_btn.connect("clicked", self.on_select_all_clicked)
        button_box.pack_start(self.select_all_btn, False, False, 0)

        self.deselect_all_btn = Gtk.Button.new_with_label("Deselect All")
        self.deselect_all_btn.connect("clicked", self.on_deselect_all_clicked)
        button_box.pack_start(self.deselect_all_btn, False, False, 0)

        # Action buttons
        self.cancel_btn = Gtk.Button.new_with_label("Cancel")
        self.cancel_btn.connect("clicked", self.on_cancel_clicked)
        button_box.pack_start(self.cancel_btn, False, False, 0)

        self.keep_btn = Gtk.Button.new_with_label("Keep Selected")
        self.keep_btn.get_style_context().add_class("suggested-action")
        self.keep_btn.connect("clicked", self.on_keep_clicked)
        button_box.pack_start(self.keep_btn, False, False, 0)

        # Enable drag-and-drop for URLs to whitelist cookie hostnames
        targets = [
            Gtk.TargetEntry.new('text/uri-list', 0, URI_LIST_TARGET),
            Gtk.TargetEntry.new('text/plain', 0, TEXT_TARGET),
        ]
        self.drag_dest_set(Gtk.DestDefaults.ALL, targets, Gdk.DragAction.COPY)
        self.connect("drag-data-received", self.on_drag_data_received)

        # Load sample cookies for demo
        self.load_sample_cookies()

    def update_stat_label(self):
        total = len(self.cookie_store)
        selected = sum(1 for row in self.cookie_store if row[0])
        visible = sum(1 for row in self.cookie_filter)
        if visible < total:
            self.stat_label.set_text(f"{selected} of {total} cookies selected ({visible} visible)")
        else:
            self.stat_label.set_text(f"{selected} of {total} cookies selected")

    def on_cell_toggled(self, widget, path):
        # Convert path from filter model to child model
        filter_path = Gtk.TreePath.new_from_string(path)
        child_path = self.cookie_filter.convert_path_to_child_path(filter_path)

        # Toggle the checkbox in the child model
        self.cookie_store[child_path][0] = not self.cookie_store[child_path][0]
        self.update_stat_label()

    def on_select_all_clicked(self, widget):
        for row in self.cookie_store:
            row[0] = True
        self.update_stat_label()

    def on_deselect_all_clicked(self, widget):
        for row in self.cookie_store:
            row[0] = False
        self.update_stat_label()

    def on_cancel_clicked(self, widget):
        self.destroy()

    def on_keep_clicked(self, widget):
        whitelist = []
        for row in self.cookie_store:
            if row[0]:  # If cookie is selected to keep
                domain = row[1]
                name = row[2]
                whitelist.append({"domain": domain, "name": name})

        # Save whitelist to file
        config_dir = os.path.expanduser("~/.config/bleachbit")
        os.makedirs(config_dir, exist_ok=True)
        whitelist_file = os.path.join(config_dir, "cookie_whitelist.json")

        with open(whitelist_file, "w") as f:
            json.dump(whitelist, f, indent=2)

        # Show success message
        dialog = Gtk.MessageDialog(
            transient_for=self,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Cookie Whitelist Saved"
        )
        dialog.format_secondary_text(f"{len(whitelist)} cookies saved to whitelist.")
        dialog.run()
        dialog.destroy()
        self.destroy()

    def filter_cookies(self, model, iter, data):
        """Filter function for the cookie list"""
        search_text = self.search_entry.get_text().lower()
        if not search_text:
            return True

        domain = model[iter][1].lower()
        name = model[iter][2].lower()


        return (search_text in domain or
                search_text in name)

    def on_search_changed(self, widget):
        """Called when the search text changes"""
        self.cookie_filter.refilter()
        self.update_stat_label()

    def load_sample_cookies(self):
        # Sample cookies for demonstration
        sample_cookies = [
            {"domain": "google.com", "name": "NID"},
            {"domain": "google.com", "name": "1P_JAR"},
            {"domain": "youtube.com", "name": "VISITOR_INFO1_LIVE"},
            {"domain": "youtube.com", "name": "YSC"},
            {"domain": "amazon.com", "name": "session-id"},
            {"domain": "amazon.com", "name": "session-token"},
            {"domain": "facebook.com", "name": "c_user"},
            {"domain": "facebook.com", "name": "xs"},
            {"domain": "twitter.com", "name": "auth_token"},
            {"domain": "twitter.com", "name": "ct0"},
            {"domain": "microsoft.com", "name": "MUID"},
            {"domain": "microsoft.com", "name": "MC1"},
            {"domain": "reddit.com", "name": "reddit_session"},
            {"domain": "reddit.com", "name": "edgebucket"},
            {"domain": "netflix.com", "name": "NetflixId"},
            {"domain": "netflix.com", "name": "nfvdid"},
            {"domain": "linkedin.com", "name": "li_at"},
            {"domain": "linkedin.com", "name": "lidc"},
            {"domain": "instagram.com", "name": "sessionid"},
            {"domain": "instagram.com", "name": "rur"},
            {"domain": "github.com", "name": "user_session"},
            {"domain": "github.com", "name": "dotcom_user"},
            {"domain": "spotify.com", "name": "sp_dc"},
            {"domain": "spotify.com", "name": "sp_key"},
            {"domain": "ebay.com", "name": "ns1"},
            {"domain": "ebay.com", "name": "npii"},
            {"domain": "twitch.tv", "name": "auth-token"},
            {"domain": "twitch.tv", "name": "persistent"},
            {"domain": "yahoo.com", "name": "Y"},
            {"domain": "yahoo.com", "name": "A3"},
            {"domain": "cloudflare.com", "name": "cf_clearance"},
            {"domain": "nytimes.com", "name": "nyt-geo"},
            {"domain": "walmart.com", "name": "cart-item-count"},
            {"domain": "apple.com", "name": "as_dc"},
        ]

        # Add to list store
        for cookie in sample_cookies:
            self.cookie_store.append([False, cookie["domain"], cookie["name"]])

        # Update stats
        self.update_stat_label()

    def on_drag_data_received(self, _widget, drag_context, _x, _y, selection_data, info, time):
        """Handle drop of hostnames"""
        hostnames = self._extract_hostnames(selection_data, info)
        self._allow_hostnames(hostnames)
        drag_context.finish(bool(hostnames), False, time)

    def _extract_hostnames(self, selection_data, info):
        """Extract hostnames from selection data"""
        hostnames = set()
        candidates = []

        if info == URI_LIST_TARGET:
            uris = selection_data.get_uris()
            if uris:
                candidates.extend(uris)
        else:
            text = selection_data.get_text()
            if text:
                normalized = text.replace('\r', '\n')
                for line in normalized.split('\n'):
                    for token in line.split():
                        candidates.append(token)

        for candidate in candidates:
            hostname = self._hostname_from_candidate(candidate)
            if hostname:
                hostnames.add(hostname)

        return sorted(hostnames)

    def _hostname_from_candidate(self, candidate):
        """Extract hostname from candidate"""
        if not candidate:
            return None

        candidate = candidate.strip()
        if not candidate:
            return None

        parsed = urlparse(candidate)

        if not parsed.scheme and '://' not in candidate:
            if ' ' in candidate:
                return None
            if '.' in candidate:
                # Add http scheme if missing
                parsed = urlparse(f"http://{candidate}")
            else:
                return None

        hostname = parsed.hostname
        if hostname:
            return hostname.lower()
        return None

    def _allow_hostnames(self, hostnames):
        """Allow hostnames"""
        if not hostnames:
            return

        changed = False
        for hostname in hostnames:
            if self._ensure_hostname_allowed(hostname):
                changed = True
            self._focus_on_hostname(hostname)

        if changed:
            self.cookie_filter.refilter()
        self.update_stat_label()

    def _ensure_hostname_allowed(self, hostname):
        """Ensure hostname is allowed"""
        normalized = hostname.lower()
        found = False
        changed = False

        for row in self.cookie_store:
            if row[1].lower() == normalized:
                found = True
                # If in list but not allowed, mark as allowed
                if not row[0]:
                    row[0] = True
                    changed = True

        if not found:
            # Not in list, add it
            self.cookie_store.append([True, normalized, "*"])
            changed = True

        return changed

    def _focus_on_hostname(self, hostname):
        """Focus on newhostname"""
        normalized = hostname.lower()
        child_iter = self.cookie_store.get_iter_first()

        while child_iter:
            if self.cookie_store[child_iter][1].lower() == normalized:
                child_path = self.cookie_store.get_path(child_iter)
                filter_path = self.cookie_filter.convert_child_path_to_path(child_path)
                if filter_path is not None:
                    selection = self.treeview.get_selection()
                    selection.select_path(filter_path)
                    self.treeview.scroll_to_cell(filter_path)
                break
            child_iter = self.cookie_store.iter_next(child_iter)

def main():
    """Main function"""
    win = CookieManagerDialog()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()
