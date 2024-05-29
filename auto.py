import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from playwright.sync_api import sync_playwright
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QVBoxLayout,
    QMenu,
    QHeaderView,
    QAbstractItemView,
    QAction,
    QCheckBox,
    QGridLayout,
    QLabel,
    QLineEdit,
    QTabWidget,
    QDialog,
)
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, QPoint, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QColor

class ThreadsAutomator:
    def __init__(self):
        self.accounts_data = {}
        self.status_callback = None
        self.running_accounts = {}
        self.headless_mode = False
        self.max_workers = 5
        self.rate_limit = 2
        self.last_action_time = 0
        self.delay_time = 2
        self.load_config()

    def load_accounts(self, filename):
        try:
            with open(filename, 'r') as f:
                self.accounts_data = json.load(f)
        except FileNotFoundError:
            QMessageBox.warning(None, "Lỗi", "Không tìm thấy file tài khoản.")

    def save_accounts(self, filename):
        try:
            with open(filename, 'w') as f:
                json.dump(self.accounts_data, f)
        except Exception as e:
            QMessageBox.warning(None, "Lỗi", f"Không thể lưu file tài khoản: {e}")

    def load_config(self, filename='config.json'):
        try:
            with open(filename, 'r') as f:
                config = json.load(f)
                self.headless_mode = config.get('headless_mode', False)
                self.rate_limit = config.get('rate_limit', 2)
                self.delay_time = config.get('delay_time', 2)
        except FileNotFoundError:
            self.save_config()

    def save_config(self, filename='config.json'):
        try:
            with open(filename, 'w') as f:
                config = {
                    'headless_mode': self.headless_mode,
                    'rate_limit': self.rate_limit,
                    'delay_time': self.delay_time
                }
                json.dump(config, f)
        except Exception as e:
            QMessageBox.warning(None, "Lỗi", f"Không thể lưu file cấu hình: {e}")

    def set_status_callback(self, callback):
        self.status_callback = callback

    def run_automator(self, accounts=None, headless=False):
        self.headless_mode = headless
        if accounts:
            accounts_to_run = [(username, self.accounts_data[username]) for username in accounts]
        else:
            accounts_to_run = self.accounts_data.items()

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            for username, password in accounts_to_run:
                if username not in self.running_accounts: 
                    self.running_accounts[username] = True  # Đánh dấu tài khoản đang chạy
                    future = executor.submit(self.run_account, username, password)
                    future.add_done_callback(lambda f: self.handle_account_finish(f, username))

    def run_account(self, username, password):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless_mode)
            page = browser.new_page()
            try:
                page.goto('https://threads.net/login')
                page.fill('.x1e56ztr:nth-child(2) > .x1i10hfl', username)
                page.fill('.x1n2onr6 > .x1s07b3s', password)
                page.click('div.xofrnu2')
                page.wait_for_selector('.x137v6ai > .x78zum5', timeout=10000)  # Tăng timeout lên 10 giây

                if page.is_visible('.x137v6ai > .x78zum5'):
                    if page.is_visible('div.xz401s1'):
                        if self.status_callback:
                            self.status_callback(username, "Đăng nhập thành công")
                        print(f"Đăng nhập thành công: {username}")
                    else:
                        if self.status_callback:
                            self.status_callback(username, "Sai mật khẩu")
                        print(f"Sai mật khẩu: {username}")
                else:
                    if self.status_callback:
                        self.status_callback(username, "Không tìm thấy tài khoản")
                    print(f"Không tìm thấy tài khoản: {username}")

                time.sleep(self.delay_time)
            except Exception as e:
                print(f"Automation failed for {username}: {e}")
                if self.status_callback:
                    self.status_callback(username, f"Lỗi: {e}")
            finally:
                browser.close()

    def handle_account_finish(self, future, username):
        try:
            future.result()
        except Exception as ex:
            print(f"Error: {ex}")
        finally:
            self.running_accounts[username] = False
            if self.status_callback:
                self.status_callback(username, "Hoàn thành")

    def enforce_rate_limit(self):
        current_time = time.time()
        if current_time - self.last_action_time < self.rate_limit:
            time.sleep(self.rate_limit - (current_time - self.last_action_time))
        self.last_action_time = time.time()


class AccountDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Quản lý Tài khoản")
        self.layout = QVBoxLayout()
        self.username_label = QLabel("Username:")
        self.username_input = QLineEdit()
        self.password_label = QLabel("Password:")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.add_button = QPushButton("Thêm")
        self.add_button.clicked.connect(self.add_account)
        self.layout.addWidget(self.username_label)
        self.layout.addWidget(self.username_input)
        self.layout.addWidget(self.password_label)
        self.layout.addWidget(self.password_input)
        self.layout.addWidget(self.add_button)
        self.setLayout(self.layout)

    def add_account(self):
        username = self.username_input.text()
        password = self.password_input.text()
        if username and password:
            self.parent().automator.accounts_data[username] = password
            self.parent().automator.save_accounts('accounts.json')
            self.parent().display_accounts()
            self.close()
        else:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập đầy đủ thông tin tài khoản.")


class DeleteConfirmationDialog(QDialog):
    def __init__(self, username, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Xác nhận xóa")
        self.layout = QVBoxLayout()
        self.message_label = QLabel(f"Bạn có chắc chắn muốn xóa tài khoản {username}?")
        self.yes_button = QPushButton("Có")
        self.yes_button.clicked.connect(self.delete_account)
        self.no_button = QPushButton("Không")
        self.no_button.clicked.connect(self.close)
        self.layout.addWidget(self.message_label)
        self.layout.addWidget(self.yes_button)
        self.layout.addWidget(self.no_button)
        self.setLayout(self.layout)
        self.username = username

    def delete_account(self):
        self.parent().automator.accounts_data.pop(self.username, None)
        self.parent().automator.save_accounts('accounts.json')
        self.parent().display_accounts()
        self.close()


class AutomatorGUI(QWidget):

    update_status_signal = pyqtSignal(list)
    def __init__(self):
        super().__init__()
        self.automator = ThreadsAutomator()
        self.initUI()
        self.automator.set_status_callback(self.update_account_status)
        self.automator.load_accounts('accounts.json')
        self.display_accounts()

        self.update_status_signal.connect(self.update_account_status)
    def initUI(self):
        self.setWindowTitle("Công cụ tự động hóa Threads")
        self.setGeometry(300, 300, 800, 500)

        mainLayout = QVBoxLayout()
        self.tab_widget = QTabWidget()
        mainLayout.addWidget(self.tab_widget)

        self.function_tab = QWidget()
        self.function_layout = QVBoxLayout()
        self.function_tab.setLayout(self.function_layout)

        add_account_button = QPushButton("Thêm tài khoản", self)
        add_account_button.clicked.connect(self.open_account_dialog)
        self.function_layout.addWidget(add_account_button)

        self.accounts_table = QTableWidget(self)
        self.accounts_table.setColumnCount(3)
        self.accounts_table.setHorizontalHeaderLabels(
            ["Username", "Password", "Trạng thái"]
        )
        self.accounts_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.accounts_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.accounts_table.customContextMenuRequested.connect(self.show_context_menu)
        self.accounts_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.accounts_table.setSelectionMode(QAbstractItemView.MultiSelection)
        self.function_layout.addWidget(self.accounts_table)

        # Tab Cấu hình
        self.config_tab = QWidget()
        self.config_layout = QVBoxLayout()
        self.config_tab.setLayout(self.config_layout)

        # Tùy chọn headless
        headless_layout = QGridLayout()
        headless_label = QLabel("Chế độ headless:")
        self.headless_checkbox = QCheckBox()
        headless_layout.addWidget(headless_label, 0, 0)
        headless_layout.addWidget(self.headless_checkbox, 0, 1)
        self.config_layout.addLayout(headless_layout)

        # Nhập thời gian delay
        delay_layout = QGridLayout()
        delay_label = QLabel("Thời gian delay (giây):")
        self.delay_input = QLineEdit("2")
        delay_layout.addWidget(delay_label, 0, 0)
        delay_layout.addWidget(self.delay_input, 0, 1)
        self.config_layout.addLayout(delay_layout)

        # Nút "Lưu cấu hình"
        save_config_button = QPushButton("Lưu cấu hình", self)
        save_config_button.clicked.connect(self.save_config)
        self.config_layout.addWidget(save_config_button)

        # Thêm các tab vào tab widget
        self.tab_widget.addTab(self.function_tab, "Chức năng")
        self.tab_widget.addTab(self.config_tab, "Cấu hình")

        start_all_button = QPushButton("Bắt đầu tất cả", self)
        start_all_button.clicked.connect(lambda: self.start_automator(headless=self.headless_checkbox.isChecked()))
        self.function_layout.addWidget(start_all_button)

        run_selected_button = QPushButton("Chạy đã chọn", self)
        run_selected_button.clicked.connect(self.run_selected_accounts)
        self.function_layout.addWidget(run_selected_button)

        self.setLayout(mainLayout)
        self.show()

        self.headless_checkbox.setChecked(self.automator.headless_mode)

        # Register QVector<int> for signal/slot usage -  You can remove this line if not needed
        # Register QVector<int> for signal/slot usage
#        QThread.currentThread().setObjectName('MainThread')
  #      QMetaObject.registerArgumentMetaType('QVector<int>') 
    def my_method(self):
        data = [1, 2, 3]  # Your data, now a Python list
        self.mySignal.emit(data)  # No need for Q_ARG
    def open_account_dialog(self):
        dialog = AccountDialog(self)
        dialog.exec_()

    def display_accounts(self):
        self.accounts_table.setRowCount(0)
        for row, (username, password) in enumerate(self.automator.accounts_data.items()):
            self.accounts_table.insertRow(row)
            self.accounts_table.setItem(row, 0, QTableWidgetItem(username))
            self.accounts_table.setItem(row, 1, QTableWidgetItem(password))
            self.accounts_table.setItem(row, 2, QTableWidgetItem("Chưa chạy"))

    def show_context_menu(self, position):
        menu = QMenu()
        delete_action = QAction("Xóa", self)
        delete_action.triggered.connect(lambda: self.delete_selected_accounts())
        menu.addAction(delete_action)
        menu.exec_(self.accounts_table.viewport().mapToGlobal(position))

    def delete_selected_accounts(self):
        selected_items = self.accounts_table.selectedItems()
        if selected_items:
            selected_usernames = {self.accounts_table.item(i.row(), 0).text() for i in selected_items if i.column() == 0}
            for username in selected_usernames:
                dialog = DeleteConfirmationDialog(username, self)
                dialog.exec_()

    def save_config(self):
        try:
            self.automator.headless_mode = self.headless_checkbox.isChecked()
            self.automator.delay_time = float(self.delay_input.text())
            self.automator.save_config()
            QMessageBox.information(self, "Thông báo", "Cấu hình đã được lưu.")
        except ValueError:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập thời gian delay hợp lệ.")

    def start_automator(self, headless=False):
        try:
            self.automator.delay_time = float(self.delay_input.text())
            threading.Thread(target=self.automator.run_automator, args=(None, headless)).start()
        except ValueError:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập thời gian delay hợp lệ.")

    def run_selected_accounts(self):
        try:
            self.automator.delay_time = float(self.delay_input.text())
            selected_items = self.accounts_table.selectedItems()
            selected_usernames = set()  # Initialize set to store selected usernames
            if selected_items:
                for item in selected_items:
                    if item.column() == 0:
                        selected_usernames.add(item.text())
                # Emit the update_status_signal with selected usernames and "Đang chạy" status
                for username in selected_usernames:
                    self.update_status_signal.emit([username, "Đang chạy"])
                threading.Thread(target=self.automator.run_automator, args=(
                    selected_usernames, self.headless_checkbox.isChecked())).start()
            else:
                QMessageBox.warning(self, "Lỗi", "Vui lòng chọn tài khoản để chạy.")
        except ValueError:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập thời gian delay hợp lệ.")

    def update_account_status(self, data):
        username, status = data[0], data[1]  # Unpack the data
        for row in range(self.accounts_table.rowCount()):
            if self.accounts_table.item(row, 0).text() == username:
                self.accounts_table.setItem(row, 2, QTableWidgetItem(status))
                if status == "Hoàn thành":
                    self.accounts_table.item(row, 2).setBackground(QColor('green'))
                else:
                    self.accounts_table.item(row, 2).setBackground(QColor('yellow'))
                break

if __name__ == "__main__":
    app = QApplication([])
    gui = AutomatorGUI()
    app.exec_()
