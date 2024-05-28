import json
import threading
import random
import asyncio
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTableView,
    QHeaderView,
    QLineEdit,
    QMessageBox,
    QCheckBox,
    QLabel,
    QComboBox,
    QTabWidget,
    QFrame,
    QGridLayout
)
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QIcon
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from playwright.async_api import async_playwright

class ThreadsAccount:
    def __init__(self, username, password, max_concurrent_tasks=2): 
        self.username = username
        self.password = password
        self.lock = asyncio.Lock()
        self.semaphore = asyncio.Semaphore(max_concurrent_tasks)

class ThreadsAutomation(QObject):
    status_updated = pyqtSignal(int, str)

    def __init__(self):
        super().__init__()
        self.accounts = []
        self.load_accounts()

    def load_accounts(self):
        try:
            with open("accounts.json", "r") as f:
                data = json.load(f)
                self.accounts = [ThreadsAccount(acc["username"], acc["password"]) for acc in data]
        except FileNotFoundError:
            pass

    def save_accounts(self):
        data = [{"username": acc.username, "password": acc.password} for acc in self.accounts]
        with open("accounts.json", "w") as f:
            json.dump(data, f)

    async def login(self, account):
        async with account.lock:
            try:
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=False)
                    page = await browser.new_page()
                    await page.goto("https://www.threads.net/login")

                    await page.fill("input[name='username']", account.username)
                    await page.fill("input[name='password']", account.password)
                    await page.click("button[type='submit']")

                    await page.wait_for_selector("//h1[contains(text(), 'Chào mừng')]")
                    return True
            except Exception as e:
                print(f"Lỗi đăng nhập cho tài khoản {account.username}: {e}")
                return False

    async def like_post(self, account, url):
        async with account.semaphore:
            async with account.lock:
                try:
                    async with async_playwright() as p:
                        browser = await p.chromium.launch(headless=False)
                        page = await browser.new_page()
                        await page.goto(url)

                        # Tìm và click vào nút like
                        like_button = await page.wait_for_selector('button[aria-label="Thích"]')
                        await like_button.click()

                        await browser.close()
                        await asyncio.sleep(random.randint(1, 3))
                except Exception as e:
                        print(f"Lỗi like bài viết cho tài khoản {account.username}: {e}")

    async def comment_post(self, account, url, content):
        async with account.semaphore:
            async with account.lock:
                try:
                    async with async_playwright() as p:
                        browser = await p.chromium.launch(headless=False)
                        page = await browser.new_page()
                        await page.goto(url)

                        comment_box = await page.query_selector('textarea[placeholder="Viết bình luận..."]') 
                        await comment_box.click()
                        await comment_box.type(content)

                        submit_button = await page.query_selector('button[type="submit"]') 
                        await submit_button.click()

                        await browser.close()
                        print("Đã bình luận thành công!")
                except Exception as e:
                    print(f"Lỗi khi bình luận: {e}")

    async def follow_user(self, account, username):
        async with account.semaphore:
            async with account.lock:
                try:
                    async with async_playwright() as p:
                        browser = await p.chromium.launch(headless=False)
                        page = await browser.new_page()

                        # Thay thế URL này bằng URL trang cá nhân của người dùng bạn muốn theo dõi
                        await page.goto(f"https://www.threads.net/{username}") 

                        # Tìm và click vào nút "Theo dõi"
                        follow_button = await page.wait_for_selector('button[aria-label="Theo dõi"]') 
                        await follow_button.click()

                        await browser.close()
                        print(f"Đã theo dõi người dùng {username}!")
                except Exception as e:
                    print(f"Lỗi khi theo dõi người dùng: {e}")

    async def execute_actions(self, account, function, target, content, row):
        self.status_updated.emit(row, "Đang chờ...")
        async with account.semaphore:
            self.status_updated.emit(row, "Đang đăng nhập...")
            success = await self.login(account)
            if success:
                try:
                    if function == "Like bài viết":
                        self.status_updated.emit(row, "Đang like...")
                        await self.like_post(account, target)
                        self.status_updated.emit(row, "Đã like")
                    elif function == "Bình luận bài viết":
                        self.status_updated.emit(row, "Đang bình luận...")
                        await self.comment_post(account, target, content)
                        self.status_updated.emit(row, "Đã bình luận")
                    elif function == "Theo dõi người dùng":
                        self.status_updated.emit(row, "Đang theo dõi...")
                        await self.follow_user(account, target)
                        self.status_updated.emit(row, "Đã theo dõi")
                except Exception as e:
                    self.status_updated.emit(row, f"Lỗi: {e}")
            else:
                self.status_updated.emit(row, "Đăng nhập thất bại")
            await asyncio.sleep(random.randint(1, 3))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Công cụ tự động hóa Threads.Net")
        self.setGeometry(100, 100, 1200, 600) 

        self.automation = ThreadsAutomation()
        self.automation.status_updated.connect(self.update_table_status)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        # Tạo Tab Widget
        self.tabs = QTabWidget()
        self.tab1 = QWidget()
        self.tab2 = QWidget()
        self.tabs.addTab(self.tab1, "Quản lý tài khoản")
        self.tabs.addTab(self.tab2, "Tự động hóa")
        self.layout.addWidget(self.tabs)

        # Tab 1: Quản lý tài khoản
        self.tab1_layout = QVBoxLayout(self.tab1)
        self.table_view = QTableView()
        self.table_model = QStandardItemModel()
        self.table_model.setHorizontalHeaderLabels(["Tài khoản", "Mật khẩu", "Trạng thái"])
        self.table_view.setModel(self.table_model)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tab1_layout.addWidget(self.table_view)

        self.input_layout = QHBoxLayout()
        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.add_button = QPushButton("Thêm tài khoản")
        self.add_button.clicked.connect(self.add_account)
        self.input_layout.addWidget(QLabel("Tên đăng nhập:"))
        self.input_layout.addWidget(self.username_input)
        self.input_layout.addWidget(QLabel("Mật khẩu:"))
        self.input_layout.addWidget(self.password_input)
        self.input_layout.addWidget(self.add_button)
        self.tab1_layout.addLayout(self.input_layout)

        self.button_layout = QHBoxLayout()
        self.edit_button = QPushButton("Sửa tài khoản")
        self.edit_button.clicked.connect(self.edit_account)
        self.delete_button = QPushButton("Xóa tài khoản")
        self.delete_button.clicked.connect(self.delete_account)
        self.button_layout.addWidget(self.edit_button)
        self.button_layout.addWidget(self.delete_button)
        self.tab1_layout.addLayout(self.button_layout)

        # Tab 2: Tự động hóa
        self.tab2_layout = QVBoxLayout(self.tab2)
        self.config_layout = QGridLayout()
        self.config_layout.addWidget(QLabel("Chức năng:"), 0, 0)
        self.function_combobox = QComboBox()
        self.function_combobox.addItems(["Like bài viết", "Bình luận bài viết", "Theo dõi người dùng"])
        self.config_layout.addWidget(self.function_combobox, 0, 1)
        self.config_layout.addWidget(QLabel("URL/Nội dung/Tên người dùng:"), 1, 0)
        self.target_input = QLineEdit()
        self.config_layout.addWidget(self.target_input, 1, 1)
        self.config_layout.addWidget(QLabel("Nội dung bình luận:"), 2, 0)  # Thêm label cho nội dung bình luận
        self.comment_input = QLineEdit()  # Thêm input cho nội dung bình luận
        self.config_layout.addWidget(self.comment_input, 2, 1)  # Đặt input vào layout
        self.run_button = QPushButton("Chạy tự động hóa")
        self.run_button.clicked.connect(self.run_automation)
        self.config_layout.addWidget(self.run_button, 3, 0, 1, 2) 
        self.tab2_layout.addLayout(self.config_layout)

        self.load_accounts_to_table()

    def update_table_status(self, row, status):
        self.table_model.setItem(row, 2, QStandardItem(status))

    def load_accounts_to_table(self):
        self.table_model.removeRows(0, self.table_model.rowCount())
        for account in self.automation.accounts:
            username_item = QStandardItem(account.username)
            password_item = QStandardItem(account.password)
            status_item = QStandardItem("Chưa hoạt động")  # Mặc định là "Chưa hoạt động"
            self.table_model.appendRow([username_item, password_item, status_item])

    def add_account(self):
        username = self.username_input.text()
        password = self.password_input.text()
        if username and password:
            self.automation.accounts.append(ThreadsAccount(username, password))
            self.automation.save_accounts()
            self.load_accounts_to_table()
            self.username_input.clear()
            self.password_input.clear()
        else:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập tên đăng nhập và mật khẩu.")

    def edit_account(self):
        selected_index = self.table_view.selectedIndexes()
        if selected_index:
            row = selected_index[0].row()
            account = self.automation.accounts[row]
            username_item = self.table_model.item(row, 0)
            password_item = self.table_model.item(row, 1)
            username_item.setText(account.username)
            password_item.setText(account.password)
            self.automation.save_accounts()
        else:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn tài khoản để sửa.")

    def delete_account(self):
        selected_index = self.table_view.selectedIndexes()
        if selected_index:
            row = selected_index[0].row()
            del self.automation.accounts[row]
            self.automation.save_accounts()
            self.load_accounts_to_table()
        else:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn tài khoản để xóa.")

    def run_automation(self):
        function = self.function_combobox.currentText()
        target = self.target_input.text()
        comment_content = self.comment_input.text()  # Lấy nội dung bình luận

        if not target:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập URL/Nội dung/Tên người dùng.")
            return

        async def run_tasks():
            tasks = []
            for row in range(self.table_model.rowCount()):
                account = self.automation.accounts[row]
                tasks.append(self.automation.execute_actions(account, function, target, comment_content, row))

            await asyncio.gather(*tasks)

        threading.Thread(target=lambda: asyncio.run(run_tasks())).start()

if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec_() 
