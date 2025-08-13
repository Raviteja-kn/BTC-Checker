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

        # Treeview + Scrollbars
        tree_frame = ttk.Frame(frame)
        tree_frame.grid(row=1, column=0, columnspan=4, pady=10, sticky="nsew")
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(tree_frame, columns=("Address", "WIF", "TX Count", "Balance"), show="headings")
        for col in self.tree["columns"]:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=200, anchor="w")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # Right-click copy menu
        self.menu = tk.Menu(self.root, tearoff=0)
        self.menu.add_command(label="Copy Address", command=lambda: self.copy_column(0))
        self.menu.add_command(label="Copy WIF", command=lambda: self.copy_column(1))

        self.tree.bind("<Button-3>", self.show_menu)

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
                    # Insert and auto-scroll
                    row_id = self.tree.insert("", tk.END, values=item)
                    self.tree.see(row_id)  # Auto-scroll to latest row
        except queue.Empty:
            pass
        self.root.after(100, self.process_queue)

    def show_menu(self, event):
        try:
            row_id = self.tree.identify_row(event.y)
            if row_id:
                self.tree.selection_set(row_id)
                self.menu.post(event.x_root, event.y_root)
        except:
            pass

    def copy_column(self, col_index):
        try:
            selected = self.tree.selection()
            if selected:
                value = self.tree.item(selected[0])["values"][col_index]
                self.root.clipboard_clear()
                self.root.clipboard_append(value)
                self.root.update()
        except:
            pass

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("900x400")
    app = BTCCheckerApp(root)
    root.mainloop()
