# intro.py
import tkinter as tk
from tkinter import ttk
from gui_app import DiskTiderGUI, THEMES, ModernButton
import math


class AnimatedButton(tk.Button):
    """Кнопка с анимацией при наведении"""

    def __init__(self, master, **kwargs):
        self.original_bg = kwargs.get('bg', '#007ACC')
        super().__init__(
            master,
            relief=tk.FLAT,
            borderwidth=0,
            cursor='hand2',
            font=('Segoe UI', 12, 'bold'),
            **kwargs
        )
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)
        self._hover_animation_id = None

    def _on_enter(self, e):
        if self['state'] != 'disabled':
            self['bg'] = self._lighten_color(self.original_bg, 0.15)

    def _on_leave(self, e):
        if self['state'] != 'disabled':
            self['bg'] = self.original_bg

    def _lighten_color(self, hex_color, factor):
        """Осветляет цвет"""
        r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
        r = min(255, int(r + (255 - r) * factor))
        g = min(255, int(g + (255 - g) * factor))
        b = min(255, int(b + (255 - b) * factor))
        return f'#{r:02x}{g:02x}{b:02x}'


class FeatureCard(tk.Frame):
    """Карточка фичи с эффектом при наведении (БЕЗ курсора кнопки)"""

    def __init__(self, master, icon, title, description, theme, **kwargs):
        super().__init__(
            master,
            bg=theme['surface'],
            relief=tk.FLAT,
            **kwargs
        )
        self.theme = theme
        self.original_bg = theme['surface']
        self.hover_bg = self._lighten_color(theme['surface'], 0.1)

        # Внутренний padding
        content_frame = tk.Frame(self, bg=theme['surface'])
        content_frame.pack(fill='both', expand=True, padx=20, pady=15)

        # Иконка
        icon_label = tk.Label(
            content_frame,
            text=icon,
            font=('Segoe UI', 32),
            bg=theme['surface'],
            fg=theme['primary'],
            cursor='arrow'
        )
        icon_label.pack(side='left', padx=(0, 15))

        # Текст
        text_frame = tk.Frame(content_frame, bg=theme['surface'])
        text_frame.pack(side='left', fill='both', expand=True)

        title_label = tk.Label(
            text_frame,
            text=title,
            font=('Segoe UI', 12, 'bold'),
            bg=theme['surface'],
            fg=theme['fg'],
            anchor='w',
            cursor='arrow'
        )
        title_label.pack(fill='x', pady=(0, 3))

        desc_label = tk.Label(
            text_frame,
            text=description,
            font=('Segoe UI', 10),
            bg=theme['surface'],
            fg=theme['text_secondary'],
            anchor='w',
            wraplength=300,
            justify='left',
            cursor='arrow'
        )
        desc_label.pack(fill='x')

        # Устанавливаем обычный курсор для самого фрейма
        self.configure(cursor='arrow')

        # Bind события для hover эффекта
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)
        for widget in self.winfo_children():
            self._bind_recursive(widget)

    def _bind_recursive(self, widget):
        """Рекурсивно привязывает события к дочерним виджетам"""
        widget.bind('<Enter>', self._on_enter)
        widget.bind('<Leave>', self._on_leave)
        try:
            widget.configure(cursor='arrow')
        except:
            pass
        for child in widget.winfo_children():
            self._bind_recursive(child)

    def _on_enter(self, e):
        self._update_colors(self.hover_bg)

    def _on_leave(self, e):
        self._update_colors(self.original_bg)

    def _update_colors(self, bg):
        """Обновляет цвет фона для всех виджетов в карточке"""
        self.configure(bg=bg)
        for widget in self.winfo_children():
            self._update_widget_bg(widget, bg)

    def _update_widget_bg(self, widget, bg):
        """Рекурсивно обновляет фон виджетов"""
        try:
            widget.configure(bg=bg)
        except:
            pass
        for child in widget.winfo_children():
            self._update_widget_bg(child, bg)

    def _lighten_color(self, hex_color, factor):
        """Осветляет цвет для dark темы"""
        r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
        r = min(255, int(r + (255 - r) * factor))
        g = min(255, int(g + (255 - g) * factor))
        b = min(255, int(b + (255 - b) * factor))
        return f'#{r:02x}{g:02x}{b:02x}'


