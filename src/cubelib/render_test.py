from PyQt5.QtWidgets import (QApplication, QListWidget, QListWidgetItem,
                             QStyledItemDelegate, QStyle, QMainWindow)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QBrush, QPalette
import sys

class CustomDelegate(QStyledItemDelegate):
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)

        # Get custom data from the item
        category = index.data(Qt.UserRole + 1)

        # Apply styling based on the category value
        if category == "important":
            option.backgroundBrush = QColor("#ffdddd")  # Light red
            option.font.setBold(True)
        elif category == "completed":
            option.backgroundBrush = QColor("#ddffdd")  # Light green
            option.font.setStrikeOut(True)
        elif category == "pending":
            option.backgroundBrush = QColor("#ffffdd")  # Light yellow

        # You can also customize text color, font, etc.
        if index.data(Qt.UserRole) > 5:
            option.palette.setColor(QPalette.Text, QColor("#0000CC"))  # Dark blue

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Custom List Item Styling Example")
        self.resize(400, 300)

        # Create the list widget
        self.list_widget = QListWidget()

        # Create and add items with different categories
        tasks = [
            {"text": "Finish project proposal", "priority": 8, "category": "important"},
            {"text": "Email client about meeting", "priority": 5, "category": "pending"},
            {"text": "Buy groceries", "priority": 3, "category": "pending"},
            {"text": "Update software", "priority": 4, "category": "completed"},
            {"text": "Schedule dentist appointment", "priority": 7, "category": "important"},
            {"text": "Pay electricity bill", "priority": 6, "category": "pending"},
            {"text": "Return library books", "priority": 2, "category": "completed"}
        ]

        for task in tasks:
            item = QListWidgetItem(task["text"])

            # Store custom data in roles
            item.setData(Qt.UserRole, task["priority"])  # Store priority
            item.setData(Qt.UserRole + 1, task["category"])  # Store category

            self.list_widget.addItem(item)

        # Apply the custom delegate
        self.list_widget.setItemDelegate(CustomDelegate())

        # Connect to item click
        self.list_widget.itemClicked.connect(self.on_item_clicked)

        # Set as central widget
        self.setCentralWidget(self.list_widget)

    def on_item_clicked(self, item):
        priority = item.data(Qt.UserRole)
        category = item.data(Qt.UserRole + 1)
        print(f"Clicked: '{item.text()}'")
        print(f"Priority: {priority}, Category: {category}")

        # You can also change the data and the item will update automatically
        if category == "pending":
            item.setData(Qt.UserRole + 1, "completed")
            self.list_widget.update()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())