from telethon import TelegramClient
import asyncio
import json
import os
import time
from colorama import init, Fore, Back, Style
import keyboard
import threading
from queue import Queue
import logging
from datetime import datetime
from chats.AnonRuBot import AnonRuBotWorker
from chats.AnonimnyyChatBot import AnonimnyyChatBotWorker
import ctypes
from dotenv import load_dotenv
import sys
import win32gui  # Добавляем импорт для работы с окнами Windows
import win32process
import win32api

# Загружаем переменные окружения
load_dotenv()

# Устанавливаем заголовок окна
WINDOW_TITLE = "TGSPAMER v1.2"
ctypes.windll.kernel32.SetConsoleTitleW(WINDOW_TITLE)

# Инициализация colorama
init()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

LOGO = f"""{Fore.MAGENTA}
  _____ _____ _____ _____ _____ _____ _____ _____ 
 |_   _|   __|   __|  _  |  _  |     |   __| __  |
   | | |  |  |__   |   __|     | | | |   __|    -|
   |_| |_____|_____|__|  |__|__|_|_|_|_____|__|__|{Style.RESET_ALL}"""

# Определяем цветовую схему
PRIMARY_COLOR = Fore.MAGENTA      # Основной цвет (неоновый розовый)
SECONDARY_COLOR = Fore.CYAN       # Дополнительный цвет (неоновый голубой)
SUCCESS_COLOR = Fore.LIGHTGREEN_EX  # Цвет успеха (яркий зеленый)
ERROR_COLOR = Fore.LIGHTRED_EX    # Цвет ошибки (яркий красный)
INFO_COLOR = Fore.LIGHTBLUE_EX    # Цвет информации (яркий синий)
WARN_COLOR = Fore.LIGHTMAGENTA_EX # Цвет предупреждений (яркий фиолетовый)

# Файлы конфигурации
CONFIG_FILE = "config.json"
ENV_FILE = ".env"

def create_default_config():
    """Создание стандартного конфига"""
    default_config = {
    "delays": {
        "between_messages": 1,
        "after_start": 2,
        "before_next": 2,
        "error_retry": 2,
        "message_timeout": 300,
        "next_command": 2,
        "partner_found": 2,
        "before_cycle": 2,
        "check_messages": 1
    },
    "chats": [
        {
            "chat_id": "@AnonRuBot",
            "enabled": True,
            "voice_enabled": False,
            "voice_first": False
        },
        {
            "chat_id": "@anonimnyychatbot",
            "enabled": True,
            "voice_enabled": False,
            "voice_first": False
        }
    ],
    "messages": ["привет"]
}
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(default_config, f, ensure_ascii=False, indent=4)
    return default_config

def create_default_env():
    """Создание .env файла"""
    if not os.path.exists(ENV_FILE):
        with open(ENV_FILE, 'w') as f:
            f.write("API_ID=\nAPI_HASH=")
        print(f"{WARN_COLOR}Создан файл .env. Пожалуйста, заполните API_ID и API_HASH{Style.RESET_ALL}")
        return False
    return True

def load_config():
    """Загрузка конфигурации из JSON файла"""
    if not os.path.exists(CONFIG_FILE):
        print(f"{Fore.YELLOW}Конфиг не найден. Создаю стандартный конфиг...{Style.RESET_ALL}")
        return create_default_config()
    
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            # Проверяем наличие необходимых полей
            if "delays" not in config:
                config["delays"] = {
                    "between_messages": 1,
                    "after_start": 3,
                    "before_next": 3,
                    "error_retry": 3,
                    "message_timeout": 300
                }
            if "chats" not in config:
                config["chats"] = []
            if "messages" not in config:
                config["messages"] = []
            return config
    except json.JSONDecodeError:
        print(f"{Fore.RED}Ошибка чтения конфига. Создаю новый стандартный конфиг...{Style.RESET_ALL}")
        return create_default_config()
    except Exception as e:
        print(f"{Fore.RED}Ошибка при загрузке конфига: {e}. Создаю новый стандартный конфиг...{Style.RESET_ALL}")
        return create_default_config()

