from customtkinter import * 
import threading
from socket import *
from PIL import Image
import base64
import io

class MainWindow(CTk):
    def __init__(self):
        super().__init__()
        self.geometry('400x400')
        self.minsize(350, 300)
        self.username = "Користувач"

        # Підключення до сервера
        self.client_socket = socket(AF_INET, SOCK_STREAM)
        try:
            self.client_socket.connect(("127.0.0.1", 8080))
        except Exception as e:
            print("Помилка підключення до сервера:", e)

        threading.Thread(target=self.recv_messages, daemon=True).start()


        # 1. Нижня панель для введення повідомлення та кнопки (фіксована висота 50 пікселів знизу)
        self.bottom_frame = CTkFrame(self, fg_color="transparent")
        self.bottom_frame.pack(side="bottom", fill="x", padx=(35, 10), pady=10)

        self.btn_send = CTkButton(self.bottom_frame, text='⏏️', width=45, height=35, 
                                  font=CTkFont(size=18, weight="bold"), command=self.send_message)
        self.btn_send.pack(side="right", padx=(5, 0))

        self.btn_image = CTkButton(self.bottom_frame, text='🖼️', width=40,height=35,
                                   command=self.send_image)
        self.btn_image.pack(side="right", padx=(5,0))

        self.entry = CTkEntry(self.bottom_frame, placeholder_text="введіть повідомлення", height=35)
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", lambda event: self.send_message())

        # 2. Центральна зона для чату (займає весь решту простору зверху)
        self.chat = CTkScrollableFrame(self)
        self.chat.pack(side="top", fill="both", expand=True, padx=(35, 10), pady=(10, 0))
        

        # 3. Бокове меню (розгортається поверх усього завдяки .place())
        self.menu_frame = CTkFrame(self, width=30, height=400, corner_radius=0)
        self.menu_frame.pack_propagate(False)
        self.menu_frame.place(x=0, y=0)
        self.is_show_menu = False
        self.speed_animate_menu = -5

        # Кнопка відкриття меню поверх усього
        self.btn = CTkButton(self, text="⏩", width=30, height=30, command=self.toggle_show_menu)
        self.btn.place(x=0, y=0)

        # Динамічне підлаштування висоти меню під розмір вікна
        self.bind("<Configure>", self.resize_menu)

    def resize_menu(self, event):
        # Щоб меню завжди покривало вікно по висоті при зміні розміру
        if not self.is_show_menu:
            self.menu_frame.configure(height=self.winfo_height(), width=30)
        else:
            self.menu_frame.configure(height=self.winfo_height())

    def toggle_show_menu(self):
        if self.is_show_menu:
            self.is_show_menu = False
            self.speed_animate_menu *= -1
            self.btn.configure(text="⏩")
            self.show_menu()
        else:
            self.is_show_menu = True
            self.speed_animate_menu *= -1
            self.btn.configure(text="⏪")
            self.show_menu()
            
            self.label = CTkLabel(self.menu_frame, text="Введіть ім'я", font=CTkFont(size=16, weight="bold"))
            self.label.place(x=45, y=50)
            self.entry_name = CTkEntry(self.menu_frame, width=140)
            self.entry_name.place(x=45, y=90)

    def show_menu(self):
        current_width = self.menu_frame.winfo_width()
        new_width = current_width + self.speed_animate_menu
        self.menu_frame.configure(width=new_width)
        
        if not new_width >= 200 and self.is_show_menu:
            self.after(10, self.show_menu)
        elif new_width >= 30 and not self.is_show_menu:
            self.after(10, self.show_menu)
            if hasattr(self, 'label') and self.label:
                self.label.destroy()
            if hasattr(self, 'entry_name') and self.entry_name:
                self.entry_name.destroy()

    def add_message(self, message, img=None):
        label = CTkLabel(
            self.chat,
            text=message,
            image=img,
            compound="top",
            anchor="w",
            justify="left"
        )
        label.pack(anchor="w", padx=5, pady=5)

    def send_message(self):
        if hasattr(self, 'entry_name') and self.entry_name.winfo_exists():
            name_val = self.entry_name.get().strip()
            if name_val:
                self.username = name_val

        message = self.entry.get().strip()
        if message:
            self.add_message(f"{self.username}: {message}")
            
            data = f"TEXT@{self.username}@{message}\n"
            try:
                self.client_socket.sendall(data.encode('utf-8'))
            except Exception as e:
                print("Помилка надсилання:", e)
            
            self.entry.delete(0, 'end')
    def send_image(self):
        # Відкриваємо вікно вибору файлу (підтримуються png, jpg, jpeg)
        file_path = filedialog.askopenfilename(
            title="Виберіть зображення",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.gif")]
        )
        
        if file_path:
            try:
                # Читаємо файл у бінарному форматі та кодуємо в base64 рядок
                with open(file_path, "rb") as img_file:
                    encoded_string = base64.b64encode(img_file.read()).decode('utf-8')
                
                # Отримуємо ім'я файлу для відображення
                filename = file_path.split("/")[-1]
                
                # Створюємо локальне прев'ю для себе
                pil_img = Image.open(file_path)
                pil_img.thumbnail((200, 200)) # зменшуємо для чату
                ctk_img = CTkImage(pil_img, size=pil_img.size)
                self.add_message(f"{self.username} надіслав(ла) зображення:", img=ctk_img)
                
                # Формуємо протокол відправки: IMAGE@Ім'яКористувача@Ім'яФайлу@ДаніBase64
                data = f"IMAGE@{self.username}@{filename}@{encoded_string}\n"
                
                # Надсилаємо на сервер
                self.client_socket.sendall(data.encode('utf-8'))
                
            except Exception as e:
                print("Помилка відправки зображення:", e)


    def recv_messages(self):
        buffer = ""
        while True:
            try:
                data = self.client_socket.recv(4096)
                if not data:
                    break

                buffer += data.decode("utf-8")

                while '\n' in buffer:
                    message, buffer = buffer.split('\n', 1)
                    self.handle_line(message.strip())

            except Exception as e:
                print("Помилка отримання:", e)
                break
        try:
            self.client_socket.close()
        except:
            pass

    def handle_line(self, line):
        if not line:
            return
        parts = line.split('@', 2)
        msg_type = parts[0]
        
        if msg_type == "TEXT":
            if len(parts) >= 3:
                username = parts[1]
                message = parts[2]
                self.add_message(f"{username}: {message}")
        elif msg_type == "IMAGE":
            parts = line.split('@,3')
            if len(parts) >= 3:
                username = parts[1]
                filename = parts[2]
                image_data = parts[3]
                try:
                    img_data = base64.b64decode(image_data)
                    pil_img = Image.open(io.BytesIO(img_data))
                    ctk_img = CTkImage(pil_img, size=(200, 200))
                    self.add_message(f"{username} надіслав(ла) зображення:", img=ctk_img)
                except Exception as e:
                    print(f"Error decoding image: {e}")

win = MainWindow()
win.mainloop()