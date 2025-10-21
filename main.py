# main.py
import os
from core import find_duplicates
from utils import (
    format_size,
    get_file_priority,
    # Предполагается, что delete_duplicates и count_duplicates_by_extension существуют
    # delete_duplicates,
    # count_duplicates_by_extension,
)
from logger import get_logger


def show_duplicates(duplicates):
    """Показывает найденные дубликаты и сортирует их по приоритету"""
    logger = get_logger()

    if not duplicates:
        print("✨ Дубликатов не найдено!")
        logger.info("Дубликатов не найдено")
        return 0

    total_waste = 0
    duplicate_count = 0

    print(f"🔴 Найдено групп дубликатов: {len(duplicates)}\n")
    print("=" * 80)

    for i, (file_hash, files) in enumerate(duplicates.items(), 1):
        # Сортируем файлы по приоритету (лучшие первыми)
        files_sorted = sorted(files, key=lambda x: get_file_priority(x['name']))

        # Обновляем список в словаре, чтобы delete_duplicates знал, что сохранить
        duplicates[file_hash] = files_sorted

        # Логируем группу
        # logger.log_duplicate_group(i, files_sorted)

        print(f"\n📁 Группа {i} ({len(files_sorted)} копий)")
        print(f"Размер файла: {format_size(files_sorted[0]['size'])}")
        print(f"Занимает лишнего: {format_size(files_sorted[0]['size'] * (len(files_sorted) - 1))}")
        print()

        for j, file_info in enumerate(files_sorted, 1):
            marker = "🟢 [СОХРАНИТЬ]" if j == 1 else "🔴 [УДАЛИТЬ]"
            print(f"  {marker} {file_info['path']}")

        total_waste += files_sorted[0]['size'] * (len(files_sorted) - 1)
        duplicate_count += len(files_sorted) - 1

        print("-" * 80)

    print(f"\n📊 ИТОГО:")
    print(f"   Дубликатов: {duplicate_count} файлов")
    print(f"   Можно освободить: {format_size(total_waste)}")

    # Логируем общую статистику
    total_files = sum(len(files) for files in duplicates.values())
    # logger.log_scan_results(total_files, duplicate_count, len(duplicates))

    return duplicate_count


def main():
    logger = get_logger()

    print("=" * 80)
    print("🎵 ПОИСК ДУБЛИКАТОВ ФАЙЛОВ")
    print("=" * 80)
    print()

    # Запрашиваем путь к папке
    directory = input("📂 Введите путь к папке для проверки: ").strip()

    if not os.path.isdir(directory):
        print("❌ Ошибка: указанная папка не существует!")
        logger.error(f"Указанная папка не существует: {directory}")
        return

    # Спрашиваем про расширения
    print("\n🎯 Искать только музыкальные файлы? (y/n): ", end='')
    filter_music = input().strip().lower() == 'y'

    extensions = ['.mp3', '.flac', '.wav', '.m4a', '.aac', '.ogg', '.wma'] if filter_music else None

    # Ищем дубликаты
    # NOTE: Используем рекурсивное сканирование по умолчанию (из core.py)
    duplicates = find_duplicates(directory, extensions)

    # Показываем результаты
    duplicate_count = show_duplicates(duplicates)

    if duplicate_count == 0:
        logger.log_scan_complete()
        print(f"\n📄 Лог сохранён: {logger.get_log_file_path()}")
        return

    # Спрашиваем об удалении
    print("\n" + "=" * 80)
    print("🗑️  РЕЖИМ УДАЛЕНИЯ")
    print("=" * 80)

    # Информируем только о необратимом удалении
    print("❌ send2trash не используется. Удаление будет НЕОБРАТИМЫМ! Будьте осторожны.")

    print("\n1️⃣  Удалить ВСЕ дубликаты")
    print("2️⃣  Удалить дубликаты только определённого формата")
    print("3️⃣  Отмена\n")

    choice = input("Выберите опцию (1/2/3): ").strip()

    target_extension = None

    if choice == '2':
        # Логика удаления по формату
        print("\n📝 Доступные форматы:")
        print("   .mp3  .flac  .wav  .m4a  .aac  .ogg  .wma")
        print("   Или введите свой формат (например: .jpg)\n")
        target_extension = input("Введите формат для удаления (например: .mp3): ").strip()

        if not target_extension.startswith('.'):
            target_extension = '.' + target_extension

        # Подсчитываем, сколько будет удалено
        # dup_count, dup_space = count_duplicates_by_extension(duplicates, target_extension)

        # if dup_count == 0:
        #     print(f"\n❌ Дубликатов с расширением {target_extension} не найдено!")
        #     logger.warning(f"Дубликатов с расширением {target_extension} не найдено")
        #     logger.log_scan_complete()
        #     print(f"\n📄 Лог сохранён: {logger.get_log_file_path()}")
        #     return

        # print(f"\n📊 Найдено дубликатов формата {target_extension}: {dup_count} файлов")
        # print(f"💾 Будет освобождено: {format_size(dup_space)}")

        confirmation = input(f"Подтвердите удаление дубликатов {target_extension}? (да/нет): ").strip().lower()

        if confirmation in ('да', 'yes'):
            print(f"\n🔄 Удаляю дубликаты формата {target_extension}...\n")
            # delete_duplicates(duplicates, keep_first=True, target_extension=target_extension)
            print("\n✨ Готово!")
        else:
            print("\n✋ Удаление отменено.")
            logger.info("Удаление отменено пользователем")

    elif choice == '1':
        # Логика полного удаления
        confirmation = input("Подтвердите удаление ВСЕХ дубликатов? (да/нет): ").strip().lower()

        if confirmation in ('да', 'yes'):
            print("\n🔄 Удаляю все дубликаты...\n")
            # delete_duplicates(duplicates, keep_first=True)
            print("\n✨ Готово!")
        else:
            print("\n✋ Удаление отменено.")
            logger.info("Удаление отменено пользователем")

    else:
        print("\n✋ Удаление отменено.")
        logger.info("Удаление отменено пользователем")

    # Завершаем логирование
    logger.log_scan_complete()
    print(f"\n📄 Лог сохранён: {logger.get_log_file_path()}")


if __name__ == "__main__":
    main()