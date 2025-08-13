import tkinter as tk
from tkinter import ttk, messagebox
import threading
import queue
import requests
from bit import Key

API_URL = "https://blockchain.info/rawaddr/"

class Worker(threading.Thread):
    def __init__(self, count, queue, stop_event):
        super().__init__()
        self.count = count
        self.q = queue
        self.stop_event = stop_event

    def run(self):
        for _ in range(self.count):
            if self.stop_event.is_set():
                break
            try:
                key = Key()
                address = key.address
                wif = key.to_wif()

                tx_count, balance = self.get_address_info(address)
                self.q.put((address, wif, tx_count, balance))

                # Save to file if TX count or balance is greater than zero
                if tx_count > 0 or balance > 0:
                    with open("Found Wallet.txt", "a") as f:
                        f.write(f"Address: {address}\n")
                        f.write(f"WIF: {wif}\n")
                        f.write(f"TX Count: {tx_count}\n")
                        f.write(f"Balance: {balance} BTC\n")
                        f.write("-" * 40 + "\n")
            except Exception as e:
                self.q.put(("error", str(e)))

        self.q.put(("done", None))

    def get_address_info(self, address):
        try:
            response = requests.get(API_URL + address, timeout=5)
            if response.status_code == 200:
                data = response.json()
                tx_count = data.get("n_tx", 0)
                balance = data.get("final_balance", 0) / 1e8
                return tx_count, balance
        except:
            pass
        return 0, 0

class BTCCheckerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("BTC Address Checker")
        self.queue = queue.Queue()
        self.stop_event = threading.Event()

        self.setup_ui()
        self.worker = None
        self.root.after(100, self.process_queue)

    def setup_ui(self):
        frame = ttk.Frame(self.root, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        self.count_var = tk.IntVar(value=10)
        ttk.Label(frame, text="Number of addresses:").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.count_var, width=10).grid(row=0, column=1)

        self.start_btn = ttk.Button(frame, text="Start", command=self.start_worker)
        self.start_btn.grid(row=0, column=2, padx=5)

        self.stop_btn = ttk.Button(frame, text="Stop", command=self.stop_worker, state=tk.DISABLED)
        self.stop_btn.grid(row=0, column=3)

        self.tree = ttk.Treeview(frame, columns=("Address", "WIF", "TX Count", "Balance"), show="headings")
        for col in self.tree["columns"]:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150)
        self.tree.grid(row=1, column=0, columnspan=4, pady=10)

    def start_worker(self):
        count = self.count_var.get()
        if count <= 0:
            messagebox.showerror("Error", "Please enter a valid count.")
            return

        self.tree.delete(*self.tree.get_children())
        self.stop_event.clear()
        self.worker = Worker(count, self.queue, self.stop_event)
        self.worker.start()
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)

    def stop_worker(self):
        self.stop_event.set()
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)

    def process_queue(self):
        try:
            while True:
                item = self.queue.get_nowait()
                if item[0] == "done":
                    self.start_btn.config(state=tk.NORMAL)
                    self.stop_btn.config(state=tk.DISABLED)
                elif item[0] == "error":
                    messagebox.showerror("Error", item[1])
                else:
                    self.tree.insert("", tk.END, values=item)
        except queue.Empty:
            pass
        self.root.after(100, self.process_queue)

if __name__ == "__main__":
    root = tk.Tk()
    app = BTCCheckerApp(root)
    root.mainloop()
