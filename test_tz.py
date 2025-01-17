import unittest
from unittest.mock import patch, MagicMock
import sqlite3
import os
import time
import tkinter as tk
from tkinter import ttk
from tz import create_db, get_system_data, SystemMonitorApp


class TestTreeview(ttk.Treeview):
    def __init__(self, *args, **kwargs):
        print("TestTreeview создан!", args, kwargs)
        super().__init__(*args, **kwargs)
        self.insert_calls = []  # Хранилище для фиксации вызовов insert
        self.columns = kwargs.get('columns', [])
        self.show = kwargs.get('show', '')

    def insert(self, parent, index, iid=None, **kwargs):
        print(f"TestTreeview.insert вызван: parent={parent}, index={index}, kwargs={kwargs}")
        self.insert_calls.append({'parent': parent, 'index': index, **kwargs})
        return super().insert(parent, index, iid=iid, **kwargs)


class TestSystemMonitor(unittest.TestCase):
    DB_NAME = "system_data.db"

    def setUp(self):
        """Создает тестовую базу данных перед каждым тестом."""
        self.db_name = TestSystemMonitor.DB_NAME
        create_db()

        # Создаем тестовое окно
        self.root = tk.Tk()
        self.app = SystemMonitorApp(self.root)

        # Останавливаем автоматическое обновление интерфейса
        self.app.stop_update()

    def tearDown(self):
        """Удаляет тестовую базу данных после каждого теста."""
        self.app.stop_update()
        if os.path.exists(self.db_name):
            os.remove(self.db_name)
        self.root.destroy()

    def test_create_db(self):
        """Тестирует создание базы данных."""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='system_data';")
            table = cursor.fetchone()
        self.assertIsNotNone(table, "Таблица system_data не создана")

    @patch('psutil.cpu_percent', return_value=50.0)
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    def test_get_system_data(self, mock_disk, mock_memory, mock_cpu):
        """Тестирует получение системных данных."""
        mock_memory.return_value = MagicMock(available=8 * 1024 ** 3, total=16 * 1024 ** 3)
        mock_disk.return_value = MagicMock(free=200 * 1024 ** 3, total=500 * 1024 ** 3)

        cpu, memory, disk = get_system_data()

        self.assertEqual(cpu, 50.0, "Некорректная загрузка ЦП")
        self.assertEqual(memory.available, 8 * 1024 ** 3, "Некорректная доступная память")
        self.assertEqual(disk.free, 200 * 1024 ** 3, "Некорректное свободное место на диске")

    @patch('tz.get_system_data')
    def test_record_data(self, mock_get_data):
        """Тестирует запись данных в базу данных."""
        mock_get_data.return_value = (
            50.0,
            MagicMock(available=8 * 1024 ** 3, total=16 * 1024 ** 3),
            MagicMock(free=200 * 1024 ** 3, total=500 * 1024 ** 3),
        )

        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            cpu, memory, disk = get_system_data()
            cursor.execute(
                "INSERT INTO system_data (timestamp, cpu_usage, memory_available, memory_total, disk_free, disk_total) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    timestamp,
                    cpu,
                    memory.available / 1024 ** 3,
                    memory.total / 1024 ** 3,
                    disk.free / 1024 ** 3,
                    disk.total / 1024 ** 3,
                ),
            )
            conn.commit()

            cursor.execute("SELECT * FROM system_data")
            data = cursor.fetchall()

        self.assertEqual(len(data), 1, "Данные не записаны в базу данных")
        self.assertEqual(
            data[0][1], timestamp, "Время записи в базе данных не совпадает с ожидаемым"
        )

    @patch('tz.tk.Tk')
    def test_gui_initialization(self, mock_tk):
        """Тестирует инициализацию графического интерфейса."""
        mock_root = MagicMock()
        app = SystemMonitorApp(mock_root)

        self.assertIsNotNone(app.cpu_label, "Метка CPU не создана")
        self.assertIsNotNone(app.memory_label, "Метка памяти не создана")
        self.assertIsNotNone(app.disk_label, "Метка диска не создана")

    @patch("sqlite3.connect")
    def test_show_history_with_data(self, mock_connect):
        """Тестирует отображение истории в интерфейсе."""
        # Подготовка данных
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            (1, "2025-01-17 15:34:56", 15.5, 4.0, 8.0, 50.0, 100.0),
            (2, "2025-01-17 15:35:56", 20.0, 3.5, 8.0, 48.0, 100.0),
        ]
        mock_connect.return_value.__enter__.return_value.cursor.return_value = mock_cursor

        # Замена Treeview для проверки вызовов
        with patch("tz.Treeview") as MockTreeview:
            mock_treeview = MockTreeview.return_value

            # Вызов метода
            self.app.show_history()

            # Проверка, что окно истории создано
            self.assertTrue(hasattr(self.app, "history_window"))
            self.assertTrue(mock_treeview.pack.called)

            # Проверка вызовов метода insert
            actual_calls = mock_treeview.insert.call_args_list
            self.assertEqual(len(actual_calls), 2)

            for i, call in enumerate(actual_calls):
                # Позиционные аргументы
                self.assertEqual(call[0], ("", tk.END))

                # Проверка значений
                actual_values = call[1]["values"]
                expected_row = mock_cursor.fetchall.return_value[i]

                # Проверка идентификатора
                self.assertEqual(actual_values[0], expected_row[0])

                # Проверка формата времени
                self.assertRegex(
                    actual_values[1], r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}"
                )

                # Проверка остальных значений
                self.assertEqual(actual_values[2:], tuple(f"{v:.2f}" for v in expected_row[2:]))

    @patch("sqlite3.connect")
    def test_show_history_no_data(self, mock_connect):
        # Подготовка пустых данных
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_connect.return_value.__enter__.return_value.cursor.return_value = mock_cursor

        # Проверка показа сообщения при отсутствии данных
        with patch("tkinter.messagebox.showinfo") as mock_messagebox:
            self.app.show_history()
            mock_messagebox.assert_called_once_with("История", "Нет данных для отображения.")


if __name__ == "__main__":
    unittest.main()