def save_config(config):
    """Сохранение конфигурации в JSON файл"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

def is_window_active():
    """Проверка, является ли окно консоли активным"""
    try:
        # Получаем handle активного окна
        active_window = win32gui.GetForegroundWindow()
        # Получаем заголовок активного окна
        active_title = win32gui.GetWindowText(active_window)
        # Проверяем, совпадает ли заголовок с нашим
        return WINDOW_TITLE in active_title
    except:
        return False

def get_key_press():
    """Ожидание нажатия клавиши только когда окно активно"""
    keyboard.unhook_all()  # Очищаем все предыдущие хуки
    ignored_keys = {'alt', 'tab', 'left alt', 'right alt', 'left windows', 'right windows', 
                   'left shift', 'right shift', 'left ctrl', 'right ctrl', 'menu'}
    
    while True:
        if is_window_active():  # Проверяем, активно ли наше окно
            try:
                event = keyboard.read_event(suppress=False)  # Не подавляем системные клавиши
                if event.event_type == 'down' and event.name not in ignored_keys:
                    return event.name
            except:
                pass
        time.sleep(0.1)  # Задержка для снижения нагрузки на CPU

def show_menu():
    """Отображение главного меню"""
    while True:
        # Проверяем API данные перед показом меню
        api_id = os.getenv('API_ID')
        api_hash = os.getenv('API_HASH')
        
        if not api_id or not api_hash or api_id == "" or api_hash == "":
            clear_console()
            print(LOGO)
            print(f"\n{WARN_COLOR}API данные не настроены.{Style.RESET_ALL}")
            print(f"{PRIMARY_COLOR}Давайте настроим их сейчас.{Style.RESET_ALL}\n")
            
            api_id = clean_input(f"{SECONDARY_COLOR}Введите API ID: {Style.RESET_ALL}")
            api_hash = clean_input(f"{SECONDARY_COLOR}Введите API Hash: {Style.RESET_ALL}")
            
            with open(ENV_FILE, 'w') as f:
                f.write(f"API_ID={api_id}\nAPI_HASH={api_hash}")
            
            load_dotenv()
            print(f"\n{SUCCESS_COLOR}API данные успешно сохранены!{Style.RESET_ALL}")
            time.sleep(1.5)

        clear_console()
        print(LOGO)
        print(f"\n{PRIMARY_COLOR}{'='*50}")
        print(f"{SECONDARY_COLOR}=== Главное меню ===")
        print(f"{PRIMARY_COLOR}{'='*50}{Style.RESET_ALL}")
        print(f"{SECONDARY_COLOR}1. Настроить конфигурацию")
        print(f"2. Запустить отправку сообщений")
        print(f"0. Выход{Style.RESET_ALL}")
        
        print(f"\n{PRIMARY_COLOR}Нажмите клавишу (0-2): {Style.RESET_ALL}")
        choice = get_key_press()
        
        if choice == "1":
            while configure_settings():
                pass
        elif choice == "2":
            clear_console()
            print(LOGO)
            asyncio.run(run_script())
            input(f"\n{PRIMARY_COLOR}Нажмите Enter для продолжения...{Style.RESET_ALL}")
        elif choice == "0":
            clear_console()
            sys.exit()
        else:
            print(f"{ERROR_COLOR}Неверный выбор. Попробуйте снова.{Style.RESET_ALL}")
            time.sleep(1.5)

def configure_settings():
    """Настройка параметров конфигурации"""
    config = load_config()
    
    while True:
        clear_console()
        print(LOGO)
        print(f"\n{PRIMARY_COLOR}{'='*50}")
        print(f"{SECONDARY_COLOR}=== Настройка конфигурации ===")
        print(f"{PRIMARY_COLOR}{'='*50}{Style.RESET_ALL}")
        print(f"{SECONDARY_COLOR}1. API ID (текущее значение: {os.getenv('API_ID', '')})")
        print(f"{SECONDARY_COLOR}2. API Hash (текущее значение: {os.getenv('API_HASH', '')})")
        print(f"{SECONDARY_COLOR}3. Управление чатами")
        print(f"{SECONDARY_COLOR}4. Сообщения для отправки")
        print(f"{SECONDARY_COLOR}5. Настройка задержек")
        print(f"{SECONDARY_COLOR}0. Назад{Style.RESET_ALL}")
        
        print(f"\n{PRIMARY_COLOR}Нажмите клавишу (0-5): {Style.RESET_ALL}")
        choice = get_key_press()
        
        if choice == "1":
            api_id = clean_input(f"{SECONDARY_COLOR}Введите API ID: {Style.RESET_ALL}")
            with open(ENV_FILE, 'r') as f:
                env_data = f.read()
            env_data = env_data.replace(f"API_ID={os.getenv('API_ID', '')}", f"API_ID={api_id}")
            with open(ENV_FILE, 'w') as f:
                f.write(env_data)
            load_dotenv()
        elif choice == "2":
            api_hash = clean_input(f"{SECONDARY_COLOR}Введите API Hash: {Style.RESET_ALL}")
            with open(ENV_FILE, 'r') as f:
                env_data = f.read()
            env_data = env_data.replace(f"API_HASH={os.getenv('API_HASH', '')}", f"API_HASH={api_hash}")
            with open(ENV_FILE, 'w') as f:
                f.write(env_data)
            load_dotenv()
        elif choice == "3":
            manage_chats(config)
        elif choice == "4":
            manage_messages(config)
        elif choice == "5":
            configure_delays(config)
        elif choice == "0":
            break
            
        save_config(config)
    return choice != "0"

def manage_messages(config):
    """Управление сообщениями"""
    while True:
        clear_console()
        print(LOGO)
        print(f"\n{PRIMARY_COLOR}{'='*50}")
        print(f"{SECONDARY_COLOR}=== Управление сообщениями ===")
        print(f"{PRIMARY_COLOR}{'='*50}{Style.RESET_ALL}")
        
        print(f"\n{SECONDARY_COLOR}Текущие сообщения:{Style.RESET_ALL}")
        if not config["messages"]:
            print(f"{WARN_COLOR}Список сообщений пуст{Style.RESET_ALL}")
        else:
            for i, msg in enumerate(config["messages"], 1):
                print(f"{PRIMARY_COLOR}{i}. {msg}{Style.RESET_ALL}")
        
        print(f"\n{SECONDARY_COLOR}1. Добавить сообщение")
        print(f"{SECONDARY_COLOR}2. Удалить сообщение")
        print(f"{SECONDARY_COLOR}0. Назад{Style.RESET_ALL}")
        
        print(f"\n{PRIMARY_COLOR}Нажмите клавишу (0-2): {Style.RESET_ALL}")
        msg_choice = get_key_press()
        
        if msg_choice == "1":
            new_msg = clean_input(f"{SECONDARY_COLOR}Введите новое сообщение: {Style.RESET_ALL}")
            config["messages"].append(new_msg)
            print(f"{SUCCESS_COLOR}Сообщение добавлено!{Style.RESET_ALL}")
            time.sleep(1)
        elif msg_choice == "2":
            if config["messages"]:
                try:
                    msg_num = int(clean_input(f"{SECONDARY_COLOR}Введите номер сообщения для удаления: {Style.RESET_ALL}")) - 1
                    if 0 <= msg_num < len(config["messages"]):
                        deleted_msg = config["messages"].pop(msg_num)
                        print(f"{SUCCESS_COLOR}Удалено сообщение: {deleted_msg}{Style.RESET_ALL}")
                        time.sleep(1)
                    else:
                        print(f"{ERROR_COLOR}Неверный номер сообщения{Style.RESET_ALL}")
                        time.sleep(1)
                except ValueError:
                    print(f"{ERROR_COLOR}Введите корректный номер{Style.RESET_ALL}")
                    time.sleep(1)
            else:
                print(f"{ERROR_COLOR}Список сообщений пуст{Style.RESET_ALL}")
                time.sleep(1)
        elif msg_choice == "0":
            break
        
        save_config(config)

def configure_delays(config):
    """Настройка задержек"""
    while True:
        clear_console()
        print(LOGO)
        print(f"\n{PRIMARY_COLOR}{'='*50}")
        print(f"{SECONDARY_COLOR}=== Настройка задержек ===")
        print(f"{PRIMARY_COLOR}{'='*50}{Style.RESET_ALL}")
        print(f"{SECONDARY_COLOR}1. Задержка между сообщениями: {config['delays']['between_messages']} сек")
        print(f"{SECONDARY_COLOR}2. Задержка после старта диалога: {config['delays']['after_start']} сек")
        print(f"{SECONDARY_COLOR}3. Задержка перед поиском нового собеседника: {config['delays']['before_next']} сек")
        print(f"{SECONDARY_COLOR}4. Задержка при ошибке: {config['delays']['error_retry']} сек")
        print(f"{SECONDARY_COLOR}5. Таймаут ожидания сообщения: {config['delays']['message_timeout']} сек")
        print(f"{SECONDARY_COLOR}6. Задержка после команды /next: {config['delays']['next_command']} сек")
        print(f"{SECONDARY_COLOR}7. Задержка после нахождения собеседника: {config['delays']['partner_found']} сек")
        print(f"{SECONDARY_COLOR}8. Задержка перед следующим циклом: {config['delays']['before_cycle']} сек")
        print(f"{SECONDARY_COLOR}9. Задержка между проверками сообщений: {config['delays']['check_messages']} сек")
        print(f"{SECONDARY_COLOR}0. Назад{Style.RESET_ALL}")
        
        print(f"\n{PRIMARY_COLOR}Нажмите клавишу (0-9): {Style.RESET_ALL}")
        choice = get_key_press()
        
        if choice == "0":
            break
            
        try:
            if choice in ["1", "2", "3", "4", "5", "6", "7", "8", "9"]:
                delay = int(clean_input(f"{SECONDARY_COLOR}Введите новое значение задержки в секундах: {Style.RESET_ALL}"))
                if delay < 0:
                    print(f"{ERROR_COLOR}Ошибка: задержка не может быть отрицательной{Style.RESET_ALL}")
                    print(f"{SECONDARY_COLOR}Нажмите любую клавишу для продолжения...{Style.RESET_ALL}")
                    get_key_press()
                    continue
                
                if choice == "1":
                    config["delays"]["between_messages"] = delay
                elif choice == "2":
                    config["delays"]["after_start"] = delay
                elif choice == "3":
                    config["delays"]["before_next"] = delay
                elif choice == "4":
                    config["delays"]["error_retry"] = delay
                elif choice == "5":
                    config["delays"]["message_timeout"] = delay
                elif choice == "6":
                    config["delays"]["next_command"] = delay
                elif choice == "7":
                    config["delays"]["partner_found"] = delay
                elif choice == "8":
                    config["delays"]["before_cycle"] = delay
                elif choice == "9":
                    config["delays"]["check_messages"] = delay
                
                save_config(config)
                print(f"{SUCCESS_COLOR}Задержка успешно изменена{Style.RESET_ALL}")
                print(f"{SECONDARY_COLOR}Нажмите любую клавишу для продолжения...{Style.RESET_ALL}")
                get_key_press()
            else:
                print(f"{ERROR_COLOR}Неверный выбор. Попробуйте снова.{Style.RESET_ALL}")
                print(f"{SECONDARY_COLOR}Нажмите любую клавишу для продолжения...{Style.RESET_ALL}")
                get_key_press()
        except ValueError:
            print(f"{ERROR_COLOR}Ошибка: введите число{Style.RESET_ALL}")
            print(f"{SECONDARY_COLOR}Нажмите любую клавишу для продолжения...{Style.RESET_ALL}")
            get_key_press()

def sync_chat_settings(config):
    """Синхронизация настроек между чатами"""
    if not config["chats"]:
        return
        
    # Берем настройки из первого чата
    first_chat = config["chats"][0]
    settings_to_sync = {
        "voice_enabled": first_chat.get("voice_enabled", False),
        "voice_first": first_chat.get("voice_first", False),
        "voice_file": first_chat.get("voice_file", None)
    }
    
    # Применяем ко всем остальным чатам
    for chat in config["chats"][1:]:
        for key, value in settings_to_sync.items():
            chat[key] = value

def manage_chats(config):
    """Управление списком чатов"""
    while True:
        clear_console()
        print(LOGO)
        print(f"\n{PRIMARY_COLOR}{'='*50}")
        print(f"{SECONDARY_COLOR}=== Управление чатами ===")
        print(f"{PRIMARY_COLOR}{'='*50}{Style.RESET_ALL}")
        
        sync_status = f"{SUCCESS_COLOR}ВКЛ{PRIMARY_COLOR}" if config.get("sync_settings", False) else f"{ERROR_COLOR}ВЫКЛ{PRIMARY_COLOR}"
        print(f"{PRIMARY_COLOR}Синхронизация настроек: {sync_status} (настройки голоса/отправки наследуются с первого чата){Style.RESET_ALL}\n")
        
        if not config["chats"]:
            print(f"{SECONDARY_COLOR}Список чатов пуст{Style.RESET_ALL}")
        else:
            for i, chat in enumerate(config["chats"], 1):
                status = f"{SUCCESS_COLOR}ВКЛ{Style.RESET_ALL}" if chat["enabled"] else f"{ERROR_COLOR}ВЫКЛ{Style.RESET_ALL}"
                voice_status = ""
                if chat.get("voice_enabled", False):
                    voice_file = chat.get("voice_file", "Не выбран")
                    if voice_file and os.path.isabs(voice_file):
                        voice_file = os.path.basename(voice_file)
                    voice_first = "голос→текст" if chat.get("voice_first", False) else "текст→голос"
                    voice_status = f" | {PRIMARY_COLOR}Голос: {voice_file} ({voice_first}){Style.RESET_ALL}"
                print(f"{PRIMARY_COLOR}{i}. {chat['chat_id']} - {status}{voice_status}{Style.RESET_ALL}")
        
        print(f"\n{SECONDARY_COLOR}1. Включить/выключить чат")
        print(f"2. Настройка голосовых сообщений")
        print(f"3. Включить/выключить синхронизацию")
        print(f"0. Назад{Style.RESET_ALL}")
        
        print(f"\n{PRIMARY_COLOR}Нажмите клавишу (0-3): {Style.RESET_ALL}")
        choice = get_key_press()
        
        if choice == "1" and config["chats"]:
            clear_console()
            print(LOGO)
            print(f"\n{PRIMARY_COLOR}{'='*50}")
            print(f"{SECONDARY_COLOR}=== Выберите чат для переключения ===")
            print(f"{PRIMARY_COLOR}{'='*50}{Style.RESET_ALL}\n")
            
            for i, chat in enumerate(config["chats"], 1):
                status = f"{SUCCESS_COLOR}ВКЛ{Style.RESET_ALL}" if chat["enabled"] else f"{ERROR_COLOR}ВЫКЛ{Style.RESET_ALL}"
                print(f"{PRIMARY_COLOR}{i}. {chat['chat_id']} - {status}{Style.RESET_ALL}")
            
            print(f"\n{PRIMARY_COLOR}Нажмите номер чата (0 для отмены): {Style.RESET_ALL}")
            chat_choice = get_key_press()
            
            if chat_choice.isdigit():
                if chat_choice == "0":
                    continue
                    
                chat_num = int(chat_choice) - 1
                if 0 <= chat_num < len(config["chats"]):
                    config["chats"][chat_num]["enabled"] = not config["chats"][chat_num]["enabled"]
                    save_config(config)
                    status = "включен" if config["chats"][chat_num]["enabled"] else "выключен"
                    print(f"{SUCCESS_COLOR}Чат {config['chats'][chat_num]['chat_id']} {status}{Style.RESET_ALL}")
                    time.sleep(1)
        
        elif choice == "2" and config["chats"]:
            clear_console()
            print(LOGO)
            print(f"\n{PRIMARY_COLOR}{'='*50}")
            print(f"{SECONDARY_COLOR}=== Выберите чат для настройки голосовых ===")
            print(f"{PRIMARY_COLOR}{'='*50}{Style.RESET_ALL}\n")
            
            for i, chat in enumerate(config["chats"], 1):
                print(f"{PRIMARY_COLOR}{i}. {chat['chat_id']}{Style.RESET_ALL}")
            
            print(f"\n{PRIMARY_COLOR}Нажмите номер чата (0 для отмены): {Style.RESET_ALL}")
            chat_choice = get_key_press()
            
            if chat_choice.isdigit():
                if chat_choice == "0":
                    continue
                    
                chat_num = int(chat_choice) - 1
                if 0 <= chat_num < len(config["chats"]):
                    configure_voice_settings(config["chats"][chat_num])
                    if config.get("sync_settings", False):
                        sync_chat_settings(config)
                    save_config(config)
        
        elif choice == "3":
            config["sync_settings"] = not config.get("sync_settings", False)
            status = "включена" if config["sync_settings"] else "выключена"
            print(f"{SUCCESS_COLOR}Синхронизация настроек {status}{Style.RESET_ALL}")
            if config["sync_settings"]:
                sync_chat_settings(config)
            save_config(config)
            time.sleep(1)
        
        elif choice == "0":
            break

def get_voice_file_path(filename):
    """Получает путь к голосовому файлу относительно папки программы"""
    voices_dir = "voices"
    if not os.path.exists(voices_dir):
        os.makedirs(voices_dir)
    return os.path.join(voices_dir, filename)

def configure_voice_settings(chat_config):
    """Настройка голосовых сообщений для чата"""
    while True:
        clear_console()
        print(LOGO)
        print(f"\n{PRIMARY_COLOR}{'='*50}")
        print(f"{SECONDARY_COLOR}=== Настройка голосовых сообщений ===")
        print(f"{PRIMARY_COLOR}{'='*50}{Style.RESET_ALL}")
        
        voice_enabled = chat_config.get("voice_enabled", False)
        voice_first = chat_config.get("voice_first", False)
        current_voice = chat_config.get("voice_file", "Не выбран")
        if current_voice and os.path.isabs(current_voice):
            current_voice = os.path.basename(current_voice)
        
        print(f"{SECONDARY_COLOR}1. Голосовые сообщения: {'Включены' if voice_enabled else 'Выключены'}")
        print(f"{SECONDARY_COLOR}2. Порядок отправки: {'Голос первым' if voice_first else 'Текст первым'}")
        print(f"{SECONDARY_COLOR}3. Выбрать голосовое сообщение (Текущее: {current_voice})")
        print(f"{SECONDARY_COLOR}0. Назад{Style.RESET_ALL}")
        
        print(f"\n{PRIMARY_COLOR}Нажмите клавишу (0-3): {Style.RESET_ALL}")
        choice = get_key_press()
        
        if choice == "1":
            chat_config["voice_enabled"] = not voice_enabled
            status = "включены" if chat_config["voice_enabled"] else "выключены"
            print(f"{SUCCESS_COLOR}Голосовые сообщения {status}{Style.RESET_ALL}")
            time.sleep(0.5)
            
        elif choice == "2":
            chat_config["voice_first"] = not voice_first
            status = "голос первым" if chat_config["voice_first"] else "текст первым"
            print(f"{SUCCESS_COLOR}Установлен порядок: {status}{Style.RESET_ALL}")
            time.sleep(0.5)
            
        elif choice == "3":
            # Кэшируем список файлов для быстрого доступа
            voices_dir = "voices"
            if not os.path.exists(voices_dir):
                os.makedirs(voices_dir)
            
            voice_files = [f for f in os.listdir(voices_dir) if f.endswith(('.ogg', '.mp3', '.wav'))]
            
            if not voice_files:
                print(f"{WARN_COLOR}Нет доступных голосовых файлов в папке voices.{Style.RESET_ALL}")
                print(f"{INFO_COLOR}Поместите файлы .ogg, .mp3 или .wav в папку voices.{Style.RESET_ALL}")
                time.sleep(1.5)
                continue
            
            # Показываем список в новом окне
            clear_console()
            print(LOGO)
            print(f"\n{PRIMARY_COLOR}{'='*50}")
            print(f"{SECONDARY_COLOR}=== Выбор голосового сообщения ===")
            print(f"{PRIMARY_COLOR}{'='*50}{Style.RESET_ALL}\n")
            
            for i, file in enumerate(voice_files, 1):
                print(f"{PRIMARY_COLOR}{i}. {file}{Style.RESET_ALL}")
            
            print(f"\n{PRIMARY_COLOR}Нажмите номер файла (0 для отмены): {Style.RESET_ALL}")
            
            file_choice = get_key_press()
            if file_choice.isdigit():
                if file_choice == "0":
                    continue
                    
                file_num = int(file_choice) - 1
                if 0 <= file_num < len(voice_files):
                    selected_file = voice_files[file_num]
                    chat_config["voice_file"] = get_voice_file_path(selected_file)
                    print(f"{SUCCESS_COLOR}Выбран файл: {selected_file}{Style.RESET_ALL}")
                    time.sleep(0.5)
                
        elif choice == "0":
            break

def clean_input(prompt=""):
    """
    Функция для корректного получения ввода от пользователя
    с предварительной очисткой буфера и форматированием
    """
    sys.stdout.flush()  # Очищаем буфер вывода
    print()  # Добавляем пустую строку для отделения
    return input(prompt).strip()  # Удаляем лишние пробелы

def clear_console():
    """Очистка консоли"""
    os.system('cls' if os.name == 'nt' else 'clear')

class ConsoleUI:
    def __init__(self):
        self.chat_statuses = {}
        self.message_counts = {}
        self.last_update = time.time()
        self.update_interval = 1.0  # Обновление каждую секунду

    def update(self, message_queue):
        current_time = time.time()
        if current_time - self.last_update < self.update_interval:
            return

        self.last_update = current_time
        clear_console()
        print(LOGO)
        print(f"\n{PRIMARY_COLOR}{'='*50}")
        print(f"{SECONDARY_COLOR}=== Статус рассылки ===")
        print(f"{PRIMARY_COLOR}{'='*50}{Style.RESET_ALL}")
        print(f"{SECONDARY_COLOR}Нажмите Ctrl+C для остановки")
        print(f"{SECONDARY_COLOR}Нажмите 'q' для выхода в меню{Style.RESET_ALL}\n")

        while not message_queue.empty():
            msg_type, chat_id, *args = message_queue.get()
            if msg_type == "status":
                self.chat_statuses[chat_id] = (args[0], args[1])
            elif msg_type == "message":
                self.message_counts[chat_id] = args[0]

        # Вывод состояния всех чатов в одну строку
        status_line = []
        for chat_id, (status, color) in self.chat_statuses.items():
            count = self.message_counts.get(chat_id, 0)
            status_line.append(f"{color}{chat_id}: {status} ({count} сообщений){Style.RESET_ALL}")
        
        print(" | ".join(status_line))

async def send_messages(client, config):
    """Отправка всех сообщений в указанные чаты"""
    if 'chats' in config and 'messages' in config:
        if not config['messages']:
            print(f"{ERROR_COLOR}Ошибка: список сообщений пуст. Добавьте сообщения в настройках.{Style.RESET_ALL}")
            return
            
        try:
            message_queue = Queue()
            console_ui = ConsoleUI()
            workers = []

            # Создаем воркеры для каждого включенного чата
            for chat in config['chats']:
                if chat['enabled']:
                    # Копируем сообщения и задержки в конфиг чата
                    chat['messages'] = config['messages']
                    chat['delays'] = config['delays']
                    
                    # Создаем соответствующий воркер в зависимости от чата
                    if chat['chat_id'] == "@AnonRuBot":
                        worker = AnonRuBotWorker(client, chat, message_queue)
                    elif chat['chat_id'] == "@anonimnyychatbot":
                        worker = AnonimnyyChatBotWorker(client, chat, message_queue)
                    else:
                        continue
                        
                    workers.append(worker)

            if not workers:
                print(f"{ERROR_COLOR}Ошибка: нет активных чатов{Style.RESET_ALL}")
                return

            # Запускаем все воркеры
            tasks = [worker.run() for worker in workers]
            main_task = asyncio.gather(*tasks)

            # Запускаем обработку клавиатуры
            keyboard.on_press_key('q', lambda _: setattr(send_messages, 'exit_requested', True))
            send_messages.exit_requested = False

            try:
                while not send_messages.exit_requested:
                    console_ui.update(message_queue)
                    await asyncio.sleep(0.1)

                # Отправляем /stop во все активные чаты перед выходом
                for chat in config['chats']:
                    if chat['enabled']:
                        try:
                            await client.send_message(chat['chat_id'], "/stop")
                            print(f"{SECONDARY_COLOR}Отправлен /stop в {chat['chat_id']}{Style.RESET_ALL}")
                        except Exception as e:
                            print(f"{ERROR_COLOR}Ошибка при отправке /stop в {chat['chat_id']}: {e}{Style.RESET_ALL}")

                # Останавливаем всех воркеров
                for worker in workers:
                    worker.stop()

                # Ждем завершения всех задач с таймаутом
                try:
                    await asyncio.wait_for(main_task, timeout=5.0)
                except asyncio.TimeoutError:
                    print(f"{WARN_COLOR}Превышено время ожидания завершения задач{Style.RESET_ALL}")
                except Exception as e:
                    print(f"{ERROR_COLOR}Ошибка при завершении задач: {e}{Style.RESET_ALL}")

            except KeyboardInterrupt:
                # Также отправляем /stop при Ctrl+C
                for chat in config['chats']:
                    if chat['enabled']:
                        try:
                            await client.send_message(chat['chat_id'], "/stop")
                            print(f"{SECONDARY_COLOR}Отправлен /stop в {chat['chat_id']}{Style.RESET_ALL}")
                        except Exception as e:
                            print(f"{ERROR_COLOR}Ошибка при отправке /stop в {chat['chat_id']}: {e}{Style.RESET_ALL}")

                # Останавливаем всех воркеров
                for worker in workers:
                    worker.stop()

                # Ждем завершения всех задач с таймаутом
                try:
                    await asyncio.wait_for(main_task, timeout=5.0)
                except asyncio.TimeoutError:
                    print(f"{WARN_COLOR}Превышено время ожидания завершения задач{Style.RESET_ALL}")
                except Exception as e:
                    print(f"{ERROR_COLOR}Ошибка при завершении задач: {e}{Style.RESET_ALL}")

            finally:
                keyboard.unhook_all()
                clear_console()
                return

        except Exception as e:
            print(f"\n{ERROR_COLOR}Критическая ошибка: {e}{Style.RESET_ALL}")
        finally:
            keyboard.unhook_all()
            clear_console()
    else:
        print(f"{ERROR_COLOR}Ошибка: в конфигурации отсутствуют данные чатов или сообщения{Style.RESET_ALL}")

async def wait_for_message(client, chat_id, target_message, timeout=300):
    """Ожидание определенного сообщения в чате"""
    print(f"\n{PRIMARY_COLOR}Ожидание сообщения '{target_message}'...{Style.RESET_ALL}")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            if keyboard.is_pressed('q'):
                return False
                
            messages = await client.get_messages(chat_id, limit=10)
            for message in messages:
                if message.text and target_message in message.text:
                    print(f"{SUCCESS_COLOR}✓ Найдено сообщение: {target_message}{Style.RESET_ALL}")
                    return True
        except Exception as e:
            print(f"{ERROR_COLOR}Ошибка при проверке сообщений: {e}{Style.RESET_ALL}")
        
        await asyncio.sleep(2)
    
    print(f"{ERROR_COLOR}Время ожидания истекло ({timeout} секунд){Style.RESET_ALL}")
    return False

async def run_script():
    """Запуск скрипта отправки сообщений"""
    config = load_config()
    
    api_id = os.getenv('API_ID')
    api_hash = os.getenv('API_HASH')
    
    if not config["chats"]:
        print(f"{ERROR_COLOR}Ошибка: не добавлены чаты{Style.RESET_ALL}")
        return
    
    if not config["messages"]:
        print(f"{ERROR_COLOR}Ошибка: не добавлены сообщения для отправки{Style.RESET_ALL}")
        return
    
    client = TelegramClient('session_name', api_id, api_hash)
    
    try:
        print(f"\n{INFO_COLOR}Подключение к Telegram...{Style.RESET_ALL}")
        await client.start()
        print(f"{SUCCESS_COLOR}Подключение успешно!{Style.RESET_ALL}")
        
        print(f"\n{INFO_COLOR}Начинаю отправку сообщений...{Style.RESET_ALL}")
        await send_messages(client, config)
        print(f"\n{SUCCESS_COLOR}Отправка сообщений завершена!{Style.RESET_ALL}")
        
    except Exception as e:
        print(f"{ERROR_COLOR}Произошла ошибка: {e}{Style.RESET_ALL}")
    finally:
        await client.disconnect()

def check_required_files():
    """Проверка наличия необходимых файлов и папок"""
    print(f"\n{PRIMARY_COLOR}Проверка необходимых файлов и папок...{Style.RESET_ALL}")
    
    # Проверка и создание папки voices
    voices_dir = "voices"
    if not os.path.exists(voices_dir):
        print(f"{WARN_COLOR}Папка voices не найдена. Создаю...{Style.RESET_ALL}")
        os.makedirs(voices_dir)
        print(f"{SUCCESS_COLOR}Папка voices создана успешно{Style.RESET_ALL}")
    else:
        print(f"{SUCCESS_COLOR}Папка voices найдена{Style.RESET_ALL}")
    
    # Проверка наличия голосовых файлов
    voice_files = [f for f in os.listdir(voices_dir) if f.endswith(('.ogg', '.mp3', '.wav'))]
    if not voice_files:
        print(f"{WARN_COLOR}В папке voices нет голосовых файлов{Style.RESET_ALL}")
        print(f"{INFO_COLOR}Поместите файлы .ogg, .mp3 или .wav в папку voices{Style.RESET_ALL}")
    else:
        print(f"{SUCCESS_COLOR}Найдено голосовых файлов: {len(voice_files)}{Style.RESET_ALL}")
    
    # Проверка конфига
    if not os.path.exists(CONFIG_FILE):
        print(f"{WARN_COLOR}Файл конфигурации не найден. Создаю стандартный конфиг...{Style.RESET_ALL}")
        create_default_config()
        print(f"{SUCCESS_COLOR}Файл конфигурации создан успешно{Style.RESET_ALL}")
    else:
        print(f"{SUCCESS_COLOR}Файл конфигурации найден{Style.RESET_ALL}")
    
    # Проверка .env файла
    if not os.path.exists(ENV_FILE):
        print(f"{WARN_COLOR}Файл .env не найден. Создаю...{Style.RESET_ALL}")
        with open(ENV_FILE, 'w') as f:
            f.write("API_ID=\nAPI_HASH=")
    
    print(f"\n{PRIMARY_COLOR}Проверка завершена{Style.RESET_ALL}")
    time.sleep(1.5)
    return True

if __name__ == "__main__":
    clear_console()
    print(LOGO)
    check_required_files()
    show_menu()