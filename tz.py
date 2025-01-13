import psutil
import time
import sqlite3
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import threading

# Настройки приложения
UPDATE_INTERVAL = 1  # Интервал обновления в секундах
DB_NAME = "system_data.db"

# Создание базы данных и таблицы
def create_db():
    conn = sqlite3.connect(DB_NAME) # Подключается к базе данных
    cursor = conn.cursor() # Создает курсор для выполнения SQL-запросов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_data (
            timestamp REAL PRIMARY KEY,
            cpu_usage REAL,
            memory_available REAL,
            memory_total REAL,
            disk_free REAL,
            disk_total REAL
        )
    """) # Создает таблицу "system_data", если она не существует
    conn.commit() # Сохраняет изменения в базе данных
    conn.close() # Закрывает соединение с базой данных

# Получение данных о загрузке
def get_system_data():
    cpu_usage = psutil.cpu_percent(interval=None) # Получает объект с информацией о загруженности процессора
    memory_usage = psutil.virtual_memory() # Получает объект с информацией о виртуальной памяти
    disk_usage = psutil.disk_usage('/') # Получает объект с информацией о дисковом пространстве корневого раздела
    return cpu_usage, memory_usage, disk_usage

# Обновление данных в интерфейсе
def update_data():
    cpu_usage, memory_usage, disk_usage = get_system_data() # Получает данные о загрузке системы
    cpu_label.config(text=f"ЦП: {cpu_usage:.2f}%") # Обновляет текст метки "ЦП" с использованием полученной загрузки процессора
    memory_label.config(text=f"ОЗУ: {memory_usage.available / 1024 / 1024 / 1024:.2f}ГБ / {memory_usage.total / 1024 / 1024 / 1024:.2f}ГБ")
    disk_label.config(text=f"ПЗУ: {disk_usage.free / 1024 /1024 / 1024:.2f}ГБ / {disk_usage.total / 1024 / 1024 / 1024:.2f}ГБ")
    root.after(int(UPDATE_INTERVAL * 1000), update_data) # Запланирует вызов функции update_data через UPDATE_INTERVAL секунд

# Запись данных в БД
def start_recording():
    global recording, timer_label, start_time # Объявляет переменные как глобальные, чтобы можно было изменять их значения внутри функции
    if not recording: # Проверяет, не идет ли запись уже
        recording = True # Устанавливает флаг записи в True
        start_time = time.time() # Запоминает время начала записи
        timer_label.config(text="00:00:00") # Устанавливает текст метки таймера в "00:00:00"
        timer_label.pack() # Делает метку таймера видимой
        start_button.pack_forget() # Скрывает кнопку "Начать запись"
        stop_button.pack() # Делает кнопку "Остановить" видимой
        threading.Thread(target=record_data).start() # Запускает поток для записи данных в базу данных
    else:
        messagebox.showinfo("Запись уже идет", "Запись уже идет!") # Выводит сообщение, если запись уже идет

# Остановка записи
def stop_recording():
    global recording, timer_label, start_time # Объявляет переменные как глобальные
    if recording: # Проверяет, идет ли запись
        recording = False # Устанавливает флаг записи в False
        stop_button.pack_forget() # Скрывает кнопку "Остановить"
        start_button.pack() # Делает кнопку "Начать запись" видимой
        timer_label.pack_forget() # Скрывает метку таймера
        timer_label.config(text="00:00:00") # Устанавливает текст метки таймера в "00:00:00"
        start_time = None # Сбрасывает время начала записи

# Запись данных в БД в отдельном потоке
def record_data():
    global recording, timer_label, start_time # Объявляет переменные как глобальные
    conn = sqlite3.connect(DB_NAME) # Подключается к базе данных
    cursor = conn.cursor() # Создает курсор для выполнения SQL-запросов
    while recording: # Цикл, который работает, пока флаг записи recording равен True
        timestamp = time.strftime("%H:%M:%S") # Получает текущее время в формате "ЧЧ:ММ:СС"
        cpu_usage, memory_usage, disk_usage = get_system_data() # Получает данные о системе

        # Форматируем данные, чтобы они имели 2 знака после запятой
        memory_available = round(memory_usage.available / 1024 / 1024 / 1024, 2)
        memory_total = round(memory_usage.total / 1024 / 1024 / 1024, 2)
        disk_free = round(disk_usage.free / 1024 / 1024 / 1024, 2)
        disk_total = round(disk_usage.total / 1024 / 1024 / 1024, 2)

        # Выполняет SQL-запрос для вставки данных в таблицу
        cursor.execute(
            "INSERT INTO system_data VALUES (?, ?, ?, ?, ?, ?)",
            (timestamp, cpu_usage, memory_available, memory_total, disk_free, disk_total),
        )
        conn.commit() # Сохраняет изменения в базе данных
        elapsed_time = time.time() - start_time # Вычисляет время, прошедшее с начала записи
        minutes, seconds = divmod(int(elapsed_time), 60) # Преобразует время в минуты и секунды
        hours, minutes = divmod(minutes, 60) # Преобразует время в часы и минуты
        timer_label.config(text=f"{hours:02}:{minutes:02}:{seconds:02}") # Обновляет текст метки таймера
        time.sleep(UPDATE_INTERVAL) # Останавливает поток на `UPDATE_INTERVAL` секунд
    conn.close() # Закрывает соединение с базой данных

# Просмотр истории
def show_history():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor() # Создает курсор для выполнения SQL-запросов
    cursor.execute("SELECT * FROM system_data") # Выполняет SQL-запрос для получения всех данных из таблицы
    data = cursor.fetchall() # Получает все строки данных из таблицы
    conn.close() # Закрывает соединение с базой данных

    history_window = tk.Toplevel(root) # Создает новое окно поверх основного окна
    history_window.title("История записи") # Устанавливает заголовок окна
    tree = ttk.Treeview(history_window, columns=("timestamp", "cpu_usage", "memory_available", "memory_total",
                    "disk_free", "disk_total"), show="headings") # Создает деревовидный виджет для отображения данных
    tree.heading("timestamp", text="Время") # Устанавливает заголовок столбца "timestamp"
    tree.heading("cpu_usage", text="ЦП")
    tree.heading("memory_available", text="ОЗУ (свободное)")
    tree.heading("memory_total", text="ОЗУ (всего)")
    tree.heading("disk_free", text="ПЗУ (свободное)")
    tree.heading("disk_total", text="ПЗУ (всего)")
    for row in data: # Цикл по каждой строке данных
        formatted_row = (
            row[0], # Время
            f"{row[1]:.2f}", # Загрузка процессора (с двумя знаками после запятой)
            f"{row[2]:.2f}",
            f"{row[3]:.2f}",
            f"{row[4]:.2f}",
            f"{row[5]:.2f}",
        )
        tree.insert("", tk.END, values=formatted_row) # Вставляет строку данных в деревовидный виджет
    tree.pack() # Делает деревовидный виджет видимым

# Создание главного окна
root = tk.Tk() # Создает главное окно приложения
root.title("Уровень загруженности:") # Устанавливает заголовок окна

# Создание элементов интерфейса
cpu_label = tk.Label(root, text="ЦП: 0.00%") # Создает метку для отображения загрузки процессора
cpu_label.pack() # Размещает метку в окне
memory_label = tk.Label(root, text="ОЗУ: 0.00ГБ / 0.00ГБ")
memory_label.pack()
disk_label = tk.Label(root, text="ПЗУ: 0.00ГБ / 0.00ГБ")
disk_label.pack()

start_button = tk.Button(root, text="Начать запись", command=start_recording) # Создает кнопку "Начать запись"
start_button.pack() # Размещает кнопку в окне
stop_button = tk.Button(root, text="Остановить", command=stop_recording) # Создает кнопку "Остановить"
stop_button.pack_forget() # Скрывает кнопку "Остановить" по умолчанию

timer_label = tk.Label(root, text="00:00:00") # Создает метку для отображения таймера
timer_label.pack_forget() # Скрывает метку таймера по умолчанию

history_button = tk.Button(root, text="История", command=show_history) # Создает кнопку "История"
history_button.pack() # Размещает кнопку в окне

# Инициализация записи
recording = False # Устанавливает флаг записи в False по умолчанию
start_time = 0 # Инициализирует время начала записи как 0

# Создание базы данных
create_db()# Вызывает функцию для создания базы данных

# Запуск обновления данных
update_data() # Вызывает функцию для обновления данных в интерфейсе

# Запуск приложения
root.mainloop() # Запускает главный цикл приложения Tkinter