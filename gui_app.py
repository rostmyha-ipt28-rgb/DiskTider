import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import os
import json
from collections import defaultdict
from core import find_duplicates
from utils import format_size, get_file_priority, delete_files_by_list
from color_utils import lighten_color, get_contrast_color

from logger import get_logger

# Конфигурация
MUSIC_EXTENSIONS = ['.mp3', '.flac', '.wav', '.m4a', '.aac', '.ogg', '.wma']

# Список ключевых слов для маркировки рискованных файлов в GUI
RISKY_PATH_KEYWORDS = [
    'SteamLibrary',
    'Program Files',
    'Program Files (x86)',
    'Windows',
    os.path.join('AppData', 'Local'),
    os.path.join('Users', 'Default'),
    'Library/Application Support',  # macOS
    'System Volume Information'
]

THEMES = {
    'light': {
        'bg': '#FAFAFA',
        'fg': '#111827',
        'surface': '#FFFFFF',
        'surface_alt': '#F0F0F0',
        'primary': '#2563EB',
        'danger': '#DC2626',
        'success': '#16A34A',
        'border': '#E0E0E0',
        'text_secondary': '#64748B',
        'treeview_bg': '#FFFFFF',
        'treeview_fg': '#111827',
        'treeview_selected': '#E8F0FF',
        'hover': '#EEEEEE',
        'risk_fg': '#92400E',
        'risk_bg_color': '#FEF3C7',
    },
    'dark': {
        'bg': '#1E1E1E',
        'fg': '#E0E0E0',
        'surface': '#2D2D30',
        'surface_alt': '#000000',
        'primary': '#007ACC',
        'danger': '#F44747',
        'success': '#4EC9B0',
        'border': '#3E3E42',
        'text_secondary': '#858585',
        'treeview_bg': '#252526',
        'treeview_fg': '#CCCCCC',
        'treeview_selected': '#094771',
        'hover': '#383838',
        'risk_fg': '#FCD34D',
        'risk_bg_color': '#443C22',
    }
}


class ModernButton(tk.Button):
    """Кастомная кнопка с плавной анимацией hover и glow"""

    def __init__(self, master, **kwargs):
        self.original_bg = kwargs.get('bg', 'SystemButtonFace')
        self.original_font = kwargs.pop('font', ('Segoe UI', 10))
        self.is_glowing = False
        self.glow_counter = 0
        super().__init__(
            master,
            relief=tk.FLAT,
            borderwidth=0,
            padx=20,
            pady=10,
            cursor='hand2',
            font=self.original_font,
            **kwargs
        )
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)

    def _on_enter(self, e):
        if self['state'] != 'disabled' and not self.is_glowing:
            all_danger_colors = [THEMES[t]['danger'] for t in THEMES]
            is_danger = self.original_bg in all_danger_colors
            parent = self.master
            while not isinstance(parent, DiskTiderGUI) and parent is not None:
                parent = parent.master
            if parent:
                self['bg'] = parent._darken_color(self.original_bg, 0.15) if is_danger else parent._lighten_color(
                    self.original_bg, 0.15)

    def _on_leave(self, e):
        if self['state'] != 'disabled' and not self.is_glowing:
            self['bg'] = self.original_bg

    def start_glow(self, start_color, end_color):
        if not self.is_glowing:
            self.is_glowing = True
            self.glow_start_color = start_color
            self.glow_end_color = end_color
            self._animate_glow()

    def stop_glow(self):
        self.is_glowing = False
        self['bg'] = self.original_bg
        self.glow_counter = 0

    def _animate_glow(self):
        if not self.is_glowing:
            self['bg'] = self.original_bg
            return
        self.glow_counter += 1
        intensity = abs(10 - (self.glow_counter % 20)) / 10
        color = self._interpolate_color(self.glow_start_color, self.glow_end_color, intensity)
        self['bg'] = color
        self.after(100, self._animate_glow)

    def _interpolate_color(self, hex1, hex2, factor):
        try:
            r1, g1, b1 = int(hex1[1:3], 16), int(hex1[3:5], 16), int(hex1[5:7], 16)
            r2, g2, b2 = int(hex2[1:3], 16), int(hex2[3:5], 16), int(hex2[5:7], 16)
            r = int(r1 + (r2 - r1) * factor)
            g = int(g1 + (g2 - g1) * factor)
            b = int(b1 + (b2 - b1) * factor)
            return f'#{r:02x}{g:02x}{b:02x}'
        except:
            return hex1

    def config(self, **kwargs):
        if 'bg' in kwargs:
            self.original_bg = kwargs['bg']
        if 'font' in kwargs:
            self.original_font = kwargs['font']
        super().config(**kwargs)


