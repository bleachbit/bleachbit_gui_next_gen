#!/usr/bin/env python3
"""
Demo of revealed drop zones in GTK3.

Normal state: Shows a simple UI with a label and button.
When drag is detected: Reveals drop zones that accept files from file manager.
"""

import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib


class RevealDropZonesDemo(Gtk.Window):
    """Demo of revealed drop zones in GTK3"""
    def __init__(self):
        """Initialize the demo window."""
        super().__init__(title="Revealed Drop Zones Demo")
        self.set_default_size(500, 400)
        self.set_border_width(20)

        # Main overlay container
        self.overlay = Gtk.Overlay()
        self.add(self.overlay)

        # === BASE LAYER: Normal UI ===
        self.base_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.overlay.add(self.base_box)

        # Normal state content
        title = Gtk.Label()
        title.set_markup("<big><b>File Organizer</b></big>")
        title.set_margin_bottom(10)
        self.base_box.pack_start(title, False, False, 0)

        description = Gtk.Label(
            label="Drag files or folders from your file manager into this window.\n"
                  "Drop zones will appear when you start dragging."
        )
        description.set_line_wrap(True)
        description.set_justify(Gtk.Justification.CENTER)
        self.base_box.pack_start(description, False, False, 0)

        self.action_button = Gtk.Button(label="Click Me (Unrelated)")
        self.action_button.connect("clicked", self.on_button_clicked)
        self.action_button.set_margin_top(20)
        self.base_box.pack_start(self.action_button, False, False, 0)

        self.status_label = Gtk.Label(label="Status: Ready for drag and drop")
        self.status_label.set_margin_top(20)
        self.base_box.pack_start(self.status_label, False, False, 0)

        # === DROP ZONES (Initially Hidden) ===
        self.drop_zones_revealer = Gtk.Revealer()
        self.drop_zones_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        self.drop_zones_revealer.set_transition_duration(300)
        self.base_box.pack_start(self.drop_zones_revealer, True, True, 0)

        # Container for drop zones
        drop_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        drop_container.set_homogeneous(True)
        drop_container.set_margin_top(30)
        drop_container.set_margin_bottom(30)
        drop_container.set_halign(Gtk.Align.FILL)
        drop_container.set_valign(Gtk.Align.CENTER)
        self.drop_zones_revealer.add(drop_container)

        # Create drop zones: Keep and Shred
        self.zone1 = self.create_drop_zone("Add to keep list", "document-save", "#4a9b4a", "#2d6a2d")
        drop_container.pack_start(self.zone1, True, True, 0)

        self.zone2 = self.create_drop_zone("Shred now", "edit-delete", "#c44", "#922")
        drop_container.pack_start(self.zone2, True, True, 0)

        # === WINDOW-LEVEL DRAG DETECTION ===
        # Set up the window as a drag destination to detect drag enter/leave
        self.drag_dest_set(
            Gtk.DestDefaults.MOTION,
            [Gtk.TargetEntry.new("text/uri-list", 0, 0)],
            Gdk.DragAction.COPY
        )
        self.connect("drag-motion", self.on_window_drag_motion)
        self.connect("drag-leave", self.on_window_drag_leave)

        # === ZONE TARGETS ===
        # Zones handle their own drop events
        self.setup_zone_target(self.zone1, "Keep")
        self.setup_zone_target(self.zone2, "Shred")

        # State tracking
        self.drag_active = False
        self.drag_leave_timeout = None

        self.connect("destroy", Gtk.main_quit)

    def create_drop_zone(self, title, icon_name, active_bg="#4a90d9", active_border="#2a6099"):
        """Create a styled drop zone widget

        Called once per drop zone.
        """
        frame = Gtk.Frame()
        frame.set_shadow_type(Gtk.ShadowType.NONE)

        # Store colors as data for later use
        frame.active_bg = active_bg
        frame.active_border = active_border

        # Container
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_border_width(20)
        frame.add(box)

        # Apply CSS styling
        css = Gtk.CssProvider()
        css.load_from_data(f"""
            frame {{
                background-color: #f0f0f0;
                border-radius: 12px;
                border: 3px dashed #999;
                min-height: 120px;
            }}
            frame.drag-over {{
                background-color: {active_bg};
                border: 3px solid {active_border};
            }}
            frame.drag-over label {{
                color: white;
            }}
        """.encode())
        style_context = frame.get_style_context()
        style_context.add_provider(css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        # Icon
        icon = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.DIALOG)
        box.pack_start(icon, False, False, 0)

        # Title
        label = Gtk.Label()
        label.set_markup(f"<b>{title}</b>")
        box.pack_start(label, False, False, 0)

        # Subtitle
        sub = Gtk.Label(label="Drop files here")
        sub.set_line_wrap(True)
        box.pack_start(sub, False, False, 0)

        return frame

    def setup_zone_target(self, frame, zone_name):
        """Set up a drop zone as a direct drag target."""
        frame.drag_dest_set(
            Gtk.DestDefaults.DROP | Gtk.DestDefaults.MOTION,
            [Gtk.TargetEntry.new("text/uri-list", 0, 0)],
            Gdk.DragAction.COPY
        )
        frame.connect("drag-motion", lambda w, c, x, y, t: self.on_zone_drag_motion(w, c, x, y, t, zone_name))
        frame.connect("drag-leave", lambda w, c, t: self.on_zone_drag_leave(w, c, t, zone_name))
        frame.connect("drag-drop", lambda w, c, x, y, t: self.on_zone_drag_drop(w, c, x, y, t, zone_name))
        frame.connect("drag-data-received", lambda w, c, x, y, d, i, t: self.on_zone_data_received(w, c, x, y, d, i, t, zone_name))

    def on_button_clicked(self, _button):
        """Handle button click (not D&D related)."""
        self.status_label.set_text("Status: Button clicked!")

    def reveal_drop_zones(self):
        """Show the drop zones."""
        if not self.drop_zones_revealer.get_reveal_child():
            self.drop_zones_revealer.set_reveal_child(True)
            # Dim the normal UI
            self.base_box.set_opacity(0.4)

    def hide_drop_zones(self):
        """Hide the drop zones."""
        if self.drop_zones_revealer.get_reveal_child():
            self.drop_zones_revealer.set_reveal_child(False)
            self.base_box.set_opacity(1.0)

    def on_window_drag_motion(self, _widget, context, _x, _y, time):
        """Drag is over the window - reveal zones."""
        if not self.drag_active:
            self.drag_active = True
            self.reveal_drop_zones()

        if self.drag_leave_timeout:
            GLib.source_remove(self.drag_leave_timeout)
            self.drag_leave_timeout = None

        Gdk.drag_status(context, Gdk.DragAction.COPY, time)
        return True

    def on_window_drag_leave(self, _widget, _context, _time):
        """Drag left the window - delay hide to check if still over a zone."""
        if self.drag_leave_timeout:
            GLib.source_remove(self.drag_leave_timeout)
        # Longer timeout to allow holding still over zones
        self.drag_leave_timeout = GLib.timeout_add(800, self.on_drag_leave_timeout)

    def on_drag_leave_timeout(self):
        """After delay, hide zones if drag truly ended."""
        self.drag_active = False
        self.hide_drop_zones()
        self.drag_leave_timeout = None
        return False

    def on_zone_drag_motion(self, widget, context, _x, _y, time, _zone_name):
        """Dragging over a specific zone."""
        # Keep zones revealed while over any zone
        if self.drag_leave_timeout:
            GLib.source_remove(self.drag_leave_timeout)
            self.drag_leave_timeout = None

        style = widget.get_style_context()
        if not style.has_class("drag-over"):
            style.add_class("drag-over")
        Gdk.drag_status(context, Gdk.DragAction.COPY, time)
        return True

    def on_zone_drag_leave(self, widget, _context, _time, _zone_name):
        """Left a specific zone - start timeout to hide zones."""
        widget.get_style_context().remove_class("drag-over")
        # Start leave timeout when leaving a zone (user might be moving to other zone or leaving window)
        if self.drag_leave_timeout:
            GLib.source_remove(self.drag_leave_timeout)
        self.drag_leave_timeout = GLib.timeout_add(600, self.on_drag_leave_timeout)

    def on_zone_drag_drop(self, widget, context, _x, _y, time, _zone_name):
        """Drop on a zone - request data."""
        target = Gdk.Atom.intern("text/uri-list", False)
        widget.drag_get_data(context, target, time)
        return True

    def on_zone_data_received(self, _widget, context, _x, _y, data, _info, time, zone_name):
        """Data received from drop."""
        if data.get_length() < 0:
            Gtk.drag_finish(context, False, False, time)
            return

        uris = data.get_uris()
        if uris:
            file_names = [uri.split("/")[-1] for uri in uris]
            files_str = ", ".join(file_names[:2])
            if len(file_names) > 2:
                files_str += f" and {len(file_names) - 2} more"

            self.status_label.set_text(f"Dropped {len(uris)} file(s) to {zone_name}: {files_str}")
            print(f"Dropped into {zone_name}: {uris}")
            Gtk.drag_finish(context, True, False, time)
        else:
            Gtk.drag_finish(context, False, False, time)

        self.drag_active = False
        self.hide_drop_zones()


def main():
    """Main entry point."""
    win = RevealDropZonesDemo()
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
