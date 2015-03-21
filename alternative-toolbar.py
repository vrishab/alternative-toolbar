# -*- Mode: python; coding: utf-8; tab-width: 4; indent-tabs-mode: nil; -*-
#
# Copyright (C) 2014 - fossfreedom
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301  USA.

# define plugin

from datetime import datetime, date

from gi.repository import Gtk
from gi.repository import GObject
from gi.repository import Peas
from gi.repository import PeasGtk
from gi.repository import RB
from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import GdkPixbuf
from gi.repository import Gio

from alttoolbar_rb3compat import gtk_version
from alttoolbar_rb3compat import ActionGroup
from alttoolbar_rb3compat import ApplicationShell
import rb
import math


view_menu_ui = """
<ui>
  <menubar name="MenuBar">
    <menu name="ViewMenu" action="View">
        <menuitem name="Show Toolbar" action="ToggleToolbar" />
    </menu>
  </menubar>
</ui>
"""

view_seek_menu_ui = """
<ui>
  <menubar name="MenuBar">
    <menu name="ViewMenu" action="View">
        <menuitem name="SeekBackward" action="SeekBackward" />
        <menuitem name="SeekForward" action="SeekForward" />
    </menu>
  </menubar>
</ui>
"""

seek_backward_time = 5
seek_forward_time = 10

class GSetting:
    '''
    This class manages the different settings that the plugin has to
    access to read or write.
    '''
    # storage for the instance reference
    __instance = None

    class __impl:
        """ Implementation of the singleton interface """
        # below public variables and methods that can be called for GSetting
        def __init__(self):
            '''
            Initializes the singleton interface, assigning all the constants
            used to access the plugin's settings.
            '''
            self.Path = self._enum(
                PLUGIN='org.gnome.rhythmbox.plugins.alternative_toolbar')
                
            self.PluginKey = self._enum(
                DISPLAY_TYPE='display-type',
                START_HIDDEN='start-hidden',
                SHOW_COMPACT='show-compact',
                PLAYING_LABEL='playing-label',
                VOLUME_CONTROL='volume-control'
            )
            
            self.setting = {}

        def get_setting(self, path):
            '''
            Return an instance of Gio.Settings pointing at the selected path.
            '''
            try:
                setting = self.setting[path]
            except:
                self.setting[path] = Gio.Settings.new(path)
                setting = self.setting[path]

            return setting

        def get_value(self, path, key):
            '''
            Return the value saved on key from the settings path.
            '''
            return self.get_setting(path)[key]

        def set_value(self, path, key, value):
            '''
            Set the passed value to key in the settings path.
            '''
            self.get_setting(path)[key] = value

        def _enum(self, **enums):
            '''
            Create an enumn.
            '''
            return type('Enum', (), enums)

    def __init__(self):
        """ Create singleton instance """
        # Check whether we already have an instance
        if GSetting.__instance is None:
            # Create and remember instance
            GSetting.__instance = GSetting.__impl()

        # Store instance reference as the only member in the handle
        self.__dict__['_GSetting__instance'] = GSetting.__instance

    def __getattr__(self, attr):
        """ Delegate access to implementation """
        return getattr(self.__instance, attr)

    def __setattr__(self, attr, value):
        """ Delegate access to implementation """
        return setattr(self.__instance, attr, value)


