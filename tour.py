import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk

steps = [
    {"widget": "preview_btn",  "text": "Click here to preview the changes"},
    {"widget": "clean_btn",  "text": "Click here to clean the files"},
    {"widget": "menu_btn",  "text": "Access more options here, including preferences"},
]

class TourManager:
    def __init__(self, widget_map):
        self.steps = []
        self.current = 0
        self.widget_map = widget_map  # dict of name -> widget
        self.popover = None
        self.revealer = None
        self.animation_timeout_id = None
        self.animation_step = 0
        self.highlight_overlay = None

    def add_step(self, widget_name, text):
        self.steps.append((widget_name, text))

    def start(self):
        self.current = 0
        self.show_step()

    def stop_animation(self):
        if self.animation_timeout_id:
            GLib.source_remove(self.animation_timeout_id)
            self.animation_timeout_id = None
        if self.revealer:
            self.revealer.set_reveal_child(False)
            self.revealer = None
        if self.highlight_overlay:
            self.highlight_overlay.destroy()
            self.highlight_overlay = None

    def animate_highlight(self):
        if not self.popover or not self.popover.get_visible():
            return False

        self.animation_step = (self.animation_step + 1) % 20
        # Gentle bounce or pulse effect could be added here if we had a drawing area
        # For simplicity in Gtk 3.0 without complex custom drawing,
        # let's just ensure the popover stays aligned or maybe pulse the widget's style
        return True

    def show_step(self):
        self.stop_animation()
        if self.popover:
            self.popover.popdown()
            self.popover.destroy()

        name, text = self.steps[self.current]
        target = self.widget_map[name]

        self.popover = Gtk.Popover(relative_to=target)
        self.popover.set_position(Gtk.PositionType.BOTTOM)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(15); box.set_margin_bottom(15)
        box.set_margin_start(15); box.set_margin_end(15)

        label = Gtk.Label(label=text)
        label.set_line_wrap(True)
        label.set_max_width_chars(30)
        box.pack_start(label, False, False, 0)

        # Button row
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        prev_btn = Gtk.Button(label="Back")
        prev_btn.set_sensitive(self.current > 0)
        prev_btn.connect("clicked", self.prev_step)

        skip_btn = Gtk.Button(label="Skip")
        skip_btn.connect("clicked", self.skip_tour)

        next_btn = Gtk.Button(label="Next" if self.current < len(self.steps)-1 else "Finish")
        next_btn.get_style_context().add_class("suggested-action")
        next_btn.connect("clicked", self.next_step)

        btn_box.pack_start(prev_btn, True, True, 0)
        btn_box.pack_start(skip_btn, True, True, 0)
        btn_box.pack_start(next_btn, True, True, 0)

        box.pack_start(btn_box, False, False, 0)

        self.revealer = Gtk.Revealer()
        self.revealer.set_transition_type(
            Gtk.RevealerTransitionType.SLIDE_DOWN)
        self.revealer.set_transition_duration(500)
        self.revealer.set_reveal_child(False)
        self.revealer.add(box)
        self.revealer.show_all()
        self.popover.add(self.revealer)
        self.popover.popup()
        # Reveal the popover content via Gtk.Revealer after the popover
        # starts presenting, to avoid drawing an empty shell.
        GLib.idle_add(self.revealer.set_reveal_child, True)

        # Start a simple "pulse" animation by toggling a style class, limited to ~2s
        self.animation_step = 0
        def pulse():
            if not self.popover or not self.popover.get_visible() or self.animation_step >= 4:
                target.get_style_context().remove_class("tour-highlight")
                self.animation_timeout_id = None
                return False

            if self.animation_step % 2 == 0:
                target.get_style_context().add_class("tour-highlight")
            else:
                target.get_style_context().remove_class("tour-highlight")

            self.animation_step += 1
            return True

        # CSS for the highlight
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b".tour-highlight { background: rgba(52, 152, 219, 0.3); border: 2px solid #3498db; }")
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        self.animation_timeout_id = GLib.timeout_add(500, pulse)

    def next_step(self, _):
        self.current += 1
        if self.current < len(self.steps):
            self.show_step()
        else:
            self.skip_tour(None)

    def prev_step(self, _):
        if self.current > 0:
            self.current -= 1
            self.show_step()

    def skip_tour(self, _):
        self.stop_animation()
        if self.popover:
            if self.revealer:
                self.revealer.set_reveal_child(False)
            self.popover.popdown()


class MainWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="Tour Demo")
        self.set_default_size(400, 200)

        header = Gtk.HeaderBar(title="Tour Demo")
        header.set_show_close_button(True)

        self.preview_btn = Gtk.Button(label="Preview")
        self.clean_btn = Gtk.Button(label="Clean")
        self.menu_btn = Gtk.Button(label="Menu")

        header.pack_start(self.preview_btn)
        header.pack_start(self.clean_btn)
        header.pack_end(self.menu_btn)

        self.set_titlebar(header)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_top(20)
        box.set_margin_start(20)

        start_tour_btn = Gtk.Button(label="Start Tour")
        start_tour_btn.connect("clicked", self.on_start_tour)
        box.pack_start(start_tour_btn, False, False, 0)

        self.add(box)

        self.widget_map = {
            "preview_btn": self.preview_btn,
            "clean_btn": self.clean_btn,
            "menu_btn": self.menu_btn,
        }

        self.tour = TourManager(self.widget_map)
        for step in steps:
            self.tour.add_step(step["widget"], step["text"])

    def on_start_tour(self, _):
        self.tour.start()


if __name__ == "__main__":
    win = MainWindow()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
