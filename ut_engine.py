import subprocess
import threading
import os
import socket
import json
import time

class YTEngine:
    def __init__(self, on_finish_callback=None):
        self.mpv_process = None
        self.fetch_process = None
        self.download_process = None
        self.on_finish_callback = on_finish_callback
        self.current_video_id = None
        self.is_paused = False
        self.ipc_socket = f"/tmp/mpv-utoop-music-{os.getuid()}.sock"

    def get_stream_url(self, video_id):
        """Extract direct audio URL using yt-dlp with fallback to bestaudio"""
        # First attempt: M4A
        for fmt in ["140", "bestaudio"]:
            cmd = [
                "yt-dlp",
                "--js-runtimes", "node:/usr/bin/nodejs",
                "--get-url",
                "--format", fmt,
                "--no-check-certificates",
                f"https://www.youtube.com/watch?v={video_id}"
            ]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            self.fetch_process = process
            
            try:
                stdout, stderr = process.communicate(timeout=30)
                if process.returncode == 0:
                    self.fetch_process = None
                    return stdout.strip()
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate() # Clean up zombie
            finally:
                self.fetch_process = None
        return None

    def play(self, video_id, is_local=False):
        # Assumed called in background thread
        self.stop()
        self.current_video_id = video_id
        
        if is_local:
            url = video_id
        else:
            url = self.get_stream_url(video_id)
            
        if not url: return False

        if os.path.exists(self.ipc_socket): os.remove(self.ipc_socket)

        cmd = [
            "mpv",
            "--no-video",
            "--cache=yes",
            "--audio-device=alsa",
            f"--input-ipc-server={self.ipc_socket}",
            url
        ]
        # Start mpv with the current environment to ensure audio backend works
        env = os.environ.copy()
        
        print(f"DEBUG: Starting mpv with: {' '.join(cmd)}")
        # Redirect stderr to a file or print it to see errors
        self.mpv_process = subprocess.Popen(
            cmd, 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.PIPE,
            env=env
        )
        self.is_paused = False
        
        # Give mpv a moment to create the socket
        time.sleep(2)
        
        # Robust check: if mpv is running, assume success
        if self.mpv_process.poll() is None:
            print("DEBUG: mpv started successfully")
            
            # Print mpv errors if any occur during playback
            def log_mpv_errors():
                for line in iter(self.mpv_process.stderr.readline, b''):
                    print(f"MPV ERROR: {line.decode().strip()}")
            
            threading.Thread(target=log_mpv_errors, daemon=True).start()
            threading.Thread(target=self._wait_for_finish, daemon=True).start()
            return True
        else:
            _, err = self.mpv_process.communicate()
            print(f"DEBUG: mpv failed to start. Error: {err.decode() if err else 'Unknown'}")
            return False

    def get_current_time(self):
        time_pos, duration = 0, 0
        try:
            client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client.settimeout(0.5)
            client.connect(self.ipc_socket)
            client.send(b'{"command": ["get_property", "time-pos"]}\n')
            data1 = client.recv(1024)
            time_pos = json.loads(data1.decode())['data']
            client.send(b'{"command": ["get_property", "duration"]}\n')
            data2 = client.recv(1024)
            duration = json.loads(data2.decode())['data']
            client.close()
        except: pass
        return time_pos or 0, duration or 0

    def seek_to(self, seconds):
        try:
            client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client.settimeout(0.5)
            client.connect(self.ipc_socket)
            # Use 'absolute' seek instead of 'relative'
            cmd = f'{{"command": ["seek", {seconds}, "absolute"]}}\n'
            client.send(cmd.encode())
            client.close()
        except Exception as e:
            print(f"DEBUG: Failed to seek via IPC: {e}")

    def seek(self, seconds):
        try:
            client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client.settimeout(0.5)
            client.connect(self.ipc_socket)
            cmd = f'{{"command": ["seek", {seconds}, "relative"]}}\n'
            client.send(cmd.encode())
            client.close()
        except: pass

    def toggle_pause(self):
        try:
            client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client.settimeout(0.5)
            client.connect(self.ipc_socket)
            
            # Toggle the pause state
            new_pause_state = not self.is_paused
            
            # Send set_property command
            cmd = json.dumps({"command": ["set_property", "pause", new_pause_state]}) + "\n"
            client.send(cmd.encode())
            client.close()
            
            self.is_paused = new_pause_state
        except Exception as e:
            print(f"DEBUG: Failed to toggle pause via IPC: {e}")
        return self.is_paused

    def stop(self):
        # Simple non-blocking kill
        if self.fetch_process:
            self.fetch_process.kill()
            self.fetch_process = None
        if self.mpv_process:
            self.mpv_process.kill()  # Aggressive kill to ensure it stops immediately
            self.mpv_process = None
        if self.download_process:
            self.download_process.kill()
            self.download_process = None
        self.is_paused = False
    def download_audio(self, video_id, progress_callback=None, custom_path=None):
        """Download audio using yt-dlp"""
        # Define download directory
        if custom_path:
            target_dir = custom_path
        else:
            # Mirroring logic in ut_app.py
            n900_dl_dir = "/home/user/MyDocs/uToopDownloads"
            generic_dl_dir = os.path.expanduser("~/uToopDownloads")
            target_dir = n900_dl_dir if os.path.exists("/home/user/MyDocs") else generic_dl_dir

        os.makedirs(target_dir, exist_ok=True)
        download_path = os.path.join(target_dir, "%(title)s.%(ext)s")
        
        cmd = [
            "yt-dlp",
            "-x",
            "-f", "bestaudio[ext=m4a]",
            "--newline",
            "-o", download_path,
            f"https://www.youtube.com/watch?v={video_id}"
        ]
        try:
            self.download_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            
            for line in self.download_process.stdout:
                if progress_callback:
                    if "[download]" in line and "%" in line:
                        try:
                            # Extract percentage like " 10.5%"
                            parts = line.split()
                            for p in parts:
                                if "%" in p:
                                    percentage = p.replace("%", "")
                                    progress_callback(percentage)
                                    break
                        except:
                            pass
                    elif "[ExtractAudio]" in line or "[ffmpeg]" in line or "Destination:" in line and ".mp3" in line:
                        progress_callback("CONVERTING")
            
            self.download_process.wait()

            # Check if process was intentionally terminated
            if self.download_process.returncode != 0:
                if self.download_process.returncode < 0: # Process was killed
                    return "STOPPED"
                return False

            self.download_process = None
            return True
        except Exception as e:
            print(f"DEBUG: Download failed: {e}")
            self.download_process = None
            return False

    def _wait_for_finish(self):
        if self.mpv_process:
            self.mpv_process.wait()
            if self.mpv_process and self.on_finish_callback:
                self.on_finish_callback()