class Preferences(GObject.Object, PeasGtk.Configurable):
    '''
    Preferences for the Plugins. It holds the settings for
    the plugin and also is the responsible of creating the preferences dialog.
    '''
    __gtype_name__ = 'AlternativeToolbarPreferences'
    object = GObject.property(type=GObject.Object)


    def __init__(self):
        '''
        Initialises the preferences, getting an instance of the settings saved
        by Gio.
        '''
        GObject.Object.__init__(self)
        self.gs = GSetting()
        self.plugin_settings = self.gs.get_setting(self.gs.Path.PLUGIN)
        
    def do_create_configure_widget(self):
        '''
        Creates the plugin's preferences dialog
        '''
        print("DEBUG - create_display_contents")
        # create the ui
        self._first_run = True

        builder = Gtk.Builder()
        builder.add_from_file(rb.find_plugin_file(self,
                                                  'ui/altpreferences.ui'))
        builder.connect_signals(self)

        # bind the toggles to the settings
        start_hidden = builder.get_object('start_hidden_checkbox')
        self.plugin_settings.bind(self.gs.PluginKey.START_HIDDEN,
                           start_hidden, 'active', Gio.SettingsBindFlags.DEFAULT)

        show_compact = builder.get_object('show_compact_checkbox')
        self.plugin_settings.bind(self.gs.PluginKey.SHOW_COMPACT,
                           show_compact, 'active', Gio.SettingsBindFlags.DEFAULT)

        self.display_type = self.plugin_settings[self.gs.PluginKey.DISPLAY_TYPE]
        self.auto_radiobutton = builder.get_object('auto_radiobutton')
        self.headerbar_radiobutton = builder.get_object('headerbar_radiobutton')
        self.toolbar_radiobutton = builder.get_object('toolbar_radiobutton')

        playing_label = builder.get_object('playing_label_checkbox')
        self.plugin_settings.bind(self.gs.PluginKey.PLAYING_LABEL,
                           playing_label, 'active', Gio.SettingsBindFlags.DEFAULT)

        volume_control = builder.get_object('volume_control_checkbox')
        self.plugin_settings.bind(self.gs.PluginKey.VOLUME_CONTROL,
                           volume_control, 'active', Gio.SettingsBindFlags.DEFAULT)

        if self.display_type == 0:
            self.auto_radiobutton.set_active(True)
        elif self.display_type == 1:
            self.headerbar_radiobutton.set_active(True)
        else:
            self.toolbar_radiobutton.set_active(True)

        self._first_run = False

        return builder.get_object('preferences_box')

    def on_display_type_radiobutton_toggled(self, button):
        if self._first_run:
            return

        if button.get_active():
            if button == self.auto_radiobutton:
                self.plugin_settings[self.gs.PluginKey.DISPLAY_TYPE] = 0
            elif button == self.headerbar_radiobutton:
                self.plugin_settings[self.gs.PluginKey.DISPLAY_TYPE] = 1
            else:
                self.plugin_settings[self.gs.PluginKey.DISPLAY_TYPE] = 2


