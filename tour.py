import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

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

    def add_step(self, widget_name, text):
        self.steps.append((widget_name, text))

    def start(self):
        self.current = 0
        self.show_step()

    def show_step(self):
        if self.popover:
            self.popover.popdown()

        name, text = self.steps[self.current]
        target = self.widget_map[name]

        self.popover = Gtk.Popover(relative_to=target)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_top(10); box.set_margin_bottom(10)
        box.set_margin_start(10); box.set_margin_end(10)

        label = Gtk.Label(label=text)
        next_btn = Gtk.Button(label="Next" if self.current < len(self.steps)-1 else "Done")
        next_btn.connect("clicked", self.next_step)

        box.pack_start(label, False, False, 0)
        box.pack_start(next_btn, False, False, 0)
        box.show_all()

        self.popover.add(box)
        self.popover.popup()

    def next_step(self, _):
        self.current += 1
        if self.current < len(self.steps):
            self.show_step()
        else:
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
