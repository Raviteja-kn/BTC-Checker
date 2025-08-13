import tkinter as tk
from tkinter import ttk, messagebox
import threading
import queue
import requests
from bit import Key
import os

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

                # Send to UI
                self.q.put((address, wif, tx_count, balance))

                # Save only if TX or Balance > 0
                if tx_count > 0 or balance > 0:
                    with open("Found_Wallets.txt", "a") as f:
                        f.write(f"Address: {address}\n")
                        f.write(f"Private Key (WIF): {wif}\n")
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

        # BTC Icon
        icon_path = "btc.ico"
        if os.path.exists(icon_path):
            self.root.iconbitmap(icon_path)

        # Modern Light Theme
        self.root.tk_setPalette(background='#f0f0f0', foreground='#333333',
                                activeBackground='#e0e0e0', activeForeground='#333333')

        style = ttk.Style()
        style.theme_use("clam")

        # Configure styles for a modern look
        style.configure("TFrame", background='#f0f0f0')
        style.configure("TLabel", background='#f0f0f0', foreground='#333333', font=('Helvetica', 10))
        style.configure("TButton", background='#0078d7', foreground='white', font=('Helvetica', 10, 'bold'), borderwidth=0)
        style.map("TButton", background=[('active', '#005a9e')])
        style.configure("TEntry", fieldbackground='white', foreground='#333333', borderwidth=1, relief='solid')

        # Treeview Styles
        style.configure("Treeview", background='white', foreground='#333333',
                        fieldbackground='white', font=('Helvetica', 9), borderwidth=1, relief='solid')
        style.configure("Treeview.Heading", font=('Helvetica', 10, 'bold'),
                        background='#e0e0e0', foreground='#333333', borderwidth=1, relief='solid')
        style.map("Treeview", background=[('selected', '#b3d7ff')])

        self.setup_ui()
        self.worker = None
        self.root.after(100, self.process_queue)

    def setup_ui(self):
        frame = ttk.Frame(self.root, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        # Top control frame
        top_frame = ttk.Frame(frame, padding=(0, 0, 0, 10))
        top_frame.grid(row=0, column=0, columnspan=2, sticky="ew")

        self.count_var = tk.IntVar(value=10)
        ttk.Label(top_frame, text="Number of addresses:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(top_frame, textvariable=self.count_var, width=10).pack(side=tk.LEFT, padx=(0, 15))

        self.start_btn = ttk.Button(top_frame, text="Start", command=self.start_worker)
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = ttk.Button(top_frame, text="Stop", command=self.stop_worker, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT)

        # Treeview with Scrollbar in its own frame
        tree_frame = ttk.Frame(frame)
        tree_frame.grid(row=1, column=0, columnspan=2, sticky="nsew")

        self.tree = ttk.Treeview(tree_frame, columns=("Address", "WIF", "TX Count", "Balance"), show="headings")
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        for col in self.tree["columns"]:
            self.tree.heading(col, text=col, anchor='w')
            self.tree.column(col, width=200, anchor='w')

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=vsb.set)
        
        # Adjust column widths
        self.tree.column("Address", width=200)
        self.tree.column("WIF", width=250)
        self.tree.column("TX Count", width=80)
        self.tree.column("Balance", width=100)

        frame.rowconfigure(1, weight=1)
        frame.columnconfigure(0, weight=1)

        # Double-click to copy
        self.tree.bind("<Double-1>", self.copy_cell_value)

    def copy_cell_value(self, event):
        item_id = self.tree.focus()
        if not item_id:
            return
        
        col = self.tree.identify_column(event.x)
        if col == '': return
        
        col_index = int(col.replace("#", "")) - 1
        value = self.tree.item(item_id)["values"][col_index]
        if value:
            self.root.clipboard_clear()
            self.root.clipboard_append(str(value))
            self.root.update()
            messagebox.showinfo("Copied", f"Copied: {value}", parent=self.root)

    def start_worker(self):
        try:
            count = self.count_var.get()
            if count <= 0:
                messagebox.showerror("Error", "Please enter a valid count.", parent=self.root)
                return
        except tk.TclError:
            messagebox.showerror("Error", "Please enter a valid number.", parent=self.root)
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
                    messagebox.showerror("Error", item[1], parent=self.root)
                else:
                    row_id = self.tree.insert("", tk.END, values=item)
                    self.tree.see(row_id)
        except queue.Empty:
            pass
        self.root.after(100, self.process_queue)

if __name__ == "__main__":
    root = tk.Tk()
    app = BTCCheckerApp(root)
    root.mainloop()