class IntroScreen(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=THEMES['dark']['bg'])
        self.master = master
        self.theme = THEMES['dark']
        self.alpha = 0.0

        self.pack(expand=True, fill="both")
        self._create_widgets()
        self._fade_in()

        self.master.bind('<Configure>', self._on_window_resize)

    def _on_window_resize(self, event):
        """Обрабатывает изменение размера окна для центрирования"""
        # Обновляем ширину окна для canvas
        if hasattr(self, 'canvas') and hasattr(self, 'scrollable_frame'):
            self.canvas.itemconfig(self.canvas_window, width=self.canvas.winfo_width())

    def _create_widgets(self):
        """Создает все виджеты интро экрана"""
        # Canvas с прокруткой
        self.canvas = tk.Canvas(self, bg=self.theme['bg'], highlightthickness=0)
        scrollbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)

        self.scrollable_frame = tk.Frame(self.canvas, bg=self.theme['bg'])

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        # КЛЮЧЕВОЕ ИЗМЕНЕНИЕ: создаём окно с anchor="center" и сохраняем ID
        self.canvas_window = self.canvas.create_window(
            (0, 0),
            window=self.scrollable_frame,
            anchor="n"
        )

        self.canvas.configure(yscrollcommand=scrollbar.set)

        # Упаковываем
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Привязываем обновление ширины окна при изменении размера canvas
        self.canvas.bind('<Configure>', self._on_canvas_configure)

        # Главный контейнер - ЦЕНТРИРУЕМ его
        main_container = tk.Frame(self.scrollable_frame, bg=self.theme['bg'])
        main_container.pack(expand=True, pady=40)

        # --- Заголовок ---
        header_frame = tk.Frame(main_container, bg=self.theme['bg'])
        header_frame.pack(pady=(0, 10))

        logo_label = tk.Label(
            header_frame,
            text="🎵",
            font=('Segoe UI', 48),
            bg=self.theme['bg']
        )
        logo_label.pack(pady=(0, 5))

        title_label = tk.Label(
            header_frame,
            text="DiskTider",
            font=('Segoe UI', 42, 'bold'),
            bg=self.theme['bg'],
            fg=self.theme['primary']
        )
        title_label.pack()

        subtitle_label = tk.Label(
            header_frame,
            text="Умный поиск и удаление дубликатов файлов",
            font=('Segoe UI', 13),
            bg=self.theme['bg'],
            fg=self.theme['text_secondary']
        )
        subtitle_label.pack(pady=(5, 0))

        # Разделитель
        separator = tk.Frame(
            main_container,
            height=2,
            bg=self.theme['border']
        )
        separator.pack(fill='x', pady=20, padx=50)

        # --- Карточки ---
        features_frame = tk.Frame(main_container, bg=self.theme['bg'])
        features_frame.pack(pady=(0, 25))

        features = [
            {
                'icon': '🛡️',
                'title': 'Безопасность превыше всего',
                'description': 'Полный контроль над удалением. Предпросмотр перед действием.'
            },
            {
                'icon': '✨',
                'title': 'Умный выбор оригинала',
                'description': 'Автоматически сохраняет файлы без приписок (1), (2), "копия".'
            },
            {
                'icon': '⚡',
                'title': 'Быстрое сканирование',
                'description': 'Оптимизированный алгоритм: сначала по размеру, потом по хешу.'
            }
        ]

        for feature in features:
            card = FeatureCard(
                features_frame,
                icon=feature['icon'],
                title=feature['title'],
                description=feature['description'],
                theme=self.theme
            )
            card.pack(fill='x', pady=5)

        # --- Нижняя панель ---
        bottom_frame = tk.Frame(main_container, bg=self.theme['bg'])
        bottom_frame.pack(pady=(15, 0))

        checkbox_frame = tk.Frame(bottom_frame, bg=self.theme['bg'])
        checkbox_frame.pack(pady=(0, 15))

        self.dont_show_again_var = tk.BooleanVar()
        checkbox = tk.Checkbutton(
            checkbox_frame,
            text="Больше не показывать это окно",
            variable=self.dont_show_again_var,
            font=('Segoe UI', 10),
            bg=self.theme['bg'],
            fg=self.theme['text_secondary'],
            selectcolor=self.theme['surface'],
            activebackground=self.theme['bg'],
            borderwidth=0,
            highlightthickness=0,
            cursor='hand2'
        )
        checkbox.pack()

        button_frame = tk.Frame(bottom_frame, bg=self.theme['bg'])
        button_frame.pack()

        self.start_button = AnimatedButton(
            button_frame,
            text="Начать работу  →",
            bg=self.theme['success'],
            fg='#FFFFFF',
            command=self.open_main_app,
            padx=40,
            pady=15
        )
        self.start_button.pack()

        hint_label = tk.Label(
            bottom_frame,
            text="Нажмите Enter для быстрого старта",
            font=('Segoe UI', 9, 'italic'),
            bg=self.theme['bg'],
            fg=self.theme['text_secondary']
        )
        hint_label.pack(pady=(10, 0))

        self.master.bind('<Return>', lambda e: self.open_main_app())

        # Прокрутка колесиком
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)

    def _on_canvas_configure(self, event):
        """Центрирует содержимое при изменении размера canvas"""
        # Получаем ширину canvas
        canvas_width = event.width
        # Обновляем ширину окна, чтобы оно занимало всю ширину canvas
        self.canvas.itemconfig(self.canvas_window, width=canvas_width)

    def _fade_in(self):
        """Плавное появление окна"""
        if self.alpha < 1.0:
            self.alpha += 0.05
            try:
                self.master.attributes('-alpha', self.alpha)
            except:
                pass
            self.after(20, self._fade_in)

    def open_main_app(self):
        """Открывает основное приложение"""
        if self.dont_show_again_var.get():
            # TODO: Сохранить в конфиг
            pass

        self._fade_out()

    def _fade_out(self):
        """Плавное исчезновение перед переходом"""
        if self.alpha > 0:
            self.alpha -= 0.1
            try:
                self.master.attributes('-alpha', self.alpha)
            except:
                pass
            self.after(20, self._fade_out)
        else:
            self._switch_to_main()

    def _switch_to_main(self):
        """Переключается на основное приложение"""

        # Отменяем привязку изменения размера окна
        self.master.unbind('<Configure>')

        # Отменяем привязку колесика мыши
        self.canvas.unbind_all("<MouseWheel>")

        self.destroy()

        width, height = 1000, 700
        self.master.title("DiskTider - Поиск и удаление дубликатов")
        self._center_window(width, height)
        self.master.minsize(800, 600)

        try:
            self.master.attributes('-alpha', 1.0)
        except:
            pass

        DiskTiderGUI(self.master)

    def _center_window(self, width, height):
        """Центрирует окно на экране"""
        self.master.geometry(f"{width}x{height}")
        self.master.update_idletasks()
        x = (self.master.winfo_screenwidth() // 2) - (width // 2)
        y = (self.master.winfo_screenheight() // 2) - (height // 2)
        self.master.geometry(f'+{x}+{y}')


def main():
    root = tk.Tk()
    root.title("DiskTider - Добро пожаловать")
    root.resizable(True, True)
    root.minsize(600, 500)

    try:
        root.attributes('-alpha', 0.0)
    except:
        pass

    app = IntroScreen(root)
    app._center_window(700, 600)

    root.mainloop()


if __name__ == '__main__':
    main()