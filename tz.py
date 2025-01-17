import os
import psutil
import time
import sqlite3
import tkinter as tk
from tkinter import messagebox
import threading
from queue import Queue
from tkinter.ttk import Treeview


# Настройки приложения
UPDATE_INTERVAL = 1  # Интервал обновления в секундах
DB_NAME = "system_data.db"

# Создание базы данных и таблицы
def create_db():
    if not os.path.exists(DB_NAME):
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS system_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    cpu_usage REAL,
                    memory_available REAL,
                    memory_total REAL,
                    disk_free REAL,
                    disk_total REAL
                )
                """
            )
            conn.commit()

# Получение данных о загрузке
def get_system_data():
    cpu_usage = psutil.cpu_percent(interval=None)
    memory_usage = psutil.virtual_memory()
    disk_usage = psutil.disk_usage('/')
    return cpu_usage, memory_usage, disk_usage

# Класс для приложения
class SystemMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Уровень загруженности:")

        self.recording = False
        self.start_time = None
        self.data_queue = Queue()

        # Создание интерфейса
        self.create_widgets()
        self.update_task = self.root.after(0, self.update_data)

    def create_widgets(self):
        self.cpu_label = tk.Label(self.root, text="ЦП: 0.00%")
        self.cpu_label.pack()

        self.memory_label = tk.Label(self.root, text="ОЗУ: 0.00ГБ / 0.00ГБ")
        self.memory_label.pack()

        self.disk_label = tk.Label(self.root, text="ПЗУ: 0.00ГБ / 0.00ГБ")
        self.disk_label.pack()

        self.start_button = tk.Button(self.root, text="Начать запись", command=self.start_recording)
        self.start_button.pack()

        self.stop_button = tk.Button(self.root, text="Остановить", command=self.stop_recording)
        self.stop_button.pack_forget()

        self.timer_label = tk.Label(self.root, text="00:00:00")
        self.timer_label.pack_forget()

        self.history_button = tk.Button(self.root, text="История", command=self.show_history)
        self.history_button.pack()

    def update_data(self):
        cpu_usage, memory_usage, disk_usage = get_system_data()
        self.cpu_label.config(text=f"ЦП: {cpu_usage:.2f}%")
        self.memory_label.config(
            text=f"ОЗУ: {memory_usage.available / 1024 / 1024 / 1024:.2f}ГБ / {memory_usage.total / 1024 / 1024 / 1024:.2f}ГБ"
        )
        self.disk_label.config(
            text=f"ПЗУ: {disk_usage.free / 1024 / 1024 / 1024:.2f}ГБ / {disk_usage.total / 1024 / 1024 / 1024:.2f}ГБ"
        )
        self.update_task = self.root.after(int(UPDATE_INTERVAL * 1000), self.update_data)

    def stop_update(self):
        if self.update_task:
            self.root.after_cancel(self.update_task)
            self.update_task = None

    def start_recording(self):
        if not self.recording:
            self.recording = True
            self.start_time = time.time()
            self.timer_label.config(text="00:00:00")
            self.timer_label.pack()
            self.start_button.pack_forget()
            self.stop_button.pack()
            self.record_thread = threading.Thread(target=self.record_data, daemon=True)
            self.record_thread.start()
        else:
            messagebox.showinfo("Запись уже идет", "Запись уже идет!")

    def stop_recording(self):
        if self.recording:
            self.recording = False
            self.stop_button.pack_forget()
            self.start_button.pack()
            self.timer_label.pack_forget()
            self.timer_label.config(text="00:00:00")
            self.start_time = None

    def record_data(self):
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            while self.recording:
                #timestamp = time.time()
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                cpu_usage, memory_usage, disk_usage = get_system_data()

                memory_available = round(memory_usage.available / 1024 / 1024 / 1024, 2)
                memory_total = round(memory_usage.total / 1024 / 1024 / 1024, 2)
                disk_free = round(disk_usage.free / 1024 / 1024 / 1024, 2)
                disk_total = round(disk_usage.total / 1024 / 1024 / 1024, 2)

                try:
                    cursor.execute(
                        "INSERT INTO system_data (timestamp, cpu_usage, memory_available, memory_total, disk_free, disk_total) VALUES (?, ?, ?, ?, ?, ?)",
                        (timestamp, cpu_usage, memory_available, memory_total, disk_free, disk_total),
                    )
                    conn.commit()
                except sqlite3.Error as e:
                    print(f"Ошибка записи в базу данных: {e}")

                elapsed_time = time.time() - self.start_time
                minutes, seconds = divmod(int(elapsed_time), 60)
                hours, minutes = divmod(minutes, 60)
                self.data_queue.put(f"{hours:02}:{minutes:02}:{seconds:02}")
                self.root.after(0, self.update_timer)
                time.sleep(UPDATE_INTERVAL)

    def update_timer(self):
        while not self.data_queue.empty():
            self.timer_label.config(text=self.data_queue.get())

    def show_history(self):
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM system_data")
            data = cursor.fetchall()

            # Логирование данных из базы
            print(f"Полученные данные из базы данных: {data}")

            if not data:
                messagebox.showinfo("История", "Нет данных для отображения.")
                return

        self.history_window = tk.Toplevel(self.root)
        self.history_window.title("История записи")

        self.tree = Treeview(
            self.history_window,
            columns=("id", "timestamp", "cpu_usage", "memory_available", "memory_total", "disk_free", "disk_total"),
            show="headings",
        )

        self.tree.heading("id", text="ID")
        self.tree.heading("timestamp", text="Время записи")
        self.tree.heading("cpu_usage", text="ЦП")
        self.tree.heading("memory_available", text="ОЗУ (свободное)")
        self.tree.heading("memory_total", text="ОЗУ (всего)")
        self.tree.heading("disk_free", text="ПЗУ (свободное)")
        self.tree.heading("disk_total", text="ПЗУ (всего)")

        # Вставка данных в Treeview
        for row in data:
            formatted_row = (
                row[0],
                row[1],
                f"{row[2]:.2f}",
                f"{row[3]:.2f}",
                f"{row[4]:.2f}",
                f"{row[5]:.2f}",
                f"{row[6]:.2f}",
            )
            self.tree.insert("", tk.END, values=formatted_row)

        self.tree.pack()


# Создание базы данных
create_db()

# Запуск приложения
root = tk.Tk()
app = SystemMonitorApp(root)
root.protocol("WM_DELETE_WINDOW", lambda: (app.stop_update(), root.destroy()))
root.mainloop()
