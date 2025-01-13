import unittest
from unittest.mock import MagicMock, patch
import tz  # Импортируем модуль tz.py
import time
import threading

class TestSystemMonitor(unittest.TestCase):
    """Класс для тестирования функций из модуля tz."""

    @patch('sqlite3.connect')  # Имитируем вызов функции sqlite3.connect
    def test_create_db(self, mock_connect):
        """Проверяет, что функция create_db создает таблицу system_data."""
        cursor = MagicMock()  # Создаем имитацию объекта курсора
        mock_connect.return_value.cursor.return_value = cursor  # Задаем возвращаемое значение для cursor при вызове conn.cursor()
        tz.create_db()  # Вызываем функцию create_db из модуля tz
        mock_connect.assert_called_once_with("system_data.db")  # Проверяем, что функция sqlite3.connect была вызвана один раз с аргументом "system_data.db"
        cursor.execute.assert_called_once_with("""
        CREATE TABLE IF NOT EXISTS system_data (
            timestamp REAL PRIMARY KEY,
            cpu_usage REAL,
            memory_available REAL,
            memory_total REAL,
            disk_free REAL,
            disk_total REAL
        )
    """)  # Проверяем, что метод execute курсора был вызван один раз с правильным SQL-запросом
        mock_connect.return_value.commit.assert_called_once()  # Проверяем, что метод commit соединения был вызван один раз
        mock_connect.return_value.close.assert_called_once()  # Проверяем, что метод close соединения был вызван один раз

    @patch('psutil.cpu_percent')  # Имитируем вызов функции psutil.cpu_percent
    @patch('psutil.virtual_memory')  # Имитируем вызов функции psutil.virtual_memory
    @patch('psutil.disk_usage')  # Имитируем вызов функции psutil.disk_usage
    def test_get_system_data(self, mock_disk_usage, mock_virtual_memory, mock_cpu_percent):
        """Проверяет, что функция get_system_data возвращает корректные данные о системе."""
        mock_cpu_percent.return_value = 50.0  # Задаем возвращаемое значение для имитированной функции psutil.cpu_percent
        mock_virtual_memory.return_value = MagicMock(available=1024 * 1024 * 1024 * 2, total=1024 * 1024 * 1024 * 4)  # Создаем имитацию объекта psutil.virtual_memory с заданными значениями
        mock_disk_usage.return_value = MagicMock(free=1024 * 1024 * 1024 * 1024 * 2, total=1024 * 1024 * 1024 * 1024 * 4)  # Создаем имитацию объекта psutil.disk_usage с заданными значениями
        cpu_usage, memory_usage, disk_usage = tz.get_system_data()  # Вызываем функцию get_system_data из модуля tz
        self.assertEqual(cpu_usage, 50.0)  # Проверяем, что значение cpu_usage равно 50.0
        self.assertEqual(memory_usage.available, 1024 * 1024 * 1024 * 2)  # Проверяем, что значение memory_usage.available равно 1024 * 1024 * 1024 * 2
        self.assertEqual(memory_usage.total, 1024 * 1024 * 1024 * 4)  # Проверяем, что значение memory_usage.total равно 1024 * 1024 * 1024 * 4
        self.assertEqual(disk_usage.free, 1024 * 1024 * 1024 * 1024 * 2)  # Проверяем, что значение disk_usage.free равно 1024 * 1024 * 1024 * 1024 * 2
        self.assertEqual(disk_usage.total, 1024 * 1024 * 1024 * 1024 * 4)  # Проверяем, что значение disk_usage.total равно 1024 * 1024 * 1024 * 1024 * 4

    @patch('tz.cpu_label')
    @patch('tz.memory_label')
    @patch('tz.disk_label')
    @patch('tz.get_system_data')
    def test_update_data(self, mock_get_system_data, mock_disk_label, mock_memory_label, mock_cpu_label):
        """Проверяет, что функция update_data обновляет текст меток с данными о системе."""

        # Задает возвращаемые значения для мок-функции get_system_data
        mock_get_system_data.return_value = (
            50.0,  # cpu_usage
            MagicMock(available=2 * 1024 ** 3, total=4 * 1024 ** 3),  # memory_usage
            MagicMock(free=2 * 1024 ** 3, total=4 * 1024 ** 3)  # disk_usage
        )

        # Вызывает тестируемую функцию
        tz.update_data()

        # Проверяет, что методы config были вызваны с правильными аргументами
        mock_cpu_label.config.assert_called_once_with(text='ЦП: 50.00%')
        mock_memory_label.config.assert_called_once_with(text='ОЗУ: 2.00ГБ / 4.00ГБ')
        mock_disk_label.config.assert_called_once_with(text='ПЗУ: 2.00ГБ / 4.00ГБ')

    def setUp(self):
        # Инициализация объектов
        self.recording = False
        self.timer_label = MagicMock()
        self.start_button = MagicMock()
        self.stop_button = MagicMock()

        tz.timer_label = self.timer_label
        tz.start_button = self.start_button
        tz.stop_button = self.stop_button

    @patch('tz.record_data')  # Имитируем функцию record_data
    @patch('tz.messagebox.showinfo')  # Имитируем всплывающее окно сообщения
    def test_start_recording(self, mock_showinfo, mock_record_data):
        """Тестирует метод start_recording для проверки начала записи."""
        tz.start_recording()  # Вызываем функцию start_recording

        # Проверяем, что флаг записи установлен в True
        self.assertTrue(tz.recording)  # обращайтесь к атрибуту класса

        # Проверяем, что текст метки таймера установлен в "00:00:00"
        self.timer_label.config.assert_called_once_with(text="00:00:00")

        # Проверяем, что метка таймера сделана видимой
        self.timer_label.pack.assert_called_once()

        # Проверяем, что кнопка "Начать запись" скрыта
        self.start_button.pack_forget.assert_called_once()

        # Проверяем, что кнопка "Остановить" видима
        self.stop_button.pack.assert_called_once()

        # Создание потока, который записывает данные
        thread = threading.Thread(target=tz.record_data)
        thread.start()

        # Проверяем, что поток для записи данных был запущен
        self.assertEqual(threading.active_count(), 1)

    @patch('tz.messagebox.showinfo')  # Имитируем всплывающее окно сообщения
    def test_stop_recording(self, mock_showinfo):
        """Тестирует метод stop_recording для проверки остановки записи."""
        tz.recording = True  # Устанавливаем, что запись идет
        tz.start_time = time.time()
        tz.stop_recording()  # Вызываем функцию stop_recording

        # Проверяем, что флаг записи установлен в False
        self.assertFalse(tz.recording)

        # Проверяем, что кнопка "Остановить" скрыта
        self.stop_button.pack_forget.assert_called_once()

        # Проверяем, что кнопка "Начать запись" видима
        self.start_button.pack.assert_called_once()

        # Проверяем, что метка таймера скрыта
        self.timer_label.pack_forget.assert_called_once()

        # Проверяем, что текст метки таймера установлен в "00:00:00"
        self.timer_label.config.assert_called_once_with(text="00:00:00")

        # Проверяем, что время начала записи сброшено
        self.assertIsNone(tz.start_time)

    def tearDown(self):
        # Убедитесь, что объекты очищаются после тестов
        self.recording = False
        self.timer_label = None
        self.start_button = None
        self.stop_button = None


if __name__ == '__main__':
    unittest.main()
