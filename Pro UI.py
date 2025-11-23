import base64
import io
import os
import threading
from socket import socket, AF_INET, SOCK_STREAM

from customtkinter import *
from tkinter import filedialog
from PIL import Image, ImageDraw, ImageFont


class MainWindow(CTk):
    def __init__(self):
        super().__init__()

        self.geometry('800x600')
        self.title("Logi Talk Pro")
        self.minsize(300, 250)

        # --- Атрибути ---
        self.username = ""
        self.user_avatar = None  # Головний аватар користувача (60x60)
        self.user_avatar_chat = None  # Аватар користувача для чату (40x40)
        self.system_avatar_chat = None  # Аватар системи для чату (40x40)
        self.user_avatars_cache = {}  # Кеш аватарок для інших користувачів
        self.menu_width = 30  # Початкова ширина меню для анімації

        # Завантажуємо аватари при старті
        self.load_main_avatar()
        self.load_chat_avatars()

        # --- Архітектура UI ---
        # Використовуємо .place() для ізоляції анімації меню
        self.menu_frame = CTkFrame(self, width=self.menu_width)
        self.menu_frame.place(x=0, y=0, relheight=1)
        self.menu_frame.pack_propagate(False)

        self.main_frame = CTkFrame(self, fg_color="transparent")
        self.main_frame.place(x=self.menu_width, y=0, relheight=1)

        # Прив'язка до зміни розміру вікна
        self.bind("<Configure>", self.on_resize)

        # 3. Панель вводу (знизу в main_frame)
        self.input_frame = CTkFrame(self.main_frame, height=45, fg_color="transparent")
        self.input_frame.pack(side='bottom', fill='x', padx=5, pady=5)

        # 4. Поле чату (зверху в main_frame, займає весь простір)
        self.chat_field = CTkScrollableFrame(self.main_frame)
        self.chat_field.pack(side='top', expand=True, fill='both', padx=5, pady=(5, 0))
        # --- КІНЕЦЬ СТРУКТУРИ ---

        # Віджети вводу тепер належать input_frame
        self.message_entry = CTkEntry(self.input_frame, placeholder_text='Введіть повідомлення:')
        self.send_button = CTkButton(self.input_frame, text='>', width=50, command=self.send_message)
        self.open_img_button = CTkButton(self.input_frame, text='📂', width=50, command=self.open_image)

        # Розміщуємо віджети в input_frame
        self.send_button.pack(side='right', padx=(0, 0), pady=0, fill='y')
        self.open_img_button.pack(side='right', padx=5, pady=0, fill='y')
        self.message_entry.pack(expand=True, fill='both', pady=0)

        # Меню
        self.is_show_menu = False
        self.is_animating = False  # Прапор для блокування анімації
        self.btn = CTkButton(self, text='▶️', command=self.toggle_show_menu, width=30, height=30)
        self.btn.place(x=0, y=0)
        self.btn.lift()

        # Додаємо стартове повідомлення
        self.add_message("Ласкаво просимо до чату!", author="SYSTEM")

        # Підключення до сервера
        try:
            self.sock = socket(AF_INET, SOCK_STREAM)
            self.sock.connect(('localhost', 8080))
            hello = f"TEXT@{self.username}@[SYSTEM] {self.username} приєднався(лась) до чату!\n"
            self.sock.send(hello.encode('utf-8'))
            threading.Thread(target=self.recv_message, daemon=True).start()
        except Exception as e:
            # Поки що просто виведемо помилку, щоб не заважати UI
            print(f"Не вдалося підключитися до сервера: {e}")

    def load_main_avatar(self):
        """Завантажує головний аватар користувача user-avatar.png (60x60) для меню."""
        try:
            image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user-avatar.png")
            self.user_avatar = self.create_circular_avatar(image_path, (60, 60))
        except Exception as e:
            print(f"Помилка завантаження головного аватара: {e}")
            # Створюємо дефолтний, якщо не вдалося завантажити
            self.user_avatar = self.create_circular_avatar(None, (60, 60), "U")

    def load_chat_avatars(self):
        """Завантажує аватари користувача та системи для чату (40x40)."""
        try:
            user_image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user-avatar.png")
            self.user_avatar_chat = self.create_circular_avatar(user_image_path, (40, 40))
        except Exception as e:
            print(f"Помилка завантаження аватара користувача для чату: {e}")
            self.user_avatar_chat = self.create_circular_avatar(None, (40, 40), "U")

        try:
            system_image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "system-avatar.png")
            self.system_avatar_chat = self.create_circular_avatar(system_image_path, (40, 40))
        except Exception as e:
            print(f"Помилка завантаження аватара системи для чату: {e}")
            self.system_avatar_chat = self.create_circular_avatar(None, (40, 40), "S")

    def create_circular_avatar(self, image_path, size, initial='?'):
        """Створює круглий аватар із зображення або ініціалів."""
        if image_path and os.path.exists(image_path):
            img = Image.open(image_path).convert("RGBA")
            img = img.resize((size[0], size[1]), Image.Resampling.LANCZOS)
        else:
            # Створюємо зображення з ініціалів, якщо шлях недійсний або відсутній
            img = Image.new("RGBA", size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.ellipse((0, 0, size[0], size[1]), fill=(0, 0, 0, 255))  # Заповнюємо фон
            try:
                # Спробуємо завантажити Arial, але якщо не вийде - використаємо дефолтний шрифт
                font = ImageFont.truetype("arial.ttf", int(size[1] * 0.6))
            except IOError:
                font = ImageFont.load_default()
            draw.text((size[0] // 2, size[1] // 2), initial, anchor="mm", fill=(255, 255, 255, 255), font=font)

        mask = Image.new('L', (size[0], size[1]), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, size[0], size[1]), fill=255)

        circular_img = Image.new("RGBA", (size[0], size[1]), (0, 0, 0, 0))
        circular_img.paste(img, (0, 0), mask)

        return CTkImage(light_image=circular_img, dark_image=circular_img, size=size)

    def toggle_show_menu(self):
        # Блокуємо повторні кліки під час анімації
        if self.is_animating:
            return

        self.is_animating = True  # Блокуємо на час анімації

        if self.is_show_menu:
            # --- ЛОГІКА ЗАКРИТТЯ ---
            self.is_show_menu = False
            self.btn.configure(text='▶️')
            # 1. Миттєво видаляємо віджети
            for widget in self.menu_frame.winfo_children():
                widget.destroy()
            # 2. Запускаємо анімацію згортання ПОРОЖНЬОЇ панелі
            self.animate_close_menu()
        else:
            # --- ЛОГІКА ВІДКРИТТЯ ---
            self.is_show_menu = True
            self.btn.configure(text='◀️')
            # Просто запускаємо анімацію розгортання
            self.animate_open_menu()

    def on_resize(self, event=None):
        """Оновлює ширину основного фрейму при зміні розміру вікна."""
        # Ігноруємо початкові/недійсні події, щоб уникнути помилок
        if not hasattr(self, 'menu_width') or self.winfo_width() <= 1:
            return
        main_width = self.winfo_width() - self.menu_width
        self.main_frame.place_configure(width=main_width)

    def animate_open_menu(self):
        """Анімовано відкриває меню до цільової ширини 200px."""
        target_width = 200
        if self.menu_width < target_width:
            self.menu_width = min(self.menu_width + 20, target_width)
            self.menu_frame.place_configure(width=self.menu_width)
            # Оновлюємо позицію та розмір головного фрейму
            main_width = self.winfo_width() - self.menu_width
            self.main_frame.place_configure(x=self.menu_width, width=main_width)
            self.after(10, self.animate_open_menu)
        else:
            self.menu_width = target_width
            self.menu_frame.place_configure(width=self.menu_width)
            self.on_resize()  # Фінальне оновлення
            self.is_animating = False  # Розблоковуємо після завершення
            # Створюємо віджети ТІЛЬКИ ПІСЛЯ завершення анімації
            self.create_menu_widgets()

    def animate_close_menu(self):
        """Анімовано закриває меню до цільової ширини 30px."""
        target_width = 30
        if self.menu_width > target_width:
            self.menu_width = max(self.menu_width - 20, target_width)
            self.menu_frame.place_configure(width=self.menu_width)
            # Оновлюємо позицію та розмір головного фрейму
            main_width = self.winfo_width() - self.menu_width
            self.main_frame.place_configure(x=self.menu_width, width=main_width)
            self.after(10, self.animate_close_menu)
        else:
            self.menu_width = target_width
            self.menu_frame.place_configure(width=self.menu_width)
            self.on_resize()  # Фінальне оновлення
            self.is_animating = False  # Розблоковуємо після завершення

    def create_menu_widgets(self):
        """Створює віджети для меню, використовуючи .place() для стабільності."""
        if self.user_avatar:
            # Цей віджет не зберігається в self, бо він не потрібен для логіки
            avatar_label = CTkLabel(self.menu_frame, text="", image=self.user_avatar)
            avatar_label.place(relx=0.5, y=50, anchor="center")

        self.label = CTkLabel(self.menu_frame, text='Імʼя')
        self.label.place(relx=0.5, y=95, anchor="center")

        self.entry = CTkEntry(self.menu_frame, placeholder_text="Ваш нік...")
        self.entry.place(relx=0.5, y=130, relwidth=0.8, anchor="center")

        self.save_button = CTkButton(self.menu_frame, text="Зберегти", command=self.save_name)
        self.save_button.place(relx=0.5, y=175, relwidth=0.8, anchor="center")

    def save_name(self):
        new_name = self.entry.get().strip()
        if new_name:
            self.username = new_name
            self.add_message(f"Нік змінено на: {self.username}", author="SYSTEM")

    def get_chat_avatar(self, author):
        """Повертає аватар (40x40) для автора в чаті."""
        # 1. Аватар поточного користувача
        if author == self.username:
            return self.user_avatar_chat

        # 2. Аватар системи
        if author == "SYSTEM":
            return self.system_avatar_chat

        # 3. Аватар іншого користувача (з кешу або новий)
        if author not in self.user_avatars_cache:
            initial = author[0].upper() if author else '?'
            self.user_avatars_cache[author] = self.create_circular_avatar(None, (40, 40), initial)

        return self.user_avatars_cache[author]

    def add_message(self, message, img=None, author=None):
        """Додає повідомлення у чат з аватаром, іменем та текстом/зображенням."""
        if author is None:
            author = self.username

        avatar_img = self.get_chat_avatar(author)

        # Головний контейнер (для вирівнювання)
        align_frame = CTkFrame(self.chat_field, fg_color="transparent")

        # Контейнер для повідомлення (аватар + текст)
        msg_container = CTkFrame(align_frame, fg_color="transparent")

        avatar_label = CTkLabel(msg_container, text="", image=avatar_img)
        text_container = CTkFrame(msg_container, fg_color='#4a4a4a', corner_radius=10)

        # Вирівнювання
        if author == self.username:  # Якщо автор - поточного користувача
            align_frame.pack(fill='x', padx=10, pady=5)
            msg_container.pack(side='right')
            avatar_label.pack(side='right', padx=(10, 0))
            text_container.pack(side='right')
        else:  # Інші автори
            align_frame.pack(fill='x', padx=10, pady=5)
            msg_container.pack(side='left')
            avatar_label.pack(side='left', padx=(0, 10))
            text_container.pack(side='left')

        # Вміст повідомлення
        if author == "SYSTEM":
            author_label = CTkLabel(text_container, text="System", text_color='gray70', font=('Arial', 12, 'bold'))
            author_label.pack(anchor='w', padx=10, pady=(5, 0))
        else:
            author_label = CTkLabel(text_container, text=author, text_color='cyan', font=('Arial', 12, 'bold'))
            author_label.pack(anchor='w', padx=10, pady=(5, 0))

        msg_label = CTkLabel(text_container, text=message, text_color='white', justify='left', image=img,
                             compound='top', wraplength=400)
        msg_label.pack(anchor='w', padx=10, pady=5)

    def send_message(self):
        message = self.message_entry.get()
        if message:
            data = f"TEXT@{self.username}@{message}\n"
            try:
                self.sock.sendall(data.encode())
                self.add_message(message, author=self.username)
            except Exception as e:
                print(f"Помилка відправки: {e}")
                self.add_message("Помилка відправки", author="SYSTEM")
        self.message_entry.delete(0, END)

    def recv_message(self):
        buffer = ""
        while True:
            try:
                chunk = self.sock.recv(4096)
                if not chunk: break
                buffer += chunk.decode('utf-8', errors='ignore')
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    self.handle_line(line.strip())
            except:
                break
        self.sock.close()

    def handle_line(self, line):
        if not line: return
        parts = line.split("@", 3)
        msg_type = parts[0]
        if msg_type == "TEXT":
            author, message = parts[1], parts[2]
            if author != self.username:
                self.add_message(message, author=author)
        elif msg_type == "IMAGE":
            author, filename, b64_img = parts[1], parts[2], parts[3]
            try:
                img_data = base64.b64decode(b64_img)
                pil_img = Image.open(io.BytesIO(img_data))
                ctk_img = CTkImage(pil_img, size=(200, 200))
                if author != self.username:
                    self.add_message(f"Надіслав(ла) зображення: {filename}", img=ctk_img, author=author)
            except Exception as e:
                self.add_message(f"Помилка зображення: {e}", author="SYSTEM")
        else:
            self.add_message(line, author="SYSTEM")

    def open_image(self):
        file_name = filedialog.askopenfilename()
        if not file_name: return
        try:
            with open(file_name, "rb") as f:
                raw = f.read()
            b64_data = base64.b64encode(raw).decode()
            short_name = os.path.basename(file_name)
            data = f"IMAGE@{self.username}@{short_name}@{b64_data}\n"
            self.sock.sendall(data.encode())
            self.add_message('Я надіслав(ла) зображення:', CTkImage(Image.open(file_name), size=(200, 200)),
                             author=self.username)
        except Exception as e:
            self.add_message(f"Помилка надсилання: {e}", author="SYSTEM")


if __name__ == "__main__":
    win = MainWindow()
    win.mainloop()