class DiskTiderGUI(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.current_theme = 'light'
        self.theme = THEMES[self.current_theme]
        self.duplicates_data = {}
        self.logger = get_logger()
        self.status_glow = None
        self.status_var = tk.StringVar(value="Готов к работе")
        self.music_var = tk.BooleanVar()
        self.recursive_var = tk.BooleanVar(value=True)
        self.permission_errors = 0
        self._apply_theme()
        self.pack(fill="both", expand=True)
        self._create_widgets()
        self.load_settings()

    def _lighten_color(self, hex_color, factor):
        return lighten_color(hex_color, factor)

    def _darken_color(self, hex_color, factor):
        try:
            r = int(hex_color[1:3], 16)
            g = int(hex_color[3:5], 16)
            b = int(hex_color[5:7], 16)
            r = max(0, int(r * (1 - factor)))
            g = max(0, int(g * (1 - factor)))
            b = max(0, int(b * (1 - factor)))
            return f'#{r:02x}{g:02x}{b:02x}'
        except:
            return hex_color

    def _check_file_risk(self, filepath):
        """Проверяет, находится ли файл в рискованной системной/программной папке."""
        filepath_lower = filepath.lower().replace(os.sep, '/')
        for keyword in RISKY_PATH_KEYWORDS:
            keyword_lower = keyword.lower().replace(os.sep, '/')
            if keyword_lower in filepath_lower:
                return 'RISK'
        return 'SAFE'

    def _apply_theme(self):
        self.master.configure(bg=self.theme['bg'])
        self.configure(bg=self.theme['bg'])
        style = ttk.Style()
        style.theme_use('default')
        style.configure(
            "Custom.Treeview",
            background=self.theme['treeview_bg'],
            foreground=self.theme['treeview_fg'],
            fieldbackground=self.theme['treeview_bg'],
            borderwidth=0,
            relief='flat',
            rowheight=28
        )
        style.configure(
            "Custom.Treeview.Heading",
            background=self.theme['surface_alt'],
            foreground=self.theme['fg'],
            borderwidth=1,
            relief='flat',
            font=('Segoe UI', 10, 'bold'),
            padding=8
        )
        style.map('Custom.Treeview',
                  background=[('selected', self.theme['treeview_selected'])],
                  foreground=[('selected', self.theme['fg'])])
        if hasattr(self, 'tree'):
            self.tree.tag_configure('keep', foreground=self.theme['success'])
            self.tree.tag_configure('delete', foreground=self.theme['danger'])
            self.tree.tag_configure('group', font=('Segoe UI', 10, 'bold'))

            # Настройка стиля для рискованного файла
            self.tree.tag_configure('risk',
                                    foreground=self.theme['risk_fg'],  # Оранжевый/желтый текст
                                    background=self.theme['risk_bg_color'])  # Светлый/темный фон

    def _toggle_theme(self):
        self.current_theme = 'light' if self.current_theme == 'dark' else 'dark'
        self.theme = THEMES[self.current_theme]
        theme_icon = "🌙" if self.current_theme == 'light' else "🌞"

        # >>> ИЗМЕНЕНИЕ: Установка BG кнопки в цвет фона (bg)
        self.theme_button.config(text=theme_icon, bg=self.theme['bg'], fg=self.theme['fg'])

        self._apply_theme()
        self._refresh_widgets()
        self._setup_treeview_hover()

    def _refresh_widgets(self):
        self.configure(bg=self.theme['bg'])
        for widget in self.winfo_children():
            self._update_widget_colors(widget)
        if self.status_glow:
            self.status_glow.start_color = self.theme['surface']
            self.status_glow.end_color = self.theme['primary']
            if self.status_glow.is_glowing:
                self.status_glow.stop_glow()
                self.status_glow.start_glow()

    def _update_widget_colors(self, widget):
        widget_type = widget.winfo_class()
        if widget_type in ('Frame', 'TFrame'):
            widget.configure(bg=self.theme['bg'])
        elif widget_type == 'Labelframe':
            widget.configure(bg=self.theme['bg'], fg=self.theme['fg'], borderwidth=1, relief='solid')
        elif widget_type == 'Label':
            widget.configure(bg=self.theme['bg'], fg=self.theme['fg'])
        elif widget_type == 'Entry':
            widget.configure(
                bg=self.theme['surface'],
                fg=self.theme['fg'],
                insertbackground=self.theme['fg'],
                highlightbackground=self.theme['border'],
                highlightcolor=self.theme['primary']
            )
        elif widget_type == 'Checkbutton':
            widget.configure(
                bg=self.theme['bg'],
                fg=self.theme['fg'],
                selectcolor=self.theme['surface_alt'],
                activebackground=self.theme['bg'],
                activeforeground=self.theme['fg']
            )
        if widget.winfo_name() == '!frame6':
            widget.configure(bg=self.theme['border'], borderwidth=1, relief='solid')
        for child in widget.winfo_children():
            self._update_widget_colors(child)
        if isinstance(widget, ModernButton):
            all_button_colors = [c for theme in THEMES.values() for c in
                                 (theme['primary'], theme['success'], theme['danger'])]
            if widget.original_bg in all_button_colors:
                new_bg = None
                for key in ['primary', 'success', 'danger']:
                    if widget.original_bg in [THEMES[theme_name].get(key) for theme_name in THEMES]:
                        new_bg = self.theme[key]
                        break
                if new_bg:
                    widget.config(bg=new_bg, fg='#FFFFFF')
                    if widget.is_glowing:
                        widget.stop_glow()
                        widget.start_glow(new_bg, self._lighten_color(new_bg, 0.2))

    def _get_contrast_color(self, hex_color):
        return get_contrast_color(hex_color)

    def _setup_treeview_hover(self):
        style = ttk.Style()
        hover_text_color = self._get_contrast_color(self.theme['primary'])
        style.map('Custom.Treeview.Heading',
                  background=[('active', self.theme['primary']), ('!active', self.theme['surface_alt'])],
                  foreground=[('active', hover_text_color), ('!active', self.theme['fg'])])

    def _create_widgets(self):
        self.configure(bg=self.theme['bg'])
        top_frame = tk.Frame(self, bg=self.theme['bg'])
        top_frame.pack(fill="x", padx=20, pady=(20, 0))
        title_label = tk.Label(
            top_frame,
            text="DiskTider",
            font=('Segoe UI', 20, 'bold'),
            bg=self.theme['bg'],
            fg=self.theme['primary']
        )
        title_label.pack(side="left")
        subtitle_label = tk.Label(
            top_frame,
            text=" • Поиск и удаление дубликатов",
            font=('Segoe UI', 10),
            bg=self.theme['bg'],
            fg=self.theme['text_secondary']
        )
        subtitle_label.pack(side="left", pady=5)
        theme_icon = "🌙" if self.current_theme == 'light' else "🌞"

        # >>> ИЗМЕНЕНИЕ: Установка BG кнопки в цвет фона (bg)
        self.theme_button = tk.Button(
            top_frame,
            text=theme_icon,
            font=('Segoe UI Emoji', 16),
            bg=self.theme['bg'],  # <-- ИЗМЕНЕНО с self.theme['surface']
            fg=self.theme['fg'],
            relief=tk.FLAT,
            borderwidth=0,
            cursor='hand2',
            command=self._toggle_theme,
            width=3,
            height=1,
        )
        self.theme_button.pack(side="right", padx=(0, 4))

        def theme_btn_enter(e):
            self.theme_button.config(bg=self.theme['hover'])

        def theme_btn_leave(e):
            # >>> ИЗМЕНЕНИЕ: Возвращаем кнопку в цвет фона (bg)
            self.theme_button.config(bg=self.theme['bg'])

        self.theme_button.bind('<Enter>', theme_btn_enter)
        self.theme_button.bind('<Leave>', theme_btn_leave)

        separator1 = tk.Frame(self, height=1, bg=self.theme['border'])
        separator1.pack(fill="x", padx=20, pady=15)
        dir_section = tk.Frame(self, bg=self.theme['bg'])
        dir_section.pack(fill="x", padx=20, pady=10)
        dir_label = tk.Label(
            dir_section,
            text="📁 Папка для сканирования",
            font=('Segoe UI', 11, 'bold'),
            bg=self.theme['bg'],
            fg=self.theme['fg']
        )
        dir_label.pack(anchor="w", pady=(0, 5))
        dir_input_frame = tk.Frame(dir_section, bg=self.theme['bg'])
        dir_input_frame.pack(fill="x")
        self.dir_entry = tk.Entry(
            dir_input_frame,
            font=('Segoe UI', 10),
            bg=self.theme['surface'],
            fg=self.theme['fg'],
            insertbackground=self.theme['fg'],
            relief='flat',
            borderwidth=1,
            highlightthickness=1,
            highlightbackground=self.theme['border'],
            highlightcolor=self.theme['primary']
        )
        self.dir_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 10))
        browse_button = ModernButton(
            dir_input_frame,
            text="📂 Обзор",
            bg=self.theme['primary'],
            fg='#FFFFFF',
            command=self._browse_directory
        )
        browse_button.pack(side="left")
        options_section = tk.Frame(self, bg=self.theme['bg'])
        options_section.pack(fill="x", padx=20, pady=10)
        music_check = tk.Checkbutton(
            options_section,
            text="🎵 Только музыкальные файлы (.mp3, .flac, .wav и т.д.)",
            variable=self.music_var,
            font=('Segoe UI', 10),
            bg=self.theme['bg'],
            fg=self.theme['fg'],
            selectcolor=self.theme['surface_alt'],
            activebackground=self.theme['bg'],
            activeforeground=self.theme['fg'],
            borderwidth=0,
            highlightthickness=0,
            cursor='hand2'
        )
        music_check.pack(side="left", padx=(0, 20))
        recursive_check = tk.Checkbutton(
            options_section,
            text="🔄 Сканировать вложенные папки",
            variable=self.recursive_var,
            font=('Segoe UI', 10),
            bg=self.theme['bg'],
            fg=self.theme['fg'],
            selectcolor=self.theme['surface_alt'],
            activebackground=self.theme['bg'],
            activeforeground=self.theme['fg'],
            borderwidth=0,
            highlightthickness=0,
            cursor='hand2'
        )
        recursive_check.pack(side="left")
        self.scan_button = ModernButton(
            options_section,
            text="▶ Сканировать",
            bg=self.theme['success'],
            fg='#FFFFFF',
            command=self._start_scan_thread
        )
        self.scan_button.pack(side="right")
        separator2 = tk.Frame(self, height=1, bg=self.theme['border'])
        separator2.pack(fill="x", padx=20, pady=15)
        results_label = tk.Label(
            self,
            text="📊 Найденные дубликаты",
            font=('Segoe UI', 11, 'bold'),
            bg=self.theme['bg'],
            fg=self.theme['fg']
        )
        results_label.pack(anchor="w", padx=20, pady=(0, 5))
        self.tree_container = tk.Frame(self, bg=self.theme['border'], borderwidth=1, relief='solid')
        self.tree_container.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        scrollbar = ttk.Scrollbar(self.tree_container)
        scrollbar.pack(side="right", fill="y")

        # Добавлен новый столбец 'Risk'
        self.tree = ttk.Treeview(
            self.tree_container,
            columns=('Status', 'Risk', 'Size', 'Path'),
            show='tree headings',
            style="Custom.Treeview",
            yscrollcommand=scrollbar.set
        )
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.tree.yview)
        self.tree.heading('#0', text='Группа')
        self.tree.heading('Status', text='Действие')
        self.tree.heading('Risk', text='Риск')
        self.tree.heading('Size', text='Размер')
        self.tree.heading('Path', text='Путь')

        self.tree.column('#0', width=150, minwidth=100)
        self.tree.column('Status', width=100, minwidth=80, anchor='center')
        self.tree.column('Risk', width=70, minwidth=50, anchor='center')
        self.tree.column('Size', width=100, minwidth=80)
        self.tree.column('Path', width=450, minwidth=200)

        self.tree.bind('<Double-1>', self._toggle_status)
        self.tree.tag_configure('keep', foreground=self.theme['success'])
        self.tree.tag_configure('delete', foreground=self.theme['danger'])
        self.tree.tag_configure('group', font=('Segoe UI', 10, 'bold'))
        self._setup_treeview_hover()

        # Нижняя панель
        bottom_frame = tk.Frame(self, bg=self.theme['bg'])
        bottom_frame.pack(fill="x", padx=20, pady=(0, 20))

        # Обновление safety_label для необратимого удаления
        safety_text = "⚠️ УДАЛЕНИЕ БУДЕТ НЕОБРАТИМЫМ!"
        safety_color = self.theme['danger']

        safety_label = tk.Label(
            bottom_frame,
            text=safety_text,
            font=('Segoe UI', 9, 'bold'),
            bg=self.theme['bg'],
            fg=safety_color
        )
        safety_label.pack(side="left")

        self.delete_button = ModernButton(
            bottom_frame,
            text="🗑 Удалить выбранные",
            bg=self.theme['danger'],
            fg='#FFFFFF',
            font=('Segoe UI', 10, 'bold'),
            command=self._start_delete_thread,
            state=tk.DISABLED
        )
        self.delete_button.pack(side="right")
        status_frame = tk.Frame(self, bg=self.theme['surface'], height=30)
        status_frame.pack(fill="x", side="bottom")
        status_frame.pack_propagate(False)
        status_label = tk.Label(
            status_frame,
            textvariable=self.status_var,
            font=('Segoe UI', 9),
            bg=self.theme['surface'],
            fg=self.theme['text_secondary'],
            anchor="w"
        )
        status_label.pack(fill="both", padx=10, pady=5)
        self.status_glow = StatusGlow(
            self,
            status_frame,
            self.theme['surface'],
            self.theme['primary']
        )

    def save_settings(self):
        settings = {
            'music_filter': self.music_var.get(),
            'recursive_scan': self.recursive_var.get(),
            'last_directory': self.dir_entry.get()
        }
        with open('settings.json', 'w') as f:
            json.dump(settings, f)

    def load_settings(self):
        try:
            with open('settings.json', 'r') as f:
                settings = json.load(f)
                self.music_var.set(settings.get('music_filter', False))
                self.recursive_var.set(settings.get('recursive_scan', True))
                if settings.get('last_directory'):
                    self.dir_entry.delete(0, tk.END)
                    self.dir_entry.insert(0, settings.get('last_directory'))
        except FileNotFoundError:
            default_dir = os.path.expanduser('~')
            self.dir_entry.insert(0, default_dir)

    def _browse_directory(self):
        directory = filedialog.askdirectory(title="Выберите папку для сканирования")
        if directory:
            self.dir_entry.delete(0, tk.END)
            self.dir_entry.insert(0, directory)

    def _start_scan_thread(self):
        directory = self.dir_entry.get().strip()
        if not directory or not os.path.isdir(directory):
            messagebox.showerror("Ошибка", "Укажите корректную папку для сканирования")
            return
        if 'Chrome\\User Data' in directory.replace(os.sep, '\\') or 'AppData' in directory.replace(os.sep, '\\'):
            messagebox.showwarning(
                "Предупреждение",
                "Сканирование системных папок (например, AppData или Chrome\\User Data) может вызвать ошибки доступа. "
                "Закройте Google Chrome и выберите пользовательскую папку, например, 'Документы' или 'Музыка'."
            )
        if self.scan_button['state'] == tk.DISABLED:
            self.logger.info("GUI: Сканирование уже выполняется, игнорируем повторный запуск")
            return
        self.logger.info(f"GUI: Попытка запуска сканирования для директории: {directory}")
        self.status_var.set("🔍 Сканирование (Этап 1: по размеру)...")
        if self.status_glow:
            self.status_glow.start_glow()
        self.scan_button.config(text="Сканирование", state=tk.DISABLED)
        self.scan_button.start_glow(self.theme['success'], self._lighten_color(self.theme['success'], 0.2))
        self.delete_button.config(state=tk.DISABLED)
        self.tree.delete(*self.tree.get_children())
        extensions = MUSIC_EXTENSIONS if self.music_var.get() else None

        recursive = self.recursive_var.get()
        scan_thread = threading.Thread(target=self._run_scan, args=(directory, extensions, recursive), daemon=True)

        scan_thread.start()
        self.save_settings()

    def _run_scan(self, directory, extensions, recursive):
        self.logger.info(f"ПОТОК: Сканирование начато. Директория: {directory}, Рекурсивное: {recursive}")
        self.permission_errors = 0
        try:
            duplicates = find_duplicates(directory, extensions, recursive, gui=self)
            self.logger.info(f"ПОТОК: Сканирование завершено. Найдено групп: {len(duplicates)}")
            self.master.after(0, lambda: self._show_results(duplicates))
        except Exception as error:
            self.logger.error(f"ПОТОК: Критическая ошибка сканирования: {error}")
            self.master.after(0, lambda: self._show_error("Ошибка сканирования (Поток)", str(error)))

    def _show_results(self, duplicates):
        self.logger.info(f"GUI: Получены результаты. Групп дубликатов: {len(duplicates)}")
        self.tree.delete(*self.tree.get_children())
        self.duplicates_data = duplicates
        total_duplicates = 0
        total_space = 0
        if duplicates:
            self.logger.debug("GUI: Заполнение Treeview дубликатами")

            # СОРТИРОВКА ГРУПП ПО РАЗМЕРУ ФАЙЛА-ОРИГИНАЛА (ПО УБЫВАНИЮ)
            processed_groups = []
            for file_hash, files in duplicates.items():
                # 1. Сортируем файлы в группе по приоритету, чтобы определить "оригинал"
                files_sorted_by_priority = sorted(files, key=lambda x: get_file_priority(x['name']))

                # 2. Размер файла, который будет сохранен (самый высокий приоритет)
                keep_size = files_sorted_by_priority[0]['size'] if files_sorted_by_priority else 0

                # Сохраняем данные группы и ключ сортировки
                processed_groups.append((file_hash, files, keep_size))

            # 3. Сортируем группы по размеру (keep_size) по убыванию (самые большие первыми)
            processed_groups.sort(key=lambda x: x[2], reverse=True)

            # --- Начало итерации по ОТСОРТИРОВАННЫМ группам ---
            for i, (file_hash, files, keep_size) in enumerate(processed_groups, 1):
                # На этом этапе, files - это список файлов, который нужно отсортировать для отображения
                files_sorted = sorted(files, key=lambda x: get_file_priority(x['name']))

                group_size = format_size(files_sorted[0]['size'])
                wasted_space = files_sorted[0]['size'] * (len(files_sorted) - 1)
                total_space += wasted_space
                group_id = self.tree.insert(
                    '',
                    tk.END,
                    text=f"Группа {i}",
                    values=('', '', group_size, f"{len(files_sorted)} файлов • {format_size(wasted_space)} лишнего"),
                    tags=('group',),
                    open=False
                )
                for j, file_info in enumerate(files_sorted):
                    status = "Сохранить" if j == 0 else "Удалить"
                    tag_status = 'keep' if j == 0 else 'delete'

                    # Проверка и маркировка риска
                    risk_status = self._check_file_risk(file_info['path'])
                    risk_indicator = "🚨 РИСК" if risk_status == 'RISK' else "🟢 ОК"
                    tag_risk = 'risk' if risk_status == 'RISK' else ''

                    # tags: (tag_risk, tag_status, file_hash, size_bytes)
                    final_tags = (tag_risk, tag_status, file_hash, str(file_info['size']))

                    if j > 0:
                        total_duplicates += 1

                    self.tree.insert(
                        group_id,
                        tk.END,
                        text='',
                        values=(status, risk_indicator, format_size(file_info['size']), file_info['path']),
                        tags=final_tags
                    )
            # --- Конец итерации ---

        if total_duplicates > 0:
            status_text = f"✓ Найдено: {len(duplicates)} групп • {total_duplicates} дубликатов • {format_size(total_space)} можно освободить"
            if self.permission_errors > 0:
                status_text += f"\n⚠ {self.permission_errors} файлов пропущено из-за ограничений доступа"
            self.status_var.set(status_text)
            self.delete_button.config(state=tk.NORMAL)
        else:
            status_text = "✨ Дубликаты не найдены. Все чисто."
            if self.permission_errors > 0:
                status_text += f"\n⚠ {self.permission_errors} файлов пропущено из-за ограничений доступа"
            self.status_var.set(status_text)
            self.delete_button.config(state=tk.DISABLED)
            messagebox.showinfo("Результат сканирования",
                                "Дубликаты не найдены. Проверьте другую директорию или настройки фильтра.")
        if self.status_glow:
            self.status_glow.stop_glow()
        self.scan_button.stop_glow()
        self.scan_button.config(text="▶ Сканировать", state=tk.NORMAL)
        self.logger.debug("GUI: Обновление завершено")

    def _show_error(self, title, message):
        if self.status_glow:
            self.status_glow.stop_glow()
        self.scan_button.stop_glow()
        self.scan_button.config(text="▶ Сканировать", state=tk.NORMAL)
        messagebox.showerror(title, message)
        self.status_var.set("✗ Ошибка при выполнении операции")

    def _toggle_status(self, event):
        item_id = self.tree.identify_row(event.y)
        if not item_id or not self.tree.parent(item_id):
            return
        parent_id = self.tree.parent(item_id)
        children = self.tree.get_children(parent_id)
        if item_id == children[0]:
            messagebox.showinfo("Информация", "Первый файл в группе помечен как оригинал и не может быть удален")
            return
        current_status = self.tree.item(item_id, 'values')[0]
        new_status = "Удалить" if current_status == "Сохранить" else "Сохранить"
        new_tag = 'delete' if new_status == "Удалить" else 'keep'
        values = list(self.tree.item(item_id, 'values'))
        values[0] = new_status
        tags = self.tree.item(item_id, 'tags')

        updated_tags = list(tags)
        updated_tags[1] = new_tag

        self.tree.item(item_id, values=values, tags=updated_tags)

    def _start_delete_thread(self):
        files_to_delete = []
        for group_id in self.tree.get_children():
            for item_id in self.tree.get_children(group_id):
                status, risk_indicator, size_str_formatted, path = self.tree.item(item_id, 'values')
                tags = self.tree.item(item_id, 'tags')
                if status == "Удалить":
                    try:
                        # Размер хранится в tags[3]
                        size_bytes = int(tags[3])
                    except (IndexError, ValueError):
                        self.logger.error(f"Ошибка извлечения размера для {path}. Пропуск.")
                        continue
                    files_to_delete.append({
                        'path': path,
                        'name': os.path.basename(path),
                        'size': size_bytes
                    })
        if not files_to_delete:
            messagebox.showinfo("Информация", "Нет файлов для удаления")
            return

        total_size = sum(f['size'] for f in files_to_delete)

        # Текст подтверждения только для необратимого удаления
        confirm_text = (
            f"Удалить {len(files_to_delete)} файлов?\n"
            f"Будет освобождено: {format_size(total_size)}\n\n"
            f"⚠️ УДАЛЕНИЕ БУДЕТ НЕОБРАТИМЫМ!"
        )

        if not messagebox.askyesno("Подтверждение", confirm_text):
            return

        self.status_var.set("🗑 Удаление файлов...")
        self.delete_button.config(state=tk.DISABLED)
        self.scan_button.config(state=tk.DISABLED)
        delete_thread = threading.Thread(target=self._run_delete, args=(files_to_delete,), daemon=True)
        delete_thread.start()

    def _run_delete(self, files_to_delete):
        try:
            deleted_count, freed_space_str = delete_files_by_list(files_to_delete)
            self.master.after(0, lambda: self._show_delete_results(deleted_count, freed_space_str))
        except Exception as e:
            self.master.after(0, lambda: self._show_error("Ошибка удаления", str(e)))
            self.logger.error(f"Ошибка удаления: {e}")

    def _show_delete_results(self, deleted_count, freed_space_str):
        self.status_var.set(f"✓ Удалено: {deleted_count} файлов • Освобождено: {freed_space_str}")
        messagebox.showinfo("Готово", f"Успешно удалено: {deleted_count} файлов\nОсвобождено: {freed_space_str}")
        self.tree.delete(*self.tree.get_children())
        self.duplicates_data = {}
        self.delete_button.config(state=tk.DISABLED)
        self.scan_button.config(state=tk.NORMAL)


