import time
import psutil
import threading
import json
import os
import tkinter as tk
from tkinter import colorchooser, font

# --- Configuration Handling ---
CONFIG_DIR = os.path.join(os.getenv('APPDATA'), 'NetworkMonitor')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')

DEFAULT_CONFIG = {
    'font_size': 12,
    'text_color': 'white',
    'background_color': 'black',
    'unit': 'KB/s',
    'window_x': 100,
    'window_y': 100,
    'opacity': 1.0
}

def load_config():
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)
    if not os.path.exists(CONFIG_FILE):
        return DEFAULT_CONFIG
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            for key, value in DEFAULT_CONFIG.items():
                config.setdefault(key, value)
            return config
    except (json.JSONDecodeError, IOError):
        return DEFAULT_CONFIG

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

config = load_config()

# --- Main Application ---
class NetworkMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Network Monitor")
        self.root.overrideredirect(True)
        self.root.wm_attributes("-topmost", True)
        # The color set here will be made transparent
        self.root.wm_attributes("-transparentcolor", config['background_color'])
        self.root.configure(bg=config['background_color'])
        self.root.geometry(f"+{config['window_x']}+{config['window_y']}")
        self.root.attributes("-alpha", config['opacity'])

        self.label_font = font.Font(family="Arial", size=config['font_size'])
        self.speed_label = tk.Label(
            self.root, 
            text="Starting...", 
            font=self.label_font, 
            fg=config['text_color'], 
            bg=config['background_color']
        )
        self.speed_label.pack()

        self.last_upload = 0
        self.last_download = 0
        self.running = True

        self._offset_x = 0
        self._offset_y = 0
        self.speed_label.bind('<Button-1>', self.on_click)
        self.speed_label.bind('<B1-Motion>', self.on_drag)
        self.speed_label.bind('<ButtonRelease-1>', self.on_release)

        self.menu = tk.Menu(self.root, tearoff=0)
        self.menu.add_command(label="Settings", command=self.open_settings)
        self.menu.add_command(label="Quit", command=self.on_quit)
        self.speed_label.bind('<Button-3>', self.show_menu)

        self.root.after(1000, self.keep_on_top)

    def keep_on_top(self):
        self.root.wm_attributes("-topmost", True)
        self.root.after(2000, self.keep_on_top)

    def on_click(self, event):
        self._offset_x = event.x
        self._offset_y = event.y

    def on_drag(self, event):
        x = self.root.winfo_pointerx() - self._offset_x
        y = self.root.winfo_pointery() - self._offset_y
        self.root.geometry(f"+{x}+{y}")

    def on_release(self, event):
        config['window_x'] = self.root.winfo_x()
        config['window_y'] = self.root.winfo_y()
        save_config(config)

    def show_menu(self, event):
        self.menu.post(event.x_root, event.y_root)

    def get_network_speed(self):
        last_io = psutil.net_io_counters()
        time.sleep(1)
        current_io = psutil.net_io_counters()
        upload = current_io.bytes_sent - last_io.bytes_sent
        download = current_io.bytes_recv - last_io.bytes_recv
        return upload, download

    def format_speed(self, speed_bytes):
        if config['unit'] == 'MB/s':
            return speed_bytes / (1024 * 1024), "MB/s"
        else:
            return speed_bytes / 1024, "KB/s"

    def update_loop(self):
        while self.running:
            self.last_upload, self.last_download = self.get_network_speed()
            self.update_label()

    def update_label(self):
        upload_val, unit = self.format_speed(self.last_upload)
        download_val, _ = self.format_speed(self.last_download)
        up_text = f"↑ {upload_val:.1f}"
        down_text = f"↓ {download_val:.1f} {unit}"
        self.speed_label.config(text=f"{up_text}\n{down_text}")

    def on_quit(self):
        self.running = False
        self.root.quit()

    def open_settings(self):
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings")

        def apply_settings():
            try:
                config['font_size'] = font_size_var.get()
                config['unit'] = unit_var.get()
                config['opacity'] = opacity_var.get() / 100.0
                self.label_font.config(size=config['font_size'])
                self.root.attributes("-alpha", config['opacity'])
                save_config(config)
                self.update_label()
            except (tk.TclError, ValueError):
                pass

        def choose_text_color():
            color_code = colorchooser.askcolor(title="Choose text color", initialcolor=config['text_color'])
            if color_code and color_code[1]:
                new_color = color_code[1]
                # Prevent text from being same as background
                if new_color == config['background_color']:
                    return 
                config['text_color'] = new_color
                self.speed_label.config(fg=config['text_color'])
                save_config(config)

        def choose_bg_color():
            color_code = colorchooser.askcolor(title="Choose background color", initialcolor=config['background_color'])
            if color_code and color_code[1]:
                new_bg_color = color_code[1]
                config['background_color'] = new_bg_color
                
                # Smartly adjust text color if it matches the new background
                if config['text_color'] == new_bg_color:
                    r, g, b = color_code[0]
                    # Determine if color is light or dark and set contrast
                    if (r * 0.299 + g * 0.587 + b * 0.114) > 186:
                        config['text_color'] = 'black'
                    else:
                        config['text_color'] = 'white'
                    self.speed_label.config(fg=config['text_color'])

                self.root.configure(bg=new_bg_color)
                self.speed_label.config(bg=new_bg_color)
                self.root.wm_attributes("-transparentcolor", new_bg_color)
                save_config(config)

        font_size_var = tk.IntVar(value=config['font_size'])
        tk.Label(settings_window, text="Font Size:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        tk.Entry(settings_window, textvariable=font_size_var).grid(row=0, column=1, padx=5, pady=5)

        unit_var = tk.StringVar(value=config['unit'])
        tk.Label(settings_window, text="Unit:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        tk.OptionMenu(settings_window, unit_var, "KB/s", "MB/s").grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        tk.Label(settings_window, text="Text Color:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        tk.Button(settings_window, text="Choose...", command=choose_text_color).grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        tk.Label(settings_window, text="Background:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        tk.Button(settings_window, text="Choose...", command=choose_bg_color).grid(row=3, column=1, padx=5, pady=5, sticky="ew")

        opacity_var = tk.IntVar(value=int(config['opacity'] * 100))
        tk.Label(settings_window, text="Opacity (%):").grid(row=4, column=0, padx=5, pady=5, sticky="w")
        tk.Scale(settings_window, from_=10, to=100, orient=tk.HORIZONTAL, variable=opacity_var).grid(row=4, column=1, padx=5, pady=5, sticky="ew")

        tk.Button(settings_window, text="Apply & Close", command=lambda: [apply_settings(), settings_window.destroy()]).grid(row=5, column=0, columnspan=2, pady=10)

    def run(self):
        update_thread = threading.Thread(target=self.update_loop)
        update_thread.daemon = True
        update_thread.start()
        self.root.mainloop()

if __name__ == "__main__":
    root = tk.Tk()
    app = NetworkMonitorApp(root)
    app.run()
