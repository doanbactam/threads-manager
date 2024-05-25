import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QLineEdit, QPushButton, QTableWidget,
                              QTableWidgetItem, QVBoxLayout, QHBoxLayout, QFormLayout, QFileDialog,
                              QSpacerItem, QSizePolicy, QDialog, QGridLayout, QComboBox,
                              QHeaderView)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import threading
import os

class Account:
    def __init__(self, username, password, proxy=None):
        self.username = username
        self.password = password
        self.proxy = proxy
        self.status = "Offline"
        self.driver = None

class AccountManager(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Threads Automation")

        # Load accounts from file
        self.accounts = self.load_accounts()

        # Create UI elements
        self.account_table = QTableWidget()
        self.account_table.setColumnCount(5)  # Thêm cột Action
        self.account_table.setHorizontalHeaderLabels(
            ["Username", "Password", "Proxy", "Status", "Action"])

        # Create Button Panel
        self.button_panel = QWidget()
        self.button_layout = QHBoxLayout()
        self.button_panel.setLayout(self.button_layout)

        self.add_account_button = QPushButton("Add Account")
        self.add_account_button.clicked.connect(self.add_account)
        self.button_layout.addWidget(self.add_account_button)

        self.start_all_button = QPushButton("Start All")
        self.start_all_button.clicked.connect(self.start_all_tasks)
        self.button_layout.addWidget(self.start_all_button)

        # Create Settings Panel
        self.settings_panel = QWidget()
        self.settings_layout = QGridLayout()
        self.settings_panel.setLayout(self.settings_layout)

        # Add settings options
        self.delay_like_input = QLineEdit()
        self.delay_like_input.setText("5")
        self.settings_layout.addWidget(QLabel("Delay Like (seconds)"), 0, 0)
        self.settings_layout.addWidget(self.delay_like_input, 0, 1)

        self.delay_comment_input = QLineEdit()
        self.delay_comment_input.setText("10")
        self.settings_layout.addWidget(QLabel("Delay Comment (seconds)"), 1, 0)
        self.settings_layout.addWidget(self.delay_comment_input, 1, 1)

        self.comment_text_input = QLineEdit()
        self.comment_text_input.setText("Nice post!")
        self.settings_layout.addWidget(QLabel("Default Comment"), 2, 0)
        self.settings_layout.addWidget(self.comment_text_input, 2, 1)

        # Add action dropdown (Example)
        self.action_dropdown = QComboBox()
        self.action_dropdown.addItems(["Like", "Comment", "Share"])
        self.settings_layout.addWidget(QLabel("Default Action"), 3, 0)
        self.settings_layout.addWidget(self.action_dropdown, 3, 1)

        # Create main layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.account_table)
        main_layout.addWidget(self.button_panel)
        main_layout.addWidget(self.settings_panel)
        main_layout.addSpacerItem(
            QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        self.setLayout(main_layout)

        # Populate table with accounts
        self.update_account_table()

        # Resize datatable
        self.account_table.horizontalHeader().setStretchLastSection(True)
        self.account_table.resizeColumnsToContents()
        # Kết nối tín hiệu cho button "Start"
        self.account_table.cellClicked.connect(self.start_task)

        # Thay đổi kích thước cửa sổ
        self.resize(800, 600)  # Thay đổi chiều rộng và chiều cao

    def load_accounts(self):
        # Load accounts from a file (e.g., accounts.txt)
        accounts = []
        try:
            with open("accounts.txt", "r") as f:
                for line in f:
                    parts = line.strip().split("|")
                    if len(parts) >= 2:
                        username, password = parts[0], parts[1]
                        proxy = parts[2] if len(parts) >= 3 else None
                        accounts.append(Account(username, password, proxy))
        except FileNotFoundError:
            pass
        return accounts

    def save_accounts(self):
        # Save accounts to a file (e.g., accounts.txt)
        with open("accounts.txt", "w") as f:
            for account in self.accounts:
                f.write(f"{account.username}|{account.password}|{account.proxy or ''}\n")

    def add_account(self):
        # Open a new form to add a new account
        add_account_form = AddAccountForm(self.accounts)
        if add_account_form.exec_():
            self.accounts = add_account_form.accounts
            self.save_accounts()
            self.update_account_table()

    def update_account_table(self):
        # Update the table with account information
        self.account_table.setRowCount(len(self.accounts))
        for i, account in enumerate(self.accounts):
            self.account_table.setItem(i, 0, QTableWidgetItem(account.username))
            self.account_table.setItem(i, 1, QTableWidgetItem(account.password))
            self.account_table.setItem(i, 2, QTableWidgetItem(account.proxy or ""))
            self.account_table.setItem(i, 3, QTableWidgetItem(account.status))

            # Thêm button "Start"
            start_button = QPushButton("Start")
            start_button.clicked.connect(lambda checked, row=i: self.start_task(row))
            self.account_table.setCellWidget(i, 4, start_button)
        # Resize columns after adding widgets
        self.account_table.horizontalHeader().setStretchLastSection(True)
        self.account_table.resizeColumnsToContents()

    def start_task(self, row):
        account = self.accounts[row]
        account_task = AccountTask(account, self.delay_like_input.text(),
                                   self.delay_comment_input.text(),
                                   self.comment_text_input.text(),
                                   self.action_dropdown.currentText())
        account_task.status_changed.connect(
            lambda status, username: self.update_account_table())
        account_task.start()

    def start_all_tasks(self):
        self.tasks = []  # Lưu trữ các luồng AccountTask
        for account in self.accounts:
            account_task = AccountTask(account, self.delay_like_input.text(),
                                       self.delay_comment_input.text(),
                                       self.comment_text_input.text(),
                                       self.action_dropdown.currentText())
            account_task.status_changed.connect(
                lambda status, username: self.update_account_table())
            account_task.start()
            self.tasks.append(account_task)

    # Hủy tất cả luồng khi đóng ứng dụng
        # Hủy tất cả luồng khi đóng ứng dụng
        def closeEvent(self, event):
            for task in self.tasks:
                if task.isRunning():  # Kiểm tra luồng có đang chạy hay không
                    task.quit()
                    task.wait()
            event.accept()

        # Kết nối closeEvent với tín hiệu close
        self.closeEvent = closeEvent  # Di chuyển dòng này vào đây


class AddAccountForm(QDialog):
    def __init__(self, accounts):
        super().__init__()
        self.setWindowTitle("Add Account")
        self.accounts = accounts

        # Create UI elements
        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.proxy_input = QLineEdit()
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_account)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.close)

        # Create layout
        layout = QFormLayout()
        layout.addRow(QLabel("Username"), self.username_input)
        layout.addRow(QLabel("Password"), self.password_input)
        layout.addRow(QLabel("Proxy (optional)"), self.proxy_input)
        layout.addRow(self.save_button, self.cancel_button)

        self.setLayout(layout)

    def save_account(self):
        username = self.username_input.text()
        password = self.password_input.text()
        proxy = self.proxy_input.text()
        if username and password:
            self.accounts.append(Account(username, password, proxy))
            self.accept()


