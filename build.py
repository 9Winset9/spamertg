import os
import shutil
import subprocess
import sys

def create_releases_dir():
    """Создание папки releases если она не существует"""
    releases_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'releases')
    if not os.path.exists(releases_dir):
        os.makedirs(releases_dir)
    return releases_dir

def clean_build_files():
    """Удаление временных файлов сборки"""
    # Список папок для удаления
    dirs_to_remove = ['build', 'dist', '__pycache__']
    
    # Удаление папок
    for dir_name in dirs_to_remove:
        dir_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), dir_name)
        if os.path.exists(dir_path):
            print(f"Удаление {dir_name}...")
            try:
                shutil.rmtree(dir_path)
            except Exception as e:
                print(f"Ошибка при удалении {dir_name}: {e}")

def compile_program():
    """Сборка программы с помощью PyInstaller"""
    print("=== Начало сборки программы ===")
    
    # Путь к основному скрипту
    main_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'main.py')
    
    # Параметры для PyInstaller
    pyinstaller_args = [
        'pyinstaller',
        '--noconfirm',
        '--onedir',
        '--windowed',
        '--icon=NONE',
        f'--name=TGSPAMER',
        main_script
    ]
    
    try:
        print("Запуск PyInstaller...")
        subprocess.run(pyinstaller_args, check=True)
        print("Сборка успешно завершена!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Ошибка при сборке: {e}")
        return False
    except Exception as e:
        print(f"Непредвиденная ошибка: {e}")
        return False

def move_executable():
    """Перемещение исполняемого файла в папку releases"""
    try:
        # Путь к исполняемому файлу
        src_exe = os.path.join('dist', 'TGSPAMER', 'TGSPAMER.exe')
        releases_dir = create_releases_dir()
        dst_exe = os.path.join(releases_dir, 'TGSPAMER.exe')
        
        # Перемещение файла
        print("Перемещение исполняемого файла в releases...")
        shutil.move(src_exe, dst_exe)
        print("Файл успешно перемещен!")
        return True
    except Exception as e:
        print(f"Ошибка при перемещении файла: {e}")
        return False

def main():
    # Сборка программы
    if not compile_program():
        print("Ошибка при сборке программы")
        return
    
    # Перемещение исполняемого файла
    if not move_executable():
        print("Ошибка при перемещении файла")
        return
    
    # Очистка временных файлов
    clean_build_files()
    print("\nВсе временные файлы успешно удалены!")
    print(f"TGSPAMER.exe успешно создан и находится в папке releases")

if __name__ == "__main__":
    main()
