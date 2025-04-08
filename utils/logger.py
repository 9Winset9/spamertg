import os
import time
from datetime import datetime
from colorama import Fore, Style

class Logger:
    def __init__(self, log_dir="logs"):
        self.log_dir = log_dir
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # Создаем лог-файл с датой
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.log_file = os.path.join(log_dir, f"spamer_log_{timestamp}.txt")
        
        # Заголовок лог-файла
        with open(self.log_file, "w", encoding="utf-8") as f:
            f.write("TGSPAMER v1.2 Log File\n")
            f.write("=" * 50 + "\n")
            f.write(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 50 + "\n\n")

    def log(self, chat_id, status, color=Fore.WHITE):
        """Записывает лог в файл и возвращает отформатированную строку"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Форматируем строку для консоли
        console_msg = f"{color}{timestamp} {chat_id}: {status}{Style.RESET_ALL}"
        
        # Форматируем строку для файла
        file_msg = f"{timestamp} {chat_id}: {status}\n"
        
        # Записываем в файл
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(file_msg)
        
        return console_msg

    def get_log_file(self):
        """Возвращает путь к текущему лог-файлу"""
        return self.log_file

# Создаем единственный экземпляр логгера
logger = Logger()
