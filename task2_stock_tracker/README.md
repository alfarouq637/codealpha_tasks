# Task 2: Stock Portfolio Tracker 📈

A robust Python command-line application that allows users to track their stock investments, calculate portfolio values, and generate automated text reports.

## 📝 Description
This project focuses on practical data structures and file handling in Python. Instead of relying on complex external databases, it uses Python Dictionaries to manage stock data efficiently. It also includes strong input validation to prevent crashes and automatically saves the final portfolio summary to a local `.txt` file.

## ✨ Key Features
* **Data Structures:** Utilizes Python Dictionaries (`dict`) for fast key-value lookups of stock prices.
* **Input Validation:** Implements `try-except` blocks to handle invalid user inputs gracefully (e.g., typing letters instead of numbers).
* **Automated Reporting:** Dynamically calculates total investments and writes a formatted summary to `Portfolio_report.txt` using Python's file I/O operations (`with open`).
* **Interactive CLI:** Provides a clean, user-friendly terminal interface for continuous data entry until the user is done.

## 🚀 How to Run
1. Open your terminal.
2. Navigate to this directory.
3. Run the following command:
   ```bash
   python stock_tracker.py
4. Follow the on-screen prompts. Type DONE when finished to generate your report!
