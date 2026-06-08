#!/usr/bin/env python3
import gi
import threading
import os
import subprocess
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk
from ut_api import search_youtube
from ut_engine import YTEngine

class UToopMusicApp(Gtk.Window):
    def __init__(self):
        super().__init__(title="uToop Music")
        self.set_default_size(800, 420)

        self.engine = YTEngine(on_finish_callback=self.on_track_finished)
        self.results = []
        self.yt_results = []
        self.local_results = []
        self.yt_query = ""
        self.local_query = ""
        self.current_idx = -1
        self.playback_mode = 0 # 0: None, 1: Loop, 2: Autoplay
        self.mode = "YT"
        self.is_dragging = False

        # Ensure default download directory exists
        default_dl_dir = self._get_default_download_dir()
        os.makedirs(default_dl_dir, exist_ok=True)

        # UI State
        self.status_base = "uToop Music Developed by Miraj Lensman"

        self.dot_count = 0

        # Style
        css = """
            window { background-color: #000; color: #f33; font-family: monospace; }
            .terminal-entry { background-color: #111; color: #f33; border: 1px solid #333; font-size: 20px; border-radius: 5px; padding: 5px; }
            .terminal-btn { background-color: #222; color: #0f0; border: 1px solid #444; border-radius: 10px; font-weight: bold; font-size: 15px; min-height: 45px; padding: 0 6px; }
            .terminal-btn:active { background-color: #444; }
            
            .terminal-btn.btn-red { color: #f33; }
            .terminal-btn.btn-blue { color: #0af; }
            .terminal-btn.btn-white { background-color: #fff; color: #000; }
            .mode-btn { min-width: 150px; }
            .options-btn { font-size: 24px; }
            
            .download-btn { min-height: 40px; padding: 0 8px; font-size: 24px; }
            .terminal-list { background-color: #000; color: #0f0; border: none; }
            .terminal-list-local { background-color: #000; color: #fff; border: none; }
            .terminal-list row { padding: 6px; border-bottom: 1px solid #222; }
            .terminal-list row:selected { background-color: #111; color: #f33; }
            .terminal-list row:selected label { color: #f33; }
            .terminal-list-local row { padding: 6px; border-bottom: 1px solid #222; }
            .terminal-list-local row:selected { background-color: #0af; }
            .terminal-list-local row:selected label { color: #fff; }
            
            .list-title { font-size: 16px; font-weight: bold; color: #0af; }
            .list-title-local { font-size: 20px; font-weight: bold; color: #fff; }
            .list-meta { font-size: 12px; color: #06f; }
            .marquee-label { color: #f33; font-size: 16px; font-weight: bold; }
            .meta-text { color: #0af; font-size: 20px; }
            .progress-box { min-height: 20px; background-color: #111; margin-top: 20px; }
            .progress-bar-bg { background-color: #222; }
            .progress-bar-fill { background-color: #f33; }
        """
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(css.encode())
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), style_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        # Main Layout
        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        main_vbox.set_border_width(5)
        self.add(main_vbox)
        self.connect("destroy", self.on_destroy)

        # Search Bar
        search_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        
        # Toggle Button
        self.toggle_mode_btn_search = Gtk.Button(label=" Downloads ")
        self.toggle_mode_btn_search.get_style_context().add_class("terminal-btn")
        self.toggle_mode_btn_search.get_style_context().add_class("btn-blue")
        self.toggle_mode_btn_search.connect("clicked", self.on_toggle_mode)
        search_hbox.pack_start(self.toggle_mode_btn_search, False, False, 0)
        
        # Container for entry and clear button
        entry_container = Gtk.Overlay()
        
        self.search_entry = Gtk.Entry()
        self.search_entry.get_style_context().add_class("terminal-entry")
        self.search_entry.set_placeholder_text("Enter song name...")
        self.search_entry.connect("activate", self.on_search_clicked)
        entry_container.add(self.search_entry)
        
        # Clear Button as Overlay
        clear_btn = Gtk.Button(label=" X ")
        clear_btn.get_style_context().add_class("terminal-btn")
        clear_btn.get_style_context().add_class("btn-red")
        clear_btn.set_halign(Gtk.Align.END)
        clear_btn.set_valign(Gtk.Align.CENTER)
        clear_btn.connect("clicked", lambda w: self.search_entry.set_text(""))
        entry_container.add_overlay(clear_btn)
        
        search_hbox.pack_start(entry_container, True, True, 0)
        
        search_btn = Gtk.Button(label=" SEARCH ")
        search_btn.get_style_context().add_class("terminal-btn")
        search_btn.get_style_context().add_class("btn-red")
        search_btn.connect("clicked", self.on_search_clicked)
        search_hbox.pack_start(search_btn, False, False, 0)
        main_vbox.pack_start(search_hbox, False, False, 0)

        # Results List
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.listbox = Gtk.ListBox()
        self.listbox.get_style_context().add_class("terminal-list")
        self.listbox.connect("row-activated", self.on_row_activated)
        scrolled.add(self.listbox)
        main_vbox.pack_start(scrolled, True, True, 0)
        
        # Progress Bar (Custom)
        self.progress_box = Gtk.EventBox()
        self.progress_box.get_style_context().add_class("progress-box")
        self.progress_box.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | 
                                     Gdk.EventMask.BUTTON_RELEASE_MASK | 
                                     Gdk.EventMask.POINTER_MOTION_MASK)
        self.progress_box.connect("button-press-event", self.on_progress_button_press)
        self.progress_box.connect("button-release-event", self.on_progress_button_release)
        self.progress_box.connect("motion-notify-event", self.on_progress_motion)
        
        # Reduced margins to fit time labels, adjusted for user preference
        self.progress_box.set_margin_start(10)
        self.progress_box.set_margin_end(10)
        
        self.progress_bar_bg = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.progress_bar_bg.get_style_context().add_class("progress-bar-bg")
        self.progress_bar_bg.set_size_request(-1, 20)
        
        self.progress_bar_fill = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.progress_bar_fill.get_style_context().add_class("progress-bar-fill")
        self.progress_bar_fill.set_size_request(0, 20)
        
        self.progress_bar_bg.pack_start(self.progress_bar_fill, False, False, 0)
        self.progress_box.add(self.progress_bar_bg)
        
        # New Seek Row: CurrentTime - ProgressBar - TotalLength
        seek_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        
        self.current_time_label = Gtk.Label(label="00:00")
        self.current_time_label.get_style_context().add_class("meta-text")
        
        self.total_time_label = Gtk.Label(label="00:00")
        self.total_time_label.get_style_context().add_class("meta-text")
        
        seek_hbox.pack_start(self.current_time_label, False, False, 0)
        seek_hbox.pack_start(self.progress_box, True, True, 0)
        seek_hbox.pack_start(self.total_time_label, False, False, 0)
        
        main_vbox.pack_start(seek_hbox, False, False, 5)
        
        # Bottom controls row
        bottom_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        
        # Prev
        prev_btn = Gtk.Button(label=" PREV ")
        prev_btn.get_style_context().add_class("terminal-btn")
        prev_btn.get_style_context().add_class("btn-blue")
        prev_btn.set_size_request(110, 45)
        prev_btn.connect("clicked", lambda w: self.change_track(-1))
        bottom_hbox.pack_start(prev_btn, False, False, 0)

        # Play/Pause
        self.play_btn = Gtk.Button(label=" PAUSE ")
        self.play_btn.get_style_context().add_class("terminal-btn")
        self.play_btn.get_style_context().add_class("btn-red")
        self.play_btn.set_size_request(110, 45)
        self.play_btn.connect("clicked", self.on_play_pause_clicked)
        bottom_hbox.pack_start(self.play_btn, False, False, 0)
        
        # Next
        next_btn = Gtk.Button(label=" NEXT ")
        next_btn.get_style_context().add_class("terminal-btn")
        next_btn.get_style_context().add_class("btn-blue")
        next_btn.set_size_request(110, 45)
        next_btn.connect("clicked", lambda w: self.change_track(1))
        bottom_hbox.pack_start(next_btn, False, False, 0)
        
        # Mode (Wider)
        self.mode_btn = Gtk.Button()
        self.mode_btn.get_style_context().add_class("terminal-btn")
        self.mode_btn.get_style_context().add_class("mode-btn")
        self.mode_btn.set_size_request(130, 45)
        self.mode_btn.connect("clicked", self.on_mode_clicked)
        bottom_hbox.pack_start(self.mode_btn, True, True, 0)
        
        # Refresh
        refresh_btn = Gtk.Button(label=" REFRESH ")
        refresh_btn.get_style_context().add_class("terminal-btn")
        refresh_btn.get_style_context().add_class("btn-red")
        refresh_btn.set_size_request(110, 45)
        refresh_btn.connect("clicked", self.on_refresh_clicked)
        bottom_hbox.pack_start(refresh_btn, False, False, 0)
        
        # Options (Narrower)
        options_btn = Gtk.Button(label=" ⚙ ")
        options_btn.get_style_context().add_class("terminal-btn")
        options_btn.get_style_context().add_class("options-btn")
        # Custom CSS for black label on white button
        options_btn.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
        options_btn.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0, 0, 0, 1))
        options_btn.set_size_request(60, 45)
        options_btn.connect("clicked", self.on_options_clicked)
        bottom_hbox.pack_start(options_btn, False, False, 0)
        
        main_vbox.pack_start(bottom_hbox, False, False, 5)

        # Status Label
        self.status_label = Gtk.Label(label=self.status_base)
        self.status_label.get_style_context().add_class("marquee-label")
        self.status_label.set_ellipsize(3) # Pango.EllipsizeMode.END
        self.status_label.set_xalign(0)
        self.status_label.set_size_request(-1, 20)
        main_vbox.pack_end(self.status_label, False, False, 5)
        
        # Initialize mode label
        self.update_mode_button()
        
        GLib.timeout_add(500, self.update_status_animation)
        GLib.timeout_add(1000, self.update_progress)
        
        self.show_all()
        self.connect("destroy", self.on_destroy)
        self.connect("key-press-event", self.on_key_press)

    def on_key_press(self, widget, event):
        # Handle alphanumeric keys to shift focus to search box
        if Gdk.KEY_a <= event.keyval <= Gdk.KEY_z or Gdk.KEY_A <= event.keyval <= Gdk.KEY_Z or Gdk.KEY_0 <= event.keyval <= Gdk.KEY_9:
            if not self.search_entry.is_focus():
                self.search_entry.grab_focus()
                self.search_entry.set_position(-1) # Move cursor to end
                return False # Allow the key to be typed into the entry

        # 1. Handle Space - Play/Pause only if NOT in search box
        if event.keyval == Gdk.KEY_space and not self.search_entry.is_focus():
            self.on_play_pause_clicked(None)
            return True
            
        # 2. Handle Down Arrow - Move focus from search to list
        if event.keyval == Gdk.KEY_Down and self.search_entry.is_focus():
            row = self.listbox.get_selected_row()
            if not row:
                row = self.listbox.get_row_at_index(0)
                if row: self.listbox.select_row(row)
            
            if row:
                row.grab_focus()
            return True

        # 3. Handle Left/Right Arrow - Seek 15 seconds
        if event.keyval == Gdk.KEY_Left and not self.search_entry.is_focus():
            self.engine.seek(-15)
            return True
        if event.keyval == Gdk.KEY_Right and not self.search_entry.is_focus():
            self.engine.seek(15)
            return True
        
        return False

    def on_destroy(self, widget):
        # Clean up temporary .part files in the download directory
        target_dir = self.load_download_location()
        if os.path.exists(target_dir):
            for file in os.listdir(target_dir):
                if file.endswith(".part"):
                    try:
                        os.remove(os.path.join(target_dir, file))
                    except OSError:
                        pass
        
        # Ensure child processes are killed
        self.engine.stop()
        
        # Force kill any lingering processes
        for proc_name in ["yt-dlp", "mpv", "ffmpeg"]:
            subprocess.run(["pkill", "-f", proc_name], stderr=subprocess.DEVNULL)
        
        Gtk.main_quit()

    def _perform_seek(self, x):
        width = self.progress_box.get_allocated_width()
        if width == 0: return
        fraction = max(0, min(1, x / width))
        _, duration = self.engine.get_current_time()
        if duration > 0:
            target_time = fraction * duration
            self.engine.seek_to(target_time)

    def on_progress_button_press(self, widget, event):
        self.is_dragging = True
        self._perform_seek(event.x)
        return True

    def on_progress_motion(self, widget, event):
        if self.is_dragging:
            self._perform_seek(event.x)
        return True

    def on_progress_button_release(self, widget, event):
        if self.is_dragging:
            self.is_dragging = False
            self._perform_seek(event.x)
        return True



    def update_status_animation(self):
        self.dot_count = (self.dot_count + 1) % 4
        self.status_label.set_text(f"{self.status_base}{'.' * self.dot_count}")
        return True

    def set_status(self, msg):
        self.status_base = msg
        self.dot_count = 0
        self.status_label.set_text(self.status_base)

    def update_progress(self):
        time_pos, duration = self.engine.get_current_time()
        if duration > 0:
            fraction = time_pos / duration
            width = self.progress_box.get_allocated_width()
            self.progress_bar_fill.set_size_request(int(width * fraction), 20)
            
            # Update separate time labels
            self.current_time_label.set_text(f"{int(time_pos//60):02}:{int(time_pos%60):02}")
            self.total_time_label.set_text(f"{int(duration//60):02}:{int(duration%60):02}")
        return True

    def set_toggle_label(self, btn, text, active):
        # Remove old label
        child = btn.get_child()
        if child: btn.remove(child)
        
        # Create new label with markup
        lbl = Gtk.Label()
        lbl.set_use_markup(True)
        # Red text always, strikethrough if inactive
        lbl.set_markup(f" {text} " if active else f"<s> {text} </s>")
        btn.add(lbl)
        btn.show_all()

    def on_options_clicked(self, btn):
        print("DEBUG: Options button clicked")
        dialog = Gtk.Dialog(
            title="Options",
            parent=self,
            modal=True,
            destroy_with_parent=True,
        )
        
        # Style for large buttons
        box = dialog.get_content_area()
        box.set_spacing(10)
        box.set_border_width(10)
        
        btn_dl = Gtk.Button(label="Change Download Location")
        btn_dl.set_size_request(-1, 60)
        btn_dl.connect("clicked", self.on_change_download_location_clicked)
        box.add(btn_dl)
        
        btn_reset = Gtk.Button(label="Reset to Default Path")
        btn_reset.set_size_request(-1, 60)
        btn_reset.connect("clicked", self.on_reset_download_location)
        box.add(btn_reset)
        
        btn_show = Gtk.Button(label="Show Current Path")
        btn_show.set_size_request(-1, 60)
        btn_show.connect("clicked", self.on_show_download_location)
        box.add(btn_show)
        
        btn_about = Gtk.Button(label="About")
        btn_about.set_size_request(-1, 60)
        btn_about.connect("clicked", self.on_about_clicked)
        box.add(btn_about)
        
        dialog.add_button(" CLOSE ", Gtk.ResponseType.CLOSE)
        
        dialog.show_all()
        dialog.run()
        dialog.destroy()

    def on_reset_download_location(self, widget):
        path = self._get_default_download_dir()
        self.save_download_location(path)
        self.set_status(f"Reset to default: {path}")

    def on_show_download_location(self, widget):
        path = self.load_download_location()
        dialog = Gtk.MessageDialog(
            parent=self, 
            modal=True, 
            buttons=Gtk.ButtonsType.OK, 
            text="Current Download Folder"
        )
        dialog.format_secondary_text(path)
        dialog.run()
        dialog.destroy()

    def on_search_clicked(self, widget):
        if self.mode == "YT":
            self.perform_yt_search()
        else:
            self.filter_local_files()

    def perform_yt_search(self):
        query = self.search_entry.get_text()
        if not query: return
        
        self.set_status("Searching, please wait")
        
        # Clear current list
        for child in self.listbox.get_children():
            self.listbox.remove(child)
        
        def run_search():
            results = search_youtube(query)
            GLib.idle_add(self.display_results, results)
        
        threading.Thread(target=run_search, daemon=True).start()

    def filter_local_files(self):
        query = self.search_entry.get_text().lower()
        target_dir = self.load_download_location()
        if not os.path.exists(target_dir):
            self.set_status("Download folder not found")
            return
            
        files = [f for f in os.listdir(target_dir) if f.lower().endswith(('.m4a', '.mp3', '.opus', '.wav'))]
        
        results = []
        for f in files:
            if query in f.lower():
                # Use filename as title, full path as videoId (handled by engine for local)
                results.append({"title": f, "videoId": os.path.join(target_dir, f), "is_local": True})
        
        # Clear current list
        for child in self.listbox.get_children():
            self.listbox.remove(child)
            
        self.display_results(results, show_metadata=False)
        self.set_status(f"Found {len(results)} local files")

    def display_results(self, results, show_metadata=True):
        # Properly clear listbox
        for child in self.listbox.get_children():
            self.listbox.remove(child)
            child.destroy()
        self.results = results
        # Ensure metadata flag matches the current mode for safety
        actual_show_metadata = (self.mode == "YT")
        for item in results:
            row = Gtk.ListBoxRow()
            # Use a box for the row content
            row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
            row.add(row_box)
            if actual_show_metadata:
                # YT mode: title + author/length
                info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
                title_lbl = Gtk.Label(label=item["title"], xalign=0)
                title_lbl.get_style_context().add_class("list-title")
                title_lbl.set_ellipsize(3)
                length_val = item.get("length")
                length_sec = int(length_val) if length_val is not None else 0
                length_str = f"{length_sec//60:02}:{length_sec%60:02}"
                meta_lbl = Gtk.Label(label=f"{item.get('author', 'Unknown')} | {length_str}", xalign=0)
                meta_lbl.get_style_context().add_class("list-meta")
                info_box.pack_start(title_lbl, True, True, 0)
                info_box.pack_start(meta_lbl, True, True, 0)
                row_box.pack_start(info_box, True, True, 0)

                # Download button
                dl_btn = Gtk.Button(label=" ⬇ ")
                dl_btn.get_style_context().add_class("terminal-btn")
                dl_btn.get_style_context().add_class("btn-blue")
                dl_btn.get_style_context().add_class("download-btn")
                dl_btn.connect("clicked", lambda b, t=item: self.download_track(t))
                row_box.pack_end(dl_btn, False, False, 0)
            else:
                # Local mode: Just title
                title_lbl = Gtk.Label(label=item['title'], xalign=0)
                title_lbl.get_style_context().add_class("list-title-local")
                row_box.pack_start(title_lbl, True, True, 0)
            self.listbox.add(row)
        self.show_all()

    def download_track(self, track):
        target_dir = self.load_download_location()
        
        # Check if file already exists
        # Note: yt-dlp might use different extensions, but we'll check based on title.
        # This is a simplified check.
        file_exists = False
        for ext in ['.m4a', '.mp3', '.opus', '.wav']:
            if os.path.exists(os.path.join(target_dir, f"{track['title']}{ext}")):
                file_exists = True
                break
        
        if file_exists:
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.NONE,
                text="File already exists",
            )
            dialog.format_secondary_text(f"'{track['title']}' already exists. Download again?")
            dialog.add_button("Download Again", Gtk.ResponseType.YES)
            dialog.add_button("Skip", Gtk.ResponseType.NO)
            response = dialog.run()
            dialog.destroy()
            if response != Gtk.ResponseType.YES:
                return

        # Stop playback to free up resources before downloading
        self.engine.stop()
        self.play_btn.set_label(" PAUSE ")
        self.set_status(f"DOWNLOADING: {track['title']}")

        def update_progress(percent):
            if percent == "CONVERTING":
                GLib.idle_add(self.set_status, f"CONVERTING... - {track['title']}")
            else:
                GLib.idle_add(self.set_status, f"DOWNLOADING: {percent}% - {track['title']}")

        def run_download():
            result = self.engine.download_audio(track['videoId'], progress_callback=update_progress, custom_path=target_dir)
            if result == True:
                GLib.idle_add(self.set_status, f"DOWNLOADED: {track['title']}")
            elif result == "STOPPED":
                GLib.idle_add(self.set_status, f"DOWNLOAD STOPPED: {track['title']}")
            else:
                GLib.idle_add(self.set_status, f"ERROR: Download failed for {track['title']}")

        threading.Thread(target=run_download, daemon=True).start()


    def on_row_activated(self, lb, row):
        self.current_idx = row.get_index()
        self.play_track(self.results[self.current_idx])

    def change_track(self, direction):
        if not self.results: return
        self.current_idx = (self.current_idx + direction) % len(self.results)
        row = self.listbox.get_row_at_index(self.current_idx)
        self.listbox.select_row(row)
        self.play_track(self.results[self.current_idx])

    def play_track(self, track):
        # If downloading, ask to cancel
        if self.engine.download_process:
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.NONE,
                text="Download in Progress",
            )
            dialog.format_secondary_text("Cancel download to play this track?")
            response = dialog.run()
            dialog.destroy()
            
            if response == Gtk.ResponseType.YES:
                self.engine.stop()
                self.play_btn.set_label(" PLAY ") # Reset button label if cancelled
            else:
                return

        is_local = track.get('is_local', False)
        status_prefix = "OPENING" if is_local else "FETCHING"
        self.set_status(f"{status_prefix}: {track['title']}")
        
        def run_play():
            self.engine.stop() 
            success = self.engine.play(track['videoId'], is_local=is_local)
            if success:
                GLib.idle_add(self.set_status, f"NOW PLAYING: {track['title']}")
                GLib.idle_add(self.play_btn.set_label, " PAUSE ")
            else:
                GLib.idle_add(self.set_status, "ERROR: Failed to play audio")
        
        threading.Thread(target=run_play, daemon=True).start()

    def on_play_pause_clicked(self, btn):
        paused = self.engine.toggle_pause()
        
        if paused:
            self.play_btn.set_label(" RESUME ")
            self.set_status("Playing paused")
        else:
            self.play_btn.set_label(" PAUSE ")
            self.set_status("Playing")

    def on_refresh_clicked(self, btn):
        self.engine.stop()
        self.results = []
        self.current_idx = -1
        # Clear list
        self.clear_listbox()
        self.search_entry.set_text("")
        self.set_status("Ready")
        self.play_btn.set_label(" PAUSE ")
        self.progress_bar_fill.set_size_request(0, 20)
        self.current_time_label.set_text("00:00")
        self.total_time_label.set_text("00:00")
        
        # Repopulate if in local mode
        if self.mode == "LOCAL":
            self.filter_local_files()

    def clear_listbox(self):
        for child in self.listbox.get_children():
            self.listbox.remove(child)
            child.destroy()

    def on_toggle_mode(self, btn):
        # Save current state before switching
        if self.mode == "YT":
            self.yt_results = self.results
            self.yt_query = self.search_entry.get_text()
        else:
            self.local_results = self.results
            self.local_query = self.search_entry.get_text()

        # Switch mode
        self.mode = "LOCAL" if self.mode == "YT" else "YT"
        
        # Switch label and color
        new_label = " Youtube " if self.mode == "LOCAL" else " Downloads "
        self.toggle_mode_btn_search.set_label(new_label)
        
        # Color logic: Local mode -> red button, YT mode -> blue button
        if self.mode == "LOCAL":
            self.toggle_mode_btn_search.get_style_context().remove_class("btn-blue")
            self.toggle_mode_btn_search.get_style_context().add_class("btn-red")
            self.listbox.get_style_context().remove_class("terminal-list")
            self.listbox.get_style_context().add_class("terminal-list-local")
            
            # Restore local state
            self.search_entry.set_text(self.local_query)
            if self.local_results:
                self.display_results(self.local_results)
            else:
                self.filter_local_files()
        else:
            self.toggle_mode_btn_search.get_style_context().remove_class("btn-red")
            self.toggle_mode_btn_search.get_style_context().add_class("btn-blue")
            self.listbox.get_style_context().remove_class("terminal-list-local")
            self.listbox.get_style_context().add_class("terminal-list")
            
            # Restore YT state
            self.search_entry.set_text(self.yt_query)
            if self.yt_results:
                self.display_results(self.yt_results)
            else:
                self.clear_listbox()
                self.results = []
                self.set_status("Ready")

    def on_about_clicked(self, widget):
        dialog = Gtk.AboutDialog(transient_for=self)
        dialog.set_program_name("uToop Music")
        dialog.set_version("1.0")
        dialog.set_comments("A simple YouTube music player for Maemo Leste on Nokia N900.\n\nDeveloped by Miraj Lensman")
        dialog.run()
        dialog.destroy()

    def on_change_download_location_clicked(self, widget):
        dialog = Gtk.FileChooserDialog(
            title="Please choose a folder",
            parent=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            "Select", Gtk.ResponseType.OK
        )
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            new_path = dialog.get_filename()
            self.save_download_location(new_path)
            self.set_status(f"Download location: {new_path}")
        dialog.destroy()

    def save_download_location(self, path):
        import json
        config_dir = os.path.expanduser("~/.config/utoop-music")
        os.makedirs(config_dir, exist_ok=True)
        config_path = os.path.join(config_dir, "config.json")
        config = {"download_path": path}
        with open(config_path, "w") as f:
            json.dump(config, f)

    def load_download_location(self):
        import json
        config_path = os.path.expanduser("~/.config/utoop-music/config.json")
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                try:
                    config = json.load(f)
                    return config.get("download_path", self._get_default_download_dir())
                except json.JSONDecodeError:
                    pass
        return self._get_default_download_dir()

    def on_mode_clicked(self, btn):
        self.playback_mode = (self.playback_mode + 1) % 3
        self.update_mode_button()

    def update_mode_button(self):
        modes = [" Loop/Autoplay ", " Loop On ", " Autoplay On "]
        self.mode_btn.set_label(modes[self.playback_mode])
        child = self.mode_btn.get_child()
        if isinstance(child, Gtk.Label):
            child.set_ellipsize(3) # Pango.EllipsizeMode.END
        
        # Color logic: White/Black for default (0), Blue for Loop (1) or Autoplay (2)
        if self.playback_mode == 0:
            self.mode_btn.get_style_context().remove_class("btn-blue")
            self.mode_btn.get_style_context().remove_class("btn-red")
            self.mode_btn.get_style_context().add_class("btn-white")
        else:
            self.mode_btn.get_style_context().remove_class("btn-white")
            self.mode_btn.get_style_context().add_class("btn-blue")

    def _get_default_download_dir(self):
        n900_dl_dir = "/home/user/MyDocs/uToopDownloads"
        generic_dl_dir = os.path.expanduser("~/uToopDownloads")
        return n900_dl_dir if os.path.exists("/home/user/MyDocs") else generic_dl_dir

    def on_track_finished(self):
        GLib.idle_add(self.handle_playback_finish)

    def handle_playback_finish(self):
        if self.playback_mode == 1: # Loop
            self.play_track(self.results[self.current_idx])
        elif self.playback_mode == 2: # Autoplay
            self.current_idx += 1
            if self.current_idx < len(self.results):
                # Select the next row in the UI for visual feedback
                row = self.listbox.get_row_at_index(self.current_idx)
                self.listbox.select_row(row)
                self.play_track(self.results[self.current_idx])
            else:
                self.set_status("Playlist ended")
        else:
            self.set_status("Track finished")


if __name__ == "__main__":
    app = UToopMusicApp()
    Gtk.main()

