# color_utils.py

def lighten_color(hex_color, factor):
    """
    Осветляет HEX-цвет. Если фактор положительный, осветляет.
    Если передан не HEX-цвет (например, имя цвета Tkinter), возвращает исходный цвет.
    """
    try:
        if not isinstance(hex_color, str) or not hex_color.startswith('#') or len(hex_color) != 7:
            return hex_color

        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)

        r = min(255, int(r + (255 - r) * factor))
        g = min(255, int(g + (255 - g) * factor))
        b = min(255, int(b + (255 - b) * factor))

        return f'#{r:02x}{g:02x}{b:02x}'
    except ValueError:
        return hex_color


def get_contrast_color(hex_color):
    """
    Автоматически определяет контрастный цвет (белый или чёрный) для заданного фона.
    """
    try:
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
    except (ValueError, TypeError):
        return '#000000'

    # Расчет яркости (Luminance) по формуле W3C
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return '#000000' if luminance > 0.5 else '#FFFFFF'