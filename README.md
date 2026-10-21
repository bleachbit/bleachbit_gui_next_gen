This is an experimental prototype of a next-generation GTK GUI for BleachBit. It has no backend: it is not connected to any cleaners or the file system.

## Why this exists

The traditional BleachBit GTK3 GUI is not pretty, and many users do not find it user friendly. This repository explores what a better one could look like.

## Video demonstration

This video shows progress as of October 5, 2024. The major changes are on the right pane, where the user can sort and filter the results of the preview or clean. The file results also have a context menu. Thx CrackHub for ideas!

[![Still Image](https://pbs.twimg.com/ext_tw_video_thumb/1842799515738275840/pu/img/cOfR42gxz_3XRSYb.jpg)](https://x.com/bleachbit/status/1842800707142848868)

This is a screen recording of the ![Cookie Manager Dialog](https://github.com/bleachbit/bleachbit/issues/1329#issuecomment-2722944529).
The dialog lets you manage cookies by website, with options to search, clear selected cookies, or clear all cookies.

## Known issues

Many features are missing. All the information is example data just for show, so it "doesn't do anything."

This is a rough prototype, so expect bugs.

## How to run

It runs from source code much like regular BleachBit: see [Running BleachBit from source code](https://docs.bleachbit.org/dev/running-from-source-code.html). Linux typically comes with Python and GTK, so simply run `python3 bleachbit_gui.py`. Windows users will need to install Python and GTK: see the link.

How to run on Ubuntu:

```sh
git clone https://github.com/bleachbit/bleachbit_gui_next_gen.git
cd bleachbit_gui_next_gen
sudo apt-get update
sudo apt-get install -y python3-gi python3-gi-cairo gir1.2-gtk-3.0
python3 -m venv venv
source venv/bin/activate
python3 -m pip install --upgrade pip
pip install -r requirements.txt
python3 bleachbit_gui.py
```

## License

The license is GNU General Public License version 3 or later.

## Other BleachBit UI choices

Besides the traditional BleachBit GTK3 GUI and the [command-line interface](https://docs.bleachbit.org/doc/command-line-interface/), users
have the choices below. While they have rough edges, these are working applications
that really clean your system.

| Interface | Platforms | Source | Windows binary |
|---|---|---|---|
| wxPython GUI | Linux, Windows, macOS | [`wx-gui-mvp` branch](https://github.com/bleachbit/bleachbit/tree/wx-gui-mvp) | [Download](https://download.bleachbit.org/ci/#branch=wx-gui-mvp) |
| Text user interface (TUI) | Terminal | [`tui` branch](https://github.com/bleachbit/bleachbit/tree/tui) | [Download](https://download.bleachbit.org/ci/#branch=tui) |

For the TUI, see the [announcement, introduction, and instructions](https://www.bleachbit.org/news/bleachbit-text-user-interface).

For the wxPython GUI, see the [video](https://github.com/bleachbit/bleachbit/issues/2101#issuecomment-4364820295).