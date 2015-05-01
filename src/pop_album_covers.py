#!/usr/bin/python
# Copyright (c) 2014-2015 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from gi.repository import Gtk, GLib, Gio, GdkPixbuf

import urllib.request
import urllib.parse
from _thread import start_new_thread

from lollypop.define import Objects, ArtSize, GOOGLE_INC
from lollypop.view_container import ViewContainer

# Show a popover with album covers from the web
class PopAlbumCovers(Gtk.Popover):

    """
        Init Popover ui with a text entry and a scrolled treeview
        @param artist id as int
        @param album id as int
    """
    def __init__(self, artist_id, album_id):
        Gtk.Popover.__init__(self)
        self._album_id = album_id
        self._start = 0

        album = Objects.albums.get_name(album_id)
        artist = Objects.artists.get_name(artist_id)

        self._search = "%s+%s" % (artist, album)

        self._stack = ViewContainer(1000)
        self._stack.show()

        builder = Gtk.Builder()
        builder.add_from_resource(
                    '/org/gnome/Lollypop/PopAlbumCovers.ui')

        self._view = Gtk.FlowBox()
        self._view.set_selection_mode(Gtk.SelectionMode.NONE)
        self._view.connect('child-activated', self._on_activate)
        self._view.set_property('row-spacing', 10)
        self._view.show()

        builder.get_object('viewport').add(self._view)

        self._widget = builder.get_object('widget')
        self._spinner = builder.get_object('spinner')
        self._not_found = builder.get_object('notfound')
        self._stack.add(self._spinner)
        self._stack.add(self._not_found)
        self._stack.add(self._widget)
        self._stack.set_visible_child(self._spinner)
        self.add(self._stack)

    """
        Populate view
    """
    def populate(self):
        self._thread = True
        start_new_thread(self._populate, ())

    """
        Resize popover and set signals callback
    """
    def do_show(self):
        self.set_size_request(700, 400)
        Gtk.Popover.do_show(self)

    """
        Kill thread
    """
    def do_hide(self):
        self._thread = False
        Gtk.Popover.do_hide(self)

#######################
# PRIVATE             #
#######################
    """
        Same as populate()
    """
    def _populate(self):
        self._urls = Objects.art.get_google_arts(self._search)
        if self._urls:
            self._start += GOOGLE_INC
            self._add_pixbufs()
        else:
            GLib.idle_add(self._show_not_found)

    """
        Add urls to the view
    """
    def _add_pixbufs(self):
        if self._urls:
            url = self._urls.pop()
            stream = None
            try:
                response = urllib.request.urlopen(url)
                stream = Gio.MemoryInputStream.new_from_data(
                                                response.read(), None)
            except:
                if self._thread:
                    self._add_pixbufs()
            if stream:
                GLib.idle_add(self._add_pixbuf, stream)
            if self._thread:
                self._add_pixbufs()
        else:
            self._populate()

    """
        Show not found message
    """
    def _show_not_found(self):
        if len(self._view.get_children()) == 0:
            self._stack.set_visible_child(self._not_found)
            self._stack.clean_old_views(self._not_found)

    """
        Add stream to the view
    """
    def _add_pixbuf(self, stream):
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_stream_at_scale(
                                            stream, ArtSize.MONSTER,
                                            ArtSize.MONSTER,
                                            False,
                                            None)
            image = Gtk.Image()
            image.set_from_pixbuf(pixbuf.scale_simple(ArtSize.BIG,
                                                      ArtSize.BIG,
                                                      2))
            image.show()
            self._view.add(image)
        except Exception as e:
            print(e)
            pass
        # Remove spinner if exist
        if self._spinner is not None:
            self._stack.set_visible_child(self._widget)
            self._stack.clean_old_views(self._widget)
            self._spinner = None

    """
        Use pixbuf as cover
        Reset cache and use player object to announce cover change
    """
    def _on_activate(self, flowbox, child):
        pixbuf = child.get_child().get_pixbuf()
        Objects.art.save_album_art(pixbuf, self._album_id)
        Objects.art.clean_album_cache(self._album_id)
        Objects.player.announce_cover_update(self._album_id)
        self.hide()
        self._streams = {}