class AccountTask(QThread):
    status_changed = pyqtSignal(str, str)

    def __init__(self, account, delay_like, delay_comment, comment_text, action):
        super().__init__()
        self.account = account
        self.delay_like = delay_like
        self.delay_comment = delay_comment
        self.comment_text = comment_text
        self.action = action

    def run(self):
        # Initialize Selenium driver with proxy (if provided)
        chrome_options = Options()
        if self.account.proxy:
            chrome_options.add_argument(f"--proxy-server={self.account.proxy}")
        self.account.driver = webdriver.Chrome(options=chrome_options)

        # Di chuyển self.finished.connect(self.cleanup) vào đây
        self.finished.connect(self.cleanup)

        try:
            # Login to Threads.Net
            self.account.driver.get("https://www.threads.net")
            # ... (Add login logic here)
            # Ví dụ đơn giản:
            username_input = self.account.driver.find_element(
                By.XPATH, "//input[@name='username']")
            password_input = self.account.driver.find_element(
                By.XPATH, "//input[@name='password']")
            login_button = self.account.driver.find_element(
                By.XPATH, "//button[@type='submit']")
            username_input.send_keys(self.account.username)
            password_input.send_keys(self.account.password)
            login_button.click()

            WebDriverWait(self.account.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'profile-card')]")))
            self.status_changed.emit(self.account.username, "Login successful")

            # Perform tasks (e.g., like, share, comment)
            # ... (Add task logic here)
            if self.action == "Like":
                # ... (Thực hiện like)
                # Ví dụ đơn giản:
                like_button = self.account.driver.find_element(
                    By.XPATH, "//button[contains(@aria-label, 'Like')]")
                like_button.click()
                time.sleep(int(self.delay_like))

            elif self.action == "Comment":  # Thụt lùi khối lệnh này
                # ... (Thực hiện comment)
                # Ví dụ đơn giản:
                comment_box = self.account.driver.find_element(
                    By.XPATH, "//textarea[contains(@aria-label, 'Comment')]")
                comment_box.send_keys(self.comment_text)
                comment_box.submit()
                time.sleep(int(self.delay_comment))

            elif self.action == "Share":
                # ... (Thực hiện share)
                # Ví dụ đơn giản:
                share_button = self.account.driver.find_element(
                    By.XPATH, "//button[contains(@aria-label, 'Share')]")
                share_button.click()
                time.sleep(5)  # Đợi 5 giây để quá trình share hoàn thành

        except Exception as e:
            self.status_changed.emit(self.account.username, f"Error: {e}")

        finally:
            if self.account.driver:
                self.account.driver.quit()

    def cleanup(self):
        # Thêm logic dọn dẹp ở đây nếu cần
        print(f"{self.account.username}: Cleanup complete")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    account_manager = AccountManager()
    account_manager.show()
    sys.exit(app.exec_())
