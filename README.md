# BTC Address Checker

A simple Python application to generate Bitcoin addresses, check their balances and transaction count, and save any non-empty wallets. Built using **Tkinter**, **threading**, and the **bit** library.

---

## Features

- Generate multiple Bitcoin addresses.
- Check each address's transaction count and balance using the [Blockchain.info API](https://blockchain.info/).
- Save wallets with a non-zero balance or transaction history to a file.
- Simple and intuitive GUI with progress updates.
- Start and stop address checking anytime.

---

## Requirements

- Python 3.13 or higher
- Libraries:
  - `bit`
  - `requests`
  - `tkinter` (usually comes with Python)

---

## Installation & Commands

1. Clone the repository:
 
"git clone https://github.com/YOUR_USERNAME/BTC-Address-Checker.git
cd BTC-Address-Checker"

2. Install dependencies:

"python btc_checker_app.py"

tkinter is included by default with most Python installations. If missing, install via your OS package manager:

Windows: Already included with Python installer

Linux (Debian/Ubuntu): "sudo apt install python3-tk"

MacOS: Already included with Python

3. Run the application:

"python btc_checker_app.py"

4. Proof / Results:
<img width="783" height="407" alt="image" src="https://github.com/user-attachments/assets/66d44498-eebb-4ccb-8b44-db2357285534" />


⚠️ Disclaimer
IMPORTANT:

This tool is for educational purposes only.
Do not attempt to access wallets you do not own. Doing so is illegal and punishable by law.
The author is not responsible for any misuse of this software.
Use at your own risk.2

License
MIT License. See LICENSE for details.