class StatusGlow:
    def __init__(self, app_gui, status_frame, start_color, end_color):
        self.app_gui = app_gui
        self.master = app_gui.master
        self.frame = status_frame
        self.start_color = start_color
        self.end_color = end_color
        self.is_glowing = False
        self.counter = 0

    def start_glow(self):
        if not self.is_glowing:
            self.is_glowing = True
            self._animate_glow()

    def stop_glow(self):
        self.is_glowing = False

    def _animate_glow(self):
        if not self.is_glowing:
            current_theme = THEMES[self.app_gui.current_theme]
            self.frame.config(bg=current_theme['surface'])
            for child in self.frame.winfo_children():
                child.config(bg=current_theme['surface'])
            return
        self.counter += 1
        intensity = abs(10 - (self.counter % 20)) / 10
        color = self._interpolate_color(self.start_color, self.end_color, intensity)
        self.frame.config(bg=color)
        for child in self.frame.winfo_children():
            child.config(bg=color)
        self.frame.after(100, self._animate_glow)

    def _interpolate_color(self, hex1, hex2, factor):
        try:
            r1, g1, b1 = int(hex1[1:3], 16), int(hex1[3:5], 16), int(hex1[5:7], 16)
            r2, g2, b2 = int(hex2[1:3], 16), int(hex2[3:5], 16), int(hex2[5:7], 16)
            r = int(r1 + (r2 - r1) * factor)
            g = int(g1 + (g2 - g1) * factor)
            b = int(b1 + (b2 - b1) * factor)
            return f'#{r:02x}{g:02x}{b:02x}'
        except:
            return hex1