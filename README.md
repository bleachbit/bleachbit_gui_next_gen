This is a prototype for next-generation GUI for BleachBit.

This is a video of progress as of October 5, 2024. The major changes are on the right pane, allowing the user to sort and filter the results of the preview or clean. The file results also have a context menu. Thx CrackHub for ideas!

[![Still Image](https://pbs.twimg.com/ext_tw_video_thumb/1842799515738275840/pu/img/cOfR42gxz_3XRSYb.jpg)](https://x.com/bleachbit/status/1842800707142848868)

This is a screen recording of the ![Cookie Manager Dialog](https://github.com/bleachbit/bleachbit/issues/1329#issuecomment-2722944529).
This dialog allows you to manage cookies by website, with options
to search, clear selected cookies, or clear all cookies.

# Known issues

There are many missing features. Most notably, this GUI is not integrated with any cleaners or the file system, and all the information is example data just for show, so it "doesn't do anything."

This is a rough prototype, so expect bugs.

# How to run

The way it runs from source code is similar to regular BleachBit: see [Running BleachBit from source code](https://docs.bleachbit.org/dev/running-from-source-code.html). Linux typically comes with Python and GTK, so simply run `python3 bleachbit_gui.py`. Windows users will need to install Python and GTK: see the link.

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

# License

The license is GNU General Public License version 3 or later.
