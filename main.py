# gamepad_monitor.py — копипаст, pip install pygame pystray pillow pywin32 monitorcontrol pure-python-adb toml
import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import threading
import time
import subprocess
import pygame
import win32gui
import win32con
from pystray import Icon, MenuItem as Item
from PIL import Image, ImageDraw
import win32com.client  # Task Scheduler

CONFIG_DIR = os.path.join(os.getenv('APPDATA'), 'GamepadMonitor')
CONFIG_PATH = os.path.join(CONFIG_DIR, 'config.json')
os.makedirs(CONFIG_DIR, exist_ok=True)

class App:
    def __init__(self):
        self.monitoring = False
        self.config = self.load_config()
        self.root = tk.Tk()
        self.root.title("Gamepad Monitor")
        self.root.geometry("450x400")
        self.setup_ui()
        self.tray_image = self.create_image()
        self.icon = None
        self.monitor_thread = None

    def load_config(self):
        defaults = {
            'tv_ip': '192.168.1.100',
            'adb_wake': ['shell', 'input', 'keyevent', 'KEYCODE_WAKEUP'],
            'adb_steam': ['shell', 'am', 'start', '-a', 'android.intent.action.MAIN', '-n', 'com.valvesoftware.Steam/.BigPictureActivity'],
            'monitor_mode': 'extend',
            'autostart': False
        }
        try:
            with open(CONFIG_PATH, 'r') as f:
                cfg = json.load(f)
                defaults.update(cfg)
        except:
            pass
        return defaults

    def save_config(self):
        with open(CONFIG_PATH, 'w') as f:
            json.dump(self.config, f, indent=2)

    def setup_ui(self):
        ttk.Label(self.root, text="IP ТВ:").pack(pady=5)
        ttk.Entry(self.root, textvariable=tk.StringVar(value=self.config['tv_ip'])).pack()

        ttk.Label(self.root, text="ADB Wake:").pack(pady=5)
        self.adb_wake = tk.Text(self.root, height=2, width=50)
        self.adb_wake.insert('1.0', ' '.join(self.config['adb_wake']))
        self.adb_wake.pack()

        ttk.Button(self.root, text="Сохранить", command=self.save_settings).pack(pady=10)
        ttk.Button(self.root, text="Автозапуск", command=self.toggle_autostart).pack(pady=5)
        ttk.Button(self.root, text="Старт/Пауза", command=self.toggle_monitor).pack(pady=5)

        self.status = ttk.Label(self.root, text="Готов")
        self.status.pack(pady=20)

        self.root.protocol("WM_DELETE_WINDOW", self.to_tray)

    def create_image(self):
        img = Image.new('RGB', (64, 64), (0, 120, 215))
        dc = ImageDraw.Draw(img)
        dc.rectangle((16, 16, 48, 48), fill=(255, 255, 255))
        return img

    def save_settings(self):
        self.config['tv_ip'] = self.root.children['!entry'].children['!entry'].get()
        self.config['adb_wake'] = self.adb_wake.get('1.0', tk.END).strip().split()
        self.save_config()
        messagebox.showinfo("OK", "Сохранено!")

    def is_gamepad(self):
        pygame.init()
        pygame.joystick.init()
        count = pygame.joystick.get_count()
        pygame.quit()
        return count > 0

    def activate(self):
        subprocess.run(["DisplaySwitch.exe", f"/{self.config['monitor_mode']}"], shell=True)
        subprocess.run(["adb", "-s", self.config['tv_ip']] + self.config['adb_wake'])
        time.sleep(2)
        subprocess.run(["adb", "-s", self.config['tv_ip']] + self.config['adb_steam'])
        subprocess.Popen(["start", "steam://open/bigpicture"], shell=True)

    def monitor_loop(self):
        was = False
        while self.monitoring:
            now = self.is_gamepad()
            if now and not was:
                self.root.after(0, lambda: self.status.config(text="TV Mode!"))
                self.activate()
            was = now
            time.sleep(0.5)

    def toggle_monitor(self):
        self.monitoring = not self.monitoring
        if self.monitoring:
            self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
            self.monitor_thread.start()
            self.status.config(text="Мониторинг...")
        else:
            self.status.config(text="Пауза")

    def toggle_autostart(self):
        # Простой реестр
        key = win32gui.RegOpenKeyEx(win32con.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run", 0, win32con.KEY_ALL_ACCESS)
        exe = os.path.abspath(__file__)
        if self.config['autostart']:
            win32gui.RegDeleteValue(key, "GamepadMonitor")
        else:
            win32gui.RegSetValueEx(key, "GamepadMonitor", 0, win32con.REG_SZ, exe)
        self.config['autostart'] = not self.config['autostart']
        self.save_config()

    def to_tray(self):
        self.root.withdraw()
        self.icon = Icon("gm", self.tray_image, menu=Menu(
            Item("Показать", self.show),
            Item("Пауза", self.toggle_monitor),
            Item("Выход", self.quit)
        ))
        self.icon.run()

    def show(self, icon, item):
        icon.stop()
        self.root.after(0, self.root.deiconify)

    def quit(self, icon, item):
        self.monitoring = False
        icon.stop()
        self.root.quit()

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    App().run()