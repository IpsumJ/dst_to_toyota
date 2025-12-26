#!/usr/bin/env python
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import serial
import threading
import serial.tools.list_ports
from embfile import EmbFile
from toyotacom import ToyotaCom
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure



class DSTSenderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DST File Sender")

        self.dst_data = None
        self.emb = None
        self.tcom = None
        self.sending_thread = None
        self.stop_poll = True
        self.colors = 0
        self.selected_port = tk.StringVar()
        self.send_button = None

        self.setup_ui()

    def setup_ui(self):
        # === Controlls ===
        control_frame = tk.Frame(self.root)
        control_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)

        control_frame.columnconfigure(2, weight=1)

        tk.Button(control_frame, text="Load DST File", command=self.load_dst_file).grid(
            row=0, column=0, padx=5, pady=5
        )

        tk.Label(control_frame, text="Select Port:").grid(row=0, column=1, padx=5, pady=5)
        self.port_menu = ttk.Combobox(control_frame, textvariable=self.selected_port, width=20)
        self.refresh_ports()
        self.port_menu.grid(row=0, column=2, padx=5, pady=5)

        tk.Button(control_frame, text="Refresh", command=self.refresh_ports).grid(row=0, column=3, padx=5, pady=5)
        self.send_button = tk.Button(control_frame, text="Send via Serial", command=self.send_via_serial)
        self.send_button.grid(row=0, column=4, padx=10, pady=5)
        self.send_button.config(state=tk.DISABLED)

        # === Progress Bar ===
        progress_frame = tk.Frame(self.root)
        progress_frame.grid(row=1, column=0, sticky="ew", padx=10)
        tk.Label(progress_frame, text="Progress:").pack(side="left", padx=5)
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            progress_frame, variable=self.progress_var, maximum=100, length=400
        )
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=5, pady=5)

        # === Plotting Frame ===
        plot_frame = tk.LabelFrame(self.root, text="DST Preview")
        plot_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=10)
        plot_frame.columnconfigure(0, weight=1)
        plot_frame.rowconfigure(0, weight=1)

        self.fig = Figure(figsize=(5, 5))
        self.ax = self.fig.add_subplot(111)
        self.ax.set_title("No file loaded")
        self.ax.axis("off")

        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

    def get_com_ports(self):
        ports = [port.device for port in serial.tools.list_ports.comports()]
        return ports if ports else ["No ports found"]

    def refresh_ports(self):
        ports = self.get_com_ports()
        self.port_menu['values'] = ports
        if ports:
            self.selected_port.set(ports[-1])

    def load_dst_file(self):
        file_path = filedialog.askopenfilename(
            title="Select DST File",
            filetypes=[("DST embroidery files", "*.dst"), ("All files", "*.*")]
        )

        if not file_path:
            return

        try:
            with open(file_path, "rb") as f:
                self.dst_data = f.read()

            self.emb = EmbFile()
            self.emb.load_dst(self.dst_data)
            self.update_plot()
            messagebox.showinfo("Success", f"Loaded and converted:\n{file_path}")
            self.send_button.config(state=tk.NORMAL)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file:\n{e}")

    def update_plot(self):
        self.ax.clear()
        if self.emb is not None:
            self.emb.plot(self.ax)
        self.ax.axis("equal")
        self.canvas.draw()

    def send_via_serial(self):
        self.send_button.config(state=tk.DISABLED)
        port = self.selected_port.get()
        if not port or "No ports" in port:
            messagebox.showwarning("Warning", "No port selected.")
            return
        if self.emb is None:
            messagebox.showwarning("Warning", "Please load and convert a DST file first.")
            return

        self.progress_var.set(0)
        self.stop_poll = False
        self.tcom = ToyotaCom(port)

        self.sending_thread = threading.Thread(target=self._send_thread, daemon=True)
        self.sending_thread.start()

        self.poll_progress()

    def _send_thread(self):
        try:
            self.tcom.send(self.emb.to10o(), self.emb.colors)
            self.tcom.close()
            # Mark complete
            self.progress_var.set(100)
            self.stop_poll = True
            self.root.after(0, lambda: messagebox.showinfo("Success", f"File sent successfully."))
        except Exception as e:
            self.stop_poll = True
            print(e)
            self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to send data."))

    def poll_progress(self):
        if self.tcom and not self.stop_poll:
            try:
                progress = self.tcom.progress()
                self.progress_var.set(progress * 100)
            except Exception as e:
                print(e)
            self.root.after(200, self.poll_progress)
        else:
            self.send_button.config(state=tk.NORMAL)

if __name__ == "__main__":
    root = tk.Tk()
    app = DSTSenderApp(root)
    root.mainloop()