class AltToolbarPlugin(GObject.Object, Peas.Activatable):
    '''
    Main class of the plugin. Manages the activation and deactivation of the
    plugin.
    '''
    __gtype_name = 'AltToolbarPlugin'
    object = GObject.property(type=GObject.Object)
    display_page_tree_visible = GObject.property(type=bool, default=False)
    show_album_art = GObject.property(type=bool, default=False)
    show_song_position_slider = GObject.property(type=bool, default=False)
    playing_label = GObject.property(type=bool, default=False)
    
    # signals
    # toolbar-visibility - bool parameter True = visible, False = not visible
    __gsignals__ = {
        'toolbar-visibility': (GObject.SIGNAL_RUN_LAST, None, (bool,))
    }

    # Builder releated utility functions... ####################################

    def load_builder_content(self, builder):
        if ( not hasattr(self, "__builder_obj_names") ):
            self.__builder_obj_names = list()

        for obj in builder.get_objects():
            if ( isinstance(obj, Gtk.Buildable) ):
                name = Gtk.Buildable.get_name(obj).replace(' ', '_')
                self.__dict__[name] = obj
                self.__builder_obj_names.append(name)

    def connect_builder_content(self, builder):
        builder.connect_signals_full(self.connect_builder_content_func, self)

    def connect_builder_content_func(self,
                                     builder,
                                     object,
                                     sig_name,
                                     handler_name,
                                     conn_object,
                                     flags,
                                     target):
        handler = None

        h_name_internal = "_sh_" + handler_name.replace(" ", "_")

        if ( hasattr(target, h_name_internal) ):
            handler = getattr(target, h_name_internal)
        else:
            handler = eval(handler_name)

        object.connect(sig_name, handler)

    def purge_builder_content(self):
        for name in self.__builder_obj_names:
            o = self.__dict__[name]
            if ( isinstance(o, Gtk.Widget) ):
                o.destroy()
            del self.__dict__[name]

        del self.__builder_obj_names


    def __init__(self):
        '''
        Initialises the plugin object.
        '''
        GObject.Object.__init__(self)
        self.appshell = None
        self.sh_psc = self.sh_op = self.sh_pc = None

    def do_activate(self):
        '''
        Called by Rhythmbox when the plugin is activated. It creates the
        plugin's source and connects signals to manage the plugin's
        preferences.
        '''

        self.shell = self.object
        self.db = self.shell.props.db
        self.main_window = self.shell.props.window

        # Prepare internal variables
        self.song_duration = 0
        self.cover_pixbuf = None
        self.entry = None
        
        self.toolbars={}

        # Prepare Album Art Displaying
        self.album_art_db = GObject.new(RB.ExtDB, name="album-art")

        self.rb_toolbar = self.find(self.shell.props.window,
                                    'main-toolbar', 'by_id')

        builder = Gtk.Builder()
        self.gs = GSetting()
        self.plugin_settings = self.gs.get_setting(self.gs.Path.PLUGIN)
        
        # get values from gsettings
        display_type = self.plugin_settings[self.gs.PluginKey.DISPLAY_TYPE]
        self.volume_control = self.plugin_settings[self.gs.PluginKey.VOLUME_CONTROL]
        self.show_compact_toolbar = self.plugin_settings[self.gs.PluginKey.SHOW_COMPACT]

        default = Gtk.Settings.get_default()

        if display_type == 0:
            if (not default.props.gtk_shell_shows_app_menu) or default.props.gtk_shell_shows_menubar:
                display_type = 2
            else:
                display_type = 1

        print("display type %d" % display_type)

        ui = rb.find_plugin_file(self, 'ui/alttoolbar.ui')
        builder.add_from_file(ui)

        self.load_builder_content(builder)
        self.connect_builder_content(builder)

        what, width, height = Gtk.icon_size_lookup(Gtk.IconSize.SMALL_TOOLBAR)

        self.icon_width = width

        self.appshell = ApplicationShell(self.shell)

        if display_type == 1:
            self._setup_headerbar()
            self._setup_searchbar()
            self._setup_playbar()
            self.shell.props.db.connect('load-complete', self._load_complete)

        if display_type == 2:
            self._setup_compactbar()

        if self.volume_control:
            self.volume_button.bind_property("value", self.shell.props.shell_player, "volume",
                                             Gio.SettingsBindFlags.DEFAULT)
            self.volume_button.props.value = self.shell.props.shell_player.props.volume
        elif not self.show_compact_toolbar and display_type == 2:
            self.volume_button = self.find(self.rb_toolbar, 'GtkVolumeButton', 'by_id')
            
        self.volume_button.set_visible(self.volume_control)
        
        self.shell_player = self.shell.props.shell_player

        self._add_menu_options()
        self._connect_signals()
        self._connect_properties()

		# Bring Builtin Actions to plugin
        for (a, b) in ((self.play_button, "play"),
                       (self.prev_button, "play-previous"),
                       (self.next_button, "play-next"),
                       (self.repeat_toggle, "play-repeat"),
                       (self.shuffle_toggle, "play-shuffle")):
            a.set_action_name("app." + b)
            if b == "play-repeat" or b == "play-shuffle":
                # for some distros you need to set the target_value
                # for others this would actually disable the action
                # so work around this by testing if the action is disabled
                # then reset the action
                a.set_action_target_value(GLib.Variant("b", True))
                print (a.get_sensitive())
                if not a.get_sensitive():
                    a.set_detailed_action_name("app."+b)
        
        # allow other plugins access to this toolbar
        self.shell.alternative_toolbar = self
        
    def _load_complete(self, *args):
        self._hide_toolbar_controls()

    def _add_menu_options(self):
        self.seek_action_group = ActionGroup(self.shell, 'AltToolbarPluginSeekActions')
        self.seek_action_group.add_action(func=self.on_skip_backward,
                                            action_name='SeekBackward', label=_("Seek Backward"),
                                            action_type='app', accel="<Alt>Left",
                                            tooltip=_("Seek backward, in current track, by 5 seconds."))
        self.seek_action_group.add_action(func=self.on_skip_forward,
                                            action_name='SeekForward', label=_("Seek Forward"),
                                            action_type='app', accel="<Alt>Right",
                                            tooltip=_("Seek forward, in current track, by 10 seconds."))
        self.appshell.insert_action_group(self.seek_action_group)
        self.appshell.add_app_menuitems(view_seek_menu_ui, 'AltToolbarPluginSeekActions', 'view')


    def _connect_properties(self):
        self.plugin_settings.bind(self.gs.PluginKey.PLAYING_LABEL, self, 'playing_label',
                           Gio.SettingsBindFlags.GET)
        
    def _connect_signals(self):
        self.sh_display_page_tree = self.shell.props.display_page_tree.connect(
            "selected", self.on_page_change
        )

        self.sh_tb = self.toolbar_button.connect('clicked', self._sh_on_toolbar_btn_clicked)

        self.sh_psc = self.shell_player.connect("playing-song-changed",
                                                self._sh_on_song_change)

        self.sh_op = self.shell_player.connect("elapsed-changed",
                                               self._sh_on_playing)

        self.sh_pc = self.shell_player.connect("playing-changed",
                                               self._sh_on_playing_change)

        self.sh_pspc = self.shell_player.connect("playing-song-property-changed",
                                                 self._sh_on_song_property_changed)

        self.rb_settings = Gio.Settings.new('org.gnome.rhythmbox')
        # tried to connect directly to changed signal but never seems to be fired
        # so have to use bind and notify method to detect key changes
        self.rb_settings.bind('display-page-tree-visible', self, 'display_page_tree_visible',
                     Gio.SettingsBindFlags.GET)
        self.sh_display_page = self.connect('notify::display-page-tree-visible', self.display_page_tree_visible_settings_changed)

        self.sh_sb = self.sidepane_button.connect('clicked', self._sh_on_sidepane_btn_clicked)

        self.rb_settings.bind('show-album-art', self, 'show_album_art',
                     Gio.SettingsBindFlags.GET)
        self.connect('notify::show-album-art', self.show_album_art_settings_changed)
        self.show_album_art_settings_changed(None)

        self.rb_settings.bind('show-song-position-slider', self, 'show_song_position_slider',
                           Gio.SettingsBindFlags.GET)
        self.connect('notify::show-song-position-slider', self.show_song_position_slider_settings_changed)
        self.show_song_position_slider_settings_changed(None)

        self.display_page_tree_visible_settings_changed(None)
        
    def _setup_searchbar(self):
        
        self.search_bar = Gtk.SearchBar.new()
        #entry = Gtk.Entry.new()
        #self.search_bar.add(entry)
        #self.search_bar.connect_entry(entry)
        self.search_bar.show_all()
        self.shell.add_widget(self.search_bar,
                                      RB.ShellUILocation.MAIN_TOP, expand=False, fill=False)
                           
        #self.search_bar.set_search_mode(True)

    def _setup_playbar(self):
        box = self.find(self.shell.props.window,
                                    'GtkBox', 'by_name')
        box.pack_start(self.small_bar, False, True, 0)
        box.reorder_child(self.small_bar, 3)
        
        self.small_bar.show_all()
            
    def _setup_compactbar(self):
        self.toggle_action_group = ActionGroup(self.shell, 'AltToolbarPluginActions')
        self.toggle_action_group.add_action(func=self.toggle_visibility,
                                            action_name='ToggleToolbar', label=_("Show Toolbar"),
                                            action_state=ActionGroup.TOGGLE,
                                            action_type='app', accel="<Ctrl>t",
                                            tooltip=_("Show or hide the main toolbar"))
        self.appshell.insert_action_group(self.toggle_action_group)
        self.appshell.add_app_menuitems(view_menu_ui, 'AltToolbarPluginActions', 'view')
        action = self.toggle_action_group.get_action('ToggleToolbar')

        start_hidden = self.plugin_settings[self.gs.PluginKey.START_HIDDEN]

        self.window_control_item.add(self._window_controls())
        
        if not start_hidden and self.show_compact_toolbar:
            self.shell.add_widget(self.small_bar,
                                 RB.ShellUILocation.MAIN_TOP, expand=False, fill=False)
            self.small_bar.show_all()
            self.rb_toolbar.hide()
            action.set_active(True)
            print("not hidden but compact")
        elif start_hidden:
            self.rb_toolbar.hide()
            print("hidden")
        else:
            action.set_active(True)
            return
            
    def _hide_toolbar_controls(self):
        self._sh_on_toolbar_btn_clicked() #used to hide the source bar
        #if not self.shell.props.selected_page:
        #    return

        if not self.shell.props.selected_page in self.toolbars:
            toolbar = self.find(self.shell.props.selected_page, 'RBSourceToolbar', 'by_name')
            
            if not toolbar:
                return

            elements = { 'GtkMenuButton',
                         'GtkSeparator',
                         'GtkToggleButton',
                         'GtkButton'}

            for element in elements:
                while True:
                    found_element = self.find(toolbar, element, 'by_name', find_only_visible=True)
                    if found_element:
                        found_element.set_visible(False)
                    else:
                        break
                
            builder = Gtk.Builder()
            ui = rb.find_plugin_file(self, 'ui/altlibrary.ui')
            builder.add_from_file(ui)

            self.load_builder_content(builder)
            
            #self.library_search_togglebutton.connect('toggled', self._sh_on_toolbar_btn_clicked)
            self.headerbar.set_custom_title(self.library_box) 

            
            setting = Gio.Settings.new('org.gnome.rhythmbox.sources')
            browser_view = setting['browser-views']
            print (browser_view)
            if browser_view == 'artists-albums':
                view_name = "Artists and albums"
            elif browser_view == 'genres-artists':
                view_name = "Genres and artists"
            elif browser_view == 'genres-artists-albums':
                view_name = "Genres, artists and albums"
            else:
                view_name = "Categories"
            
            view_name = "Categories" #hard-code
            self.library_browser_radiobutton.set_label(view_name)  
            
            self.library_browser_radiobutton.connect('toggled', self._library_radiobutton_toggled)
            self.library_song_radiobutton.connect('toggled', self._library_radiobutton_toggled)
            
            self.search = self.find(toolbar, 'RBSearchEntry', 'by_name')
            entry=self.find(self.search, 'GtkEntry', 'by_name')
            toolbar.remove(self.search)
        
            self.search_bar.add(self.search)
            self.search_bar.connect_entry(entry)
            
            self.search_button = Gtk.ToggleButton.new()
            image = Gtk.Image.new_from_icon_name("preferences-system-search-symbolic", Gtk.IconSize.SMALL_TOOLBAR)
            self.search_button.add(image)
            
            self.end_box.add(self.search_button)
            self.end_box.reorder_child(self.search_button, 0)
            self.search_button.show_all()
            self.search_button.connect('toggled', self._search_button_toggled)
            #self.headerbar.pack_end(self.search)
            
    def _search_button_toggled(self, *args):
        self.search_bar.set_search_mode(self.search_button.get_active())
             
            
    def _library_radiobutton_toggled(self, toggle_button):
        if not hasattr(self, 'library_song_radiobutton'):
            return #kludge = fix this later
            
        val = True
        if self.library_song_radiobutton.get_active():
            val = False
            
        self.shell.props.selected_page.props.show_browser = val
    def _window_controls(self):
        self.window_box = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 0)
        
        self.toolbar_button = Gtk.Button.new_from_icon_name("go-up-symbolic", self.icon_width)
        self.toolbar_button.set_relief(Gtk.ReliefStyle.NONE)
        #self.window_box.add(self.toolbar_button)

        self.sidepane_button = Gtk.Button.new_from_icon_name("go-next-symbolic", self.icon_width)
        self.sidepane_button.set_relief(Gtk.ReliefStyle.NONE)
        #self.window_box.add(self.sidepane_button)
        
        image = self.toolbar_button.get_image()
        if not image:
            image = self.toolbar_button.get_child()

        image.set_pixel_size((self.icon_width / 2))

        image = self.sidepane_button.get_image()
        if not image:
            image = self.sidepane_button.get_child()

        image.set_pixel_size((self.icon_width / 2))

        return self.window_box

    def _setup_headerbar(self):
        default = Gtk.Settings.get_default()
        self.headerbar = Gtk.HeaderBar.new()
        self.headerbar.set_show_close_button(True)
        
        # required for Gtk 3.14 to stop RB adding a title to the header bar
        #empty = Gtk.DrawingArea.new()
        #self.headerbar.set_custom_title(empty)
        
        self.main_window.set_titlebar(self.headerbar)  # this is needed for gnome-shell to replace the decoration
        self.rb_toolbar.hide()
        
        self.headerbar.pack_start(self._window_controls())

        self.end_box = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 0)
        
        if (not default.props.gtk_shell_shows_app_menu) or default.props.gtk_shell_shows_menubar:
        
            # for environments that dont support app-menus
            menu_button = Gtk.MenuButton.new()
            menu_button.set_relief(Gtk.ReliefStyle.NONE)
            if gtk_version() >= 3.14:
                symbol = "open-menu-symbolic"
            else:
                symbol = "emblem-system-symbolic"

            image = Gtk.Image.new_from_icon_name(symbol, Gtk.IconSize.SMALL_TOOLBAR)
            menu_button.add(image)
            menu = self.shell.props.application.get_shared_menu('app-menu')
            menu_button.set_menu_model(menu)
            self.end_box.add(menu_button)

        self.headerbar.pack_end(self.end_box)
        self.headerbar.show_all()

    
    def on_skip_backward( self, *args ):
        sp = self.object.props.shell_player
        if( sp.get_playing()[1] ):
            seek_time = sp.get_playing_time()[1] - seek_backward_time
            print (seek_time)
            if( seek_time < 0 ): seek_time = 0

            print (seek_time)
            sp.set_playing_time( seek_time )

    def on_skip_forward( self, *args ):
        sp = self.object.props.shell_player
        if( sp.get_playing()[1] ):
            seek_time = sp.get_playing_time()[1] + seek_forward_time
            song_duration = sp.get_playing_song_duration()
            if( song_duration > 0 ): #sanity check
                if( seek_time > song_duration ): seek_time = song_duration

                sp.set_playing_time( seek_time )

    def show_song_position_slider_settings_changed(self, *args):
        self.song_box.set_visible(self.show_song_position_slider)

    def display_page_tree_visible_settings_changed(self, *args):

        if self.display_page_tree_visible:
            image_name = 'go-next-symbolic'
        else:
            image_name = 'go-previous-symbolic'

        image = self.sidepane_button.get_image()
        if not image:
            image = self.sidepane_button.get_child()

        image.props.icon_name = image_name

    def show_album_art_settings_changed(self, *args):
        self.album_cover.set_visible(self.show_album_art)

    def on_page_change(self, display_page_tree, page):
        print ("page changed")
        toolbar = self.find(page, 'RBSourceToolbar', 'by_name')
         
        # self.current_page = page
        image = self.toolbar_button.get_image()
        if not image:
            image = self.toolbar_button.get_child()

        if image.props.icon_name == 'go-up-symbolic':
            visible = True
        else:
            visible = False

        if toolbar:
            print("found")
            toolbar.set_visible(visible)
        else:
            print("not found")
        
        self._library_radiobutton_toggled(None)
        
        self.emit('toolbar-visibility', visible)

    # Couldn't find better way to find widgets than loop through them
    def find(self, node, search_id, search_type, find_only_visible=None):
        print(node.get_name())
        if isinstance(node, Gtk.Buildable):
            if search_type == 'by_id':
                if Gtk.Buildable.get_name(node) == search_id:
                    if find_only_visible == None or (find_only_visible and node.get_visible() == True):
                        return node
            elif search_type == 'by_name':
                if node.get_name() == search_id:
                    if find_only_visible == None or (find_only_visible and node.get_visible() == True):
                        return node

        if isinstance(node, Gtk.Container):
            for child in node.get_children():
                ret = self.find(child, search_id, search_type, find_only_visible)
                if ret:
                    return ret
        return None

    def do_deactivate(self):
        '''
        Called by Rhythmbox when the plugin is deactivated. It makes sure to
        free all the resources used by the plugin.
        '''
        if self.sh_op:
            self.shell_player.disconnect(self.sh_op)
            self.shell_player.disconnect(self.sh_psc)
            self.shell_player.disconnect(self.sh_pc)
            self.shell_player.disconnect(self.sh_pspc)
            self.disconnect(self.sh_display_page)
            self.shell.props.display_page_tree.disconnect(self.sh_display_page_tree)
            del self.shell_player

        if self.appshell:
            self.appshell.cleanup()
        self.rb_toolbar.set_visible(True)

        self.purge_builder_content()
        del self.shell
        del self.db

    def toggle_visibility(self, action, param=None, data=None):
        print("toggle_visibility")
        action = self.toggle_action_group.get_action('ToggleToolbar')

        if action.get_active():
            if self.show_compact_toolbar:
                print("show_compact")
                self.shell.add_widget(self.small_bar,
                                      RB.ShellUILocation.MAIN_TOP, expand=False, fill=False)
                self.small_bar.show_all()
                self.volume_button.set_visible(self.volume_control)

            else:
                print("show full")
                self.rb_toolbar.set_visible(True)
        else:
            if self.show_compact_toolbar:
                print("hide compact")
                self.shell.remove_widget(self.small_bar,
                                         RB.ShellUILocation.MAIN_TOP)
            else:
                print("hide full")
                self.rb_toolbar.set_visible(False)

    def display_song(self, entry):
        self.entry = entry

        self.cover_pixbuf = None
        self.album_cover.clear()

        if ( entry is None ):
            self.song_button_label.set_text("")

        else:
            stream_title = self.shell.props.db.entry_request_extra_metadata(entry, RB.RHYTHMDB_PROP_STREAM_SONG_TITLE)
            stream_artist = self.shell.props.db.entry_request_extra_metadata(entry, RB.RHYTHMDB_PROP_STREAM_SONG_ARTIST)
            
            if stream_title:
                if stream_artist:
                    markup = "<b>{title}</b> <small>{artist}</small>".format(
                        title=GLib.markup_escape_text(stream_title),
                        artist=GLib.markup_escape_text(stream_artist))
                else:
                    markup = "<b>{title}</b>".format(
                        title=GLib.markup_escape_text(stream_title))
                self.song_button_label.set_markup(markup)
                return
                
            album = entry.get_string(RB.RhythmDBPropType.ALBUM) 
            if not album or album == "":
                self.song_button_label.set_markup("<b>{title}</b>".format( 
                    title=GLib.markup_escape_text(entry.get_string(RB.RhythmDBPropType.TITLE))))
                return
                
            if self.playing_label:
                year = entry.get_ulong(RB.RhythmDBPropType.DATE)
                if year == 0:
                    year = date.today().year
                else:
                    year = datetime.fromordinal(year).year

                self.song_button_label.set_markup(
                    "<small>{album} - {genre} - {year}</small>".format(
                        album=GLib.markup_escape_text(entry.get_string(RB.RhythmDBPropType.ALBUM)),
                        genre=GLib.markup_escape_text(entry.get_string(RB.RhythmDBPropType.GENRE)),
                        year=GLib.markup_escape_text(str(year))))
            else:
                self.song_button_label.set_markup(
                    "<b>{title}</b> <small>{album} - {artist}</small>".format(
                        title=GLib.markup_escape_text(entry.get_string(RB.RhythmDBPropType.TITLE)),
                        album=GLib.markup_escape_text(entry.get_string(RB.RhythmDBPropType.ALBUM)),
                        artist=GLib.markup_escape_text(entry.get_string(RB.RhythmDBPropType.ARTIST))))

            key = entry.create_ext_db_key(RB.RhythmDBPropType.ALBUM)
            self.album_art_db.request(key,
                                      self.display_song_album_art_callback,
                                      entry)


    def display_song_album_art_callback(self, *args): #key, filename, data, entry):
        # rhythmbox 3.2 breaks the API - need to find the parameter with the pixbuf
        data = None
        for data in args:
            if isinstance(data, GdkPixbuf.Pixbuf):
                break
                
        if ( ( data is not None ) and ( isinstance(data, GdkPixbuf.Pixbuf) ) ):
            self.cover_pixbuf = data
            scale_cover = self.cover_pixbuf.scale_simple(self.icon_width + 10, self.icon_width + 10,
                                                         GdkPixbuf.InterpType.HYPER)

            self.album_cover.set_from_pixbuf(scale_cover)
        else:
            self.cover_pixbuf = None
            self.album_cover.clear()

        self.album_cover.trigger_tooltip_query()

    # Signal Handlers ##########################################################
    def _sh_on_sidepane_btn_clicked(self, *args):
        self.rb_settings.set_boolean('display-page-tree-visible', not self.display_page_tree_visible)

    def _sh_on_toolbar_btn_clicked(self, *args):
        image = self.toolbar_button.get_image()
        if not image:
            image = self.toolbar_button.get_child()

        if image.props.icon_name == 'go-up-symbolic':
            image.props.icon_name = 'go-down-symbolic'
            self.emit('toolbar-visibility', False)

        else:
            image.props.icon_name = 'go-up-symbolic'
            self.emit('toolbar-visibility', True)

        self.on_page_change(self.shell.props.display_page_tree, self.shell.props.selected_page)
    
    def _sh_on_song_property_changed(self, sp, uri, property, old, new):
        if sp.get_playing() and property in ('artist', 
                                             'album', 
                                             'title',
                                             RB.RHYTHMDB_PROP_STREAM_SONG_ARTIST,
                                             RB.RHYTHMDB_PROP_STREAM_SONG_ALBUM,
                                             RB.RHYTHMDB_PROP_STREAM_SONG_TITLE):
            entry = sp.get_playing_entry()
            self.display_song(entry)
    
    def _sh_on_playing_change(self, player, playing):
        image = self.play_button.get_child()
        if (playing):
            if player.get_active_source().can_pause():
                icon_name = "media-playback-pause-symbolic"
            else:
                icon_name = "media-playback-stop-symbolic"

        else:
            icon_name = "media-playback-start-symbolic"

        image.set_from_icon_name(icon_name, self.icon_width)

    def _sh_on_song_change(self, player, entry):
        if ( entry is not None ):
            self.song_duration = entry.get_ulong(RB.RhythmDBPropType.DURATION)
        else:
            self.song_duration = 0
            
        self.display_song(entry)

    def _sh_on_playing(self, player, second):
        if ( self.song_duration != 0 ):
            self.song_progress.progress = float(second) / self.song_duration

            try:
                valid, time = player.get_playing_time()
                if not valid or time == 0:
                    return
            except:
                return

            m, s = divmod(time, 60)
            h, m = divmod(m, 60)

            tm, ts = divmod(self.song_duration, 60)
            th, tm = divmod(tm, 60)

            if th == 0:
                label = "<small>{time}</small>".format(time="%02d:%02d" % (m, s))
                tlabel = "<small>{time}</small>".format(time="%02d:%02d" % (tm, ts))
            else:
                label = "<small>{time}</small>".format(time="%d:%02d:%02d" % (h, m, s))
                tlabel = "<small>{time}</small>".format(time="%d:%02d:%02d" % (th, tm, ts))

            self.current_time_label.set_markup(label)
            self.total_time_label.set_markup(tlabel)

    def _sh_progress_control(self, progress, fraction):
        if ( self.song_duration != 0 ):
            self.shell_player.set_playing_time(self.song_duration * fraction)

    def _sh_bigger_cover(self, cover, x, y, key, tooltip):
        if ( self.cover_pixbuf is not None ):
            tooltip.set_icon(self.cover_pixbuf.scale_simple(300, 300,
                                                            GdkPixbuf.InterpType.HYPER))
            return True
        else:
            return False


