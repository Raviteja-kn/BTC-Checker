import tkinter as tk
from tkinter import ttk, messagebox
import threading
import queue
import requests
from bit import Key
import os
import time

# Use the batch-supporting API endpoint
API_URL = "https://blockchain.info/balance?active="
BATCH_SIZE = 100 # Number of addresses to check in a single API call

class Worker(threading.Thread):
    # ... (Worker class is unchanged)
    def __init__(self, thread_id, work_queue, ui_queue, stop_event):
        super().__init__(daemon=True)
        self.thread_id = thread_id
        self.work_queue = work_queue
        self.ui_queue = ui_queue
        self.stop_event = stop_event
        self.session = requests.Session() # Use a session for connection pooling

    def run(self):
        while not self.stop_event.is_set():
            try:
                # Generate a batch of keys first
                keys_batch = {}
                for _ in range(BATCH_SIZE):
                    key = Key()
                    keys_batch[key.address] = key.to_wif()

                # Check if we need to stop before the network request
                if self.stop_event.is_set():
                    break

                # Query the API with a batch of addresses
                addresses_to_check = "|".join(keys_batch.keys())
                self.check_batch(addresses_to_check, keys_batch)

                # Inform UI that a batch has been processed
                self.ui_queue.put(('status', {'checked': BATCH_SIZE}))

                # Take a small break to be nice to the API
                time.sleep(0.5)

            except Exception as e:
                self.ui_queue.put(("error", f"Thread {self.thread_id}: {e}"))

        self.ui_queue.put(('done', self.thread_id))

    def check_batch(self, addresses_str, keys_dict):
        try:
            response = self.session.get(API_URL + addresses_str, timeout=10)
            response.raise_for_status() # Raise an exception for bad status codes
            data = response.json()

            for address, info in data.items():
                balance = info.get("final_balance", 0) / 1e8 # Convert from satoshi to BTC
                tx_count = info.get("n_tx", 0)
                wif = keys_dict.get(address)

                # Put result in queue for the UI
                result = (address, wif, tx_count, balance)
                self.ui_queue.put(('result', result))

                # Save only if it has a history or balance
                if tx_count > 0 or balance > 0:
                    self.ui_queue.put(('found', {'count': 1}))
                    with open("Found_Wallets.txt", "a") as f:
                        f.write(f"Address: {address}\n")
                        f.write(f"Private Key (WIF): {wif}\n")
                        f.write(f"TX Count: {tx_count}\n")
                        f.write(f"Balance: {balance:.8f} BTC\n")
                        f.write("-" * 40 + "\n")

        except requests.exceptions.RequestException as e:
            # Handle network errors gracefully
            print(f"API Request failed: {e}")
            pass
        except Exception as e:
            print(f"An error occurred in check_batch: {e}")


class BTCCheckerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("BTC Address Checker (Educational Tool)")
        self.root.geometry("950x600")

        self.ui_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.workers = []
        self.autoscroll_var = tk.BooleanVar(value=True) # <--- NEW: Variable for auto-scroll checkbox

        # Stats
        self.total_checked = 0
        self.total_found = 0
        self.start_time = 0
        
        self.setup_styles()
        self.setup_ui()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.process_queue()

    def setup_styles(self):
        # ... (style setup is unchanged)
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background='#f0f0f0')
        style.configure("TLabel", background='#f0f0f0', font=('Segoe UI', 10))
        style.configure("TButton", background='#0078d7', foreground='white', font=('Segoe UI', 10, 'bold'), borderwidth=0)
        style.map("TButton", background=[('active', '#005a9e'), ('disabled', '#a0a0a0')])
        style.configure("Treeview", rowheight=25, fieldbackground='white', font=('Segoe UI', 9))
        style.configure("Treeview.Heading", font=('Segoe UI', 10, 'bold'))
        style.map("Treeview", background=[('selected', '#b3d7ff')])
        style.configure("Found.Treeview", background='#dff0d8') # Greenish background for found items


    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.rowconfigure(1, weight=1)
        main_frame.columnconfigure(0, weight=1)

        # --- Controls Frame ---
        controls_frame = ttk.Frame(main_frame)
        controls_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        ttk.Label(controls_frame, text="Addresses to check:").pack(side=tk.LEFT, padx=(0, 5))
        self.count_var = tk.IntVar(value=10000)
        ttk.Entry(controls_frame, textvariable=self.count_var, width=12).pack(side=tk.LEFT, padx=(0, 15))

        ttk.Label(controls_frame, text="Threads:").pack(side=tk.LEFT, padx=(0, 5))
        self.threads_var = tk.IntVar(value=4)
        ttk.Spinbox(controls_frame, from_=1, to=20, textvariable=self.threads_var, width=5).pack(side=tk.LEFT, padx=(0, 15))

        self.start_btn = ttk.Button(controls_frame, text="Start", command=self.start_workers)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        self.stop_btn = ttk.Button(controls_frame, text="Stop", command=self.stop_workers, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT)

        # <--- NEW: Add the autoscroll checkbox to the right side of the controls
        autoscroll_check = ttk.Checkbutton(controls_frame, text="Auto-scroll", variable=self.autoscroll_var)
        autoscroll_check.pack(side=tk.RIGHT, padx=5)
        
        # --- Treeview Frame ---
        # ... (Treeview setup is unchanged)
        tree_frame = ttk.Frame(main_frame)
        tree_frame.grid(row=1, column=0, sticky="nsew")
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)
        self.tree = ttk.Treeview(tree_frame, columns=("Address", "WIF", "TXs", "Balance"), show="headings")
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.heading("Address", text="Address")
        self.tree.heading("WIF", text="Private Key (WIF)")
        self.tree.heading("TXs", text="TXs")
        self.tree.heading("Balance", text="Balance (BTC)")
        self.tree.column("Address", width=280, anchor='w')
        self.tree.column("WIF", width=350, anchor='w')
        self.tree.column("TXs", width=50, anchor='center')
        self.tree.column("Balance", width=120, anchor='e')
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        hsb.grid(row=1, column=0, sticky="ew")
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.tag_configure('found', background='#c8e6c9', foreground='black')

        # --- Status Frame ---
        # ... (Status frame setup is unchanged)
        status_frame = ttk.Frame(main_frame, padding=(5, 5))
        status_frame.grid(row=2, column=0, sticky="ew")
        self.progress = ttk.Progressbar(status_frame, orient='horizontal', mode='determinate')
        self.progress.pack(fill=tk.X, expand=True, pady=(5,0))
        stats_bar = ttk.Frame(status_frame)
        stats_bar.pack(fill=tk.X, expand=True)
        self.checked_label = ttk.Label(stats_bar, text="Checked: 0")
        self.checked_label.pack(side=tk.LEFT)
        self.found_label = ttk.Label(stats_bar, text="Found: 0")
        self.found_label.pack(side=tk.LEFT, padx=20)
        self.rate_label = ttk.Label(stats_bar, text="Rate: 0 addr/s")
        self.rate_label.pack(side=tk.RIGHT)
        
    def start_workers(self):
        # ... (start_workers method is unchanged)
        try:
            self.total_to_check = self.count_var.get()
            num_threads = self.threads_var.get()
            if self.total_to_check <= 0 or num_threads <= 0:
                messagebox.showerror("Error", "Please enter positive values for addresses and threads.")
                return
        except tk.TclError:
            messagebox.showerror("Error", "Please enter valid numbers.")
            return
        self.tree.delete(*self.tree.get_children())
        self.stop_event.clear()
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.total_checked = 0
        self.total_found = 0
        self.start_time = time.time()
        self.progress['maximum'] = self.total_to_check
        self.progress['value'] = 0
        self.update_status_bar()
        self.workers = []
        for i in range(num_threads):
            worker = Worker(i + 1, None, self.ui_queue, self.stop_event)
            self.workers.append(worker)
            worker.start()

    def stop_workers(self):
        # ... (stop_workers method is unchanged)
        self.stop_event.set()
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)

    def process_queue(self):
        try:
            for _ in range(100): 
                msg_type, data = self.ui_queue.get_nowait()
                
                if msg_type == 'result':
                    # --- THIS BLOCK IS MODIFIED ---
                    address, wif, tx_count, balance = data
                    tags = ()
                    if balance > 0 or tx_count > 0:
                        tags = ('found',)
                    
                    formatted_balance = f"{balance:.8f}"
                    # Insert the new row and get its unique ID
                    row_id = self.tree.insert("", tk.END, values=(address, wif, tx_count, formatted_balance), tags=tags) # <--- MODIFIED

                    # If autoscroll is enabled, move the view to the new row
                    if self.autoscroll_var.get(): # <--- NEW
                        self.tree.see(row_id) # <--- NEW

                elif msg_type == 'status':
                    self.total_checked += data['checked']
                    if self.total_checked >= self.total_to_check:
                        self.total_checked = self.total_to_check
                        self.stop_workers()
                    self.update_status_bar()
                
                elif msg_type == 'found':
                    self.total_found += data['count']
                    self.update_status_bar()

                elif msg_type == 'done':
                    if all(not w.is_alive() for w in self.workers):
                         self.stop_workers()

                elif msg_type == 'error':
                    messagebox.showwarning("Worker Error", data)

        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_queue)

    def update_status_bar(self):
        # ... (update_status_bar method is unchanged)
        elapsed_time = time.time() - self.start_time
        rate = self.total_checked / elapsed_time if elapsed_time > 0 else 0
        self.checked_label.config(text=f"Checked: {self.total_checked:,}/{self.total_to_check:,}")
        self.found_label.config(text=f"Found: {self.total_found}")
        self.rate_label.config(text=f"Rate: {rate:,.0f} addr/s")
        self.progress['value'] = self.total_checked
        
    def on_closing(self):
        # ... (on_closing method is unchanged)
        if self.workers and any(w.is_alive() for w in self.workers):
            if messagebox.askokcancel("Quit", "Workers are still running. Do you want to stop them and quit?"):
                self.stop_workers()
                self.root.destroy()
        else:
            self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = BTCCheckerApp(root)
    root.mainloop()