# ###############################################################################
# Custom Widgets ###############################################################

class SmallProgressBar(Gtk.DrawingArea):
    __gsignals__ = {
        "control": (GObject.SIGNAL_RUN_LAST, None, (float,))
    }

    @GObject.Property
    def progress(self):
        return self.__progress__

    @progress.setter
    def progress(self, value):
        self.__progress__ = value
        self.queue_draw()

    def __init__(self):
        super(SmallProgressBar, self).__init__()
        self.add_events(Gdk.EventMask.POINTER_MOTION_MASK |
                        Gdk.EventMask.BUTTON_PRESS_MASK |
                        Gdk.EventMask.BUTTON_RELEASE_MASK)
        self.button_pressed = False
        self.button_time = 0
        self.__progress__ = 0

    def do_draw(self, cc):
        alloc = self.get_allocation()
        sc = self.get_style_context()
        fgc = sc.get_background_color(Gtk.StateFlags.SELECTED)  #self.get_state_flags() )
        bgc = sc.get_color(Gtk.StateFlags.NORMAL)  #self.get_state_flags() )

        cc.set_source_rgba(bgc.red, bgc.green, bgc.blue, bgc.alpha)
        cc.rectangle(0, alloc.height / 2, alloc.width, alloc.height / 4)
        cc.fill()

        cc.set_source_rgba(fgc.red, fgc.green, fgc.blue, fgc.alpha)
        cc.rectangle(0, alloc.height / 2, alloc.width * self.progress, alloc.height / 4)
        cc.fill()
        
        if self.progress != 0:
            cc.set_line_width(1)  
            cc.set_source_rgba(bgc.red, bgc.green, bgc.blue, bgc.alpha)
      
            cc.translate((alloc.width * self.progress), (alloc.height / 2) + 1)
            print (self.progress)
            cc.arc(0, 0, 5, 0, 2*math.pi)
            cc.stroke_preserve()
            
            cc.fill() 

    def do_motion_notify_event(self, event):
        if ( self.button_pressed ):
            self.control_by_event(event)
            return True
        else:
            return False

    def do_button_press_event(self, event):
        self.button_pressed = True
        self.control_by_event(event)
        return True

    def do_button_release_event(self, event):
        self.button_pressed = False
        self.control_by_event(event)
        return True

    def control_by_event(self, event):
        allocw = self.get_allocated_width()
        fraction = event.x / allocw
        if ( self.button_time + 100 < event.time ):
            self.button_time = event.time
            self.emit("control", fraction)

