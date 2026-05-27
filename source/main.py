import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import subprocess
import os
import sys

from core.database import create_tables
from core.queue_logic import (
    join_queue,
    call_next,
    mark_done,
    get_waiting,
    get_history,
    get_all_records,
    delete_record,
    clear_all_records,
    get_stats,
    edit_record,
)


class QueueSystemGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🏥 Queue Management System")
        self.root.geometry("900x650")
        self.root.resizable(True, True)

        self.server_process = None
        self.server_button = None

        style = ttk.Style()
        style.theme_use("clam")

        self.create_widgets()

    # ── Layout ────────────────────────────────────────────────
    def create_widgets(self):
        """Creates the main GUI layout."""
        # Header
        header = ttk.Frame(self.root)
        header.pack(fill=tk.X, padx=10, pady=10)
        ttk.Label(
            header, text="🏥 Queue Management System", font=("Arial", 24, "bold")
        ).pack(side=tk.LEFT)

        # Main content frame
        content = ttk.Frame(self.root)
        content.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left panel — Actions
        left_panel = ttk.LabelFrame(content, text="Actions", padding=10)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 10))

        button_width = 20
        ttk.Button(
            left_panel, text="➕ Join Queue", width=button_width,
            command=self.join_queue_dialog,
        ).pack(pady=5, fill=tk.X)
        ttk.Button(
            left_panel, text="📢 Call Next Customer", width=button_width,
            command=self.call_next_action,
        ).pack(pady=5, fill=tk.X)
        ttk.Button(
            left_panel, text="✅ Mark as Done", width=button_width,
            command=self.mark_done_action,
        ).pack(pady=5, fill=tk.X)
        ttk.Button(
            left_panel, text="✏️  Edit Record", width=button_width,
            command=self.edit_record_dialog,
        ).pack(pady=5, fill=tk.X)
        ttk.Button(
            left_panel, text="🗑️  Delete Record", width=button_width,
            command=self.delete_record_dialog,
        ).pack(pady=5, fill=tk.X)
        ttk.Button(
            left_panel, text="⚠️  Clear All Records", width=button_width,
            command=self.clear_all_records_dialog,
        ).pack(pady=5, fill=tk.X)

        ttk.Separator(left_panel, orient=tk.HORIZONTAL).pack(pady=10, fill=tk.X)

        self.server_button = ttk.Button(
            left_panel, text="🚀 Start Server", width=button_width,
            command=self.toggle_server,
        )
        self.server_button.pack(pady=5, fill=tk.X)

        ttk.Button(
            left_panel, text="🔄 Refresh", width=button_width,
            command=self.refresh_display,
        ).pack(pady=5, fill=tk.X)
        ttk.Button(
            left_panel, text="❌ Exit", width=button_width,
            command=self.root.destroy,
        ).pack(pady=5, fill=tk.X)

        # Right panel — tabbed display
        right_panel = ttk.Frame(content)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.notebook = ttk.Notebook(right_panel)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.waiting_text = self._make_tab("⏳ Waiting Queue", "Customers Waiting:")
        self.history_text = self._make_tab("📋 Full History", "All Records:")

        stats_frame = ttk.Frame(self.notebook)
        self.notebook.add(stats_frame, text="📊 Statistics")
        self.stats_text = tk.Text(stats_frame, height=20, width=60, font=("Courier", 10))
        self.stats_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.refresh_display()

    def _make_tab(self, tab_label, header_text):
        """Helper: creates a scrollable text tab and returns the Text widget."""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=tab_label)
        ttk.Label(frame, text=header_text, font=("Arial", 12, "bold")).pack(
            padx=10, pady=5, anchor=tk.W
        )
        scrollbar = ttk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget = tk.Text(
            frame, height=20, width=60,
            yscrollcommand=scrollbar.set, font=("Courier", 10),
        )
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        scrollbar.config(command=text_widget.yview)
        return text_widget

    def _format_priority(self, priority: int) -> str:
        if priority == 2:
            return "VIP"
        if priority == 1:
            return "Priority"
        return "Regular"

    # ── Actions ───────────────────────────────────────────────
    def join_queue_dialog(self):
        """Opens a dialog to add a new customer to the queue."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Join Queue")
        dialog.geometry("350x200")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="Customer name:").pack(padx=10, pady=(10, 2), anchor=tk.W)
        name_var = tk.StringVar()
        name_entry = ttk.Entry(dialog, textvariable=name_var, width=30)
        name_entry.pack(padx=10, pady=2, fill=tk.X)
        name_entry.focus_set()

        ttk.Label(dialog, text="Priority:").pack(padx=10, pady=(10, 2), anchor=tk.W)
        priority_var = tk.StringVar(value="Regular")
        priority_options = ("Regular", "Priority", "VIP")
        priority_combo = ttk.Combobox(
            dialog, textvariable=priority_var, values=priority_options, state="readonly"
        )
        priority_combo.pack(padx=10, pady=2, fill=tk.X)

        def submit():
            name = name_var.get().strip()
            if not name:
                messagebox.showwarning("Warning", "Name cannot be empty.")
                return
            priority_label = priority_var.get()
            priority_map = {"Regular": 0, "Priority": 1, "VIP": 2}
            priority = priority_map.get(priority_label, 0)
            try:
                ticket = join_queue(name, priority)
                messagebox.showinfo(
                    "Success", f"🎫 Welcome {name}!\nYour ticket is {ticket}"
                )
                self.refresh_display()
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to join queue: {e}")

        def cancel():
            dialog.destroy()

        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="Join", command=submit).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=cancel).pack(side=tk.LEFT, padx=5)

        dialog.bind("<Return>", lambda _event: submit())
        dialog.bind("<Escape>", lambda _event: cancel())

    def call_next_action(self):
        """Calls the next customer in the queue."""
        try:
            result = call_next()
            if result is None:
                messagebox.showinfo("Queue", "📭 No one is waiting in the queue.")
            else:
                ticket, name = result
                messagebox.showinfo("Now Serving", f"📢 Now serving: {name}\nTicket: {ticket}")
            self.refresh_display()
        except RuntimeError as e:
            messagebox.showwarning("Warning", f"⚠️  {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to call next customer: {e}")

    def mark_done_action(self):
        """Marks the current customer as done."""
        try:
            result = mark_done()
            if result is None:
                messagebox.showwarning("Warning", "⚠️  No customer is currently being served.")
            else:
                ticket, name = result
                messagebox.showinfo(
                    "Complete", f"✅ {name} (Ticket {ticket}) has been marked as done."
                )
            self.refresh_display()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to mark customer as done: {e}")

    def edit_record_dialog(self):
        """Opens a window listing records; the selected one can have its priority edited."""
        try:
            rows = get_all_records()
            if not rows:
                messagebox.showinfo("Edit", "📭 No records found.")
                return

            edit_window = tk.Toplevel(self.root)
            edit_window.title("Edit Record Priority")
            edit_window.geometry("500x450")
            edit_window.transient(self.root)
            edit_window.grab_set()
            ttk.Label(
                edit_window, text="Select a record to edit:",
                font=("Arial", 10, "bold"),
            ).pack(padx=10, pady=5)

            scrollbar = ttk.Scrollbar(edit_window)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            listbox = tk.Listbox(
                edit_window, yscrollcommand=scrollbar.set, font=("Courier", 9)
            )
            listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
            scrollbar.config(command=listbox.yview)

            record_ids = []
            for row in rows:
                record_id, ticket, name, status = row[:4]
                record_ids.append(record_id)
                listbox.insert(
                    tk.END, f"ID: {record_id}  |  {ticket}  |  {name}  |  {status.upper()}"
                )

            ttk.Label(edit_window, text="New Priority:").pack(padx=10, pady=(5, 2), anchor=tk.W)
            priority_var = tk.StringVar(value="Regular")
            priority_combo = ttk.Combobox(
                edit_window, textvariable=priority_var,
                values=("Regular", "Priority", "VIP"), state="readonly", width=20,
            )
            priority_combo.pack(padx=10, pady=2, anchor=tk.W)

            def save_selected():
                selection = listbox.curselection()
                if not selection:
                    messagebox.showwarning("Warning", "Please select a record to edit.")
                    return
                record_id = record_ids[selection[0]]
                priority_map = {"Regular": 0, "Priority": 1, "VIP": 2}
                priority = priority_map[priority_var.get()]
                try:
                    result = edit_record(record_id, priority)
                    if result is None:
                        messagebox.showwarning("Warning", "Record no longer exists.")
                    else:
                        ticket, name = result
                        messagebox.showinfo(
                            "Success",
                            f"✅ {name} ({ticket}) priority updated to {priority_var.get()}.",
                        )
                    self.refresh_display()
                    edit_window.destroy()
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to edit record: {e}")

            ttk.Button(
                edit_window, text="Save Changes", command=save_selected
            ).pack(pady=10)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open edit dialog: {e}")

    def delete_record_dialog(self):
        """Opens a window listing records; the selected one can be deleted."""
        try:
            rows = get_all_records()
            if not rows:
                messagebox.showinfo("Delete", "📭 No records found.")
                return

            delete_window = tk.Toplevel(self.root)
            delete_window.title("Delete Record")
            delete_window.geometry("500x400")
            ttk.Label(
                delete_window, text="Select a record to delete:",
                font=("Arial", 10, "bold"),
            ).pack(padx=10, pady=5)

            scrollbar = ttk.Scrollbar(delete_window)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            listbox = tk.Listbox(
                delete_window, yscrollcommand=scrollbar.set, font=("Courier", 9)
            )
            listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
            scrollbar.config(command=listbox.yview)

            record_ids = []
            for row in rows:
                record_id, ticket, name, status = row[:4]
                record_ids.append(record_id)
                listbox.insert(
                    tk.END, f"ID: {record_id}  |  {ticket}  |  {name}  |  {status.upper()}"
                )

            def delete_selected():
                selection = listbox.curselection()
                if not selection:
                    messagebox.showwarning("Warning", "Please select a record to delete.")
                    return
                record_id = record_ids[selection[0]]
                # Re-fetch from the database to avoid acting on stale data.
                fresh_rows = get_all_records()
                record_info = next(
                    ((t, n) for rid, t, n, s in fresh_rows if rid == record_id), None
                )
                if record_info is None:
                    messagebox.showwarning("Warning", "Record no longer exists.")
                    delete_window.destroy()
                    self.refresh_display()
                    return
                if messagebox.askyesno(
                    "Confirm", f"⚠️  Delete {record_info[0]} ({record_info[1]})?"
                ):
                    try:
                        delete_record(record_id)
                        messagebox.showinfo(
                            "Success",
                            f"✅ Record {record_info[0]} ({record_info[1]}) has been deleted.",
                        )
                        self.refresh_display()
                        delete_window.destroy()
                    except Exception as e:
                        messagebox.showerror("Error", f"Failed to delete record: {e}")

            ttk.Button(
                delete_window, text="Delete Selected", command=delete_selected
            ).pack(pady=10)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open delete dialog: {e}")

    def clear_all_records_dialog(self):
        """Confirms and clears all records."""
        try:
            rows = get_all_records()
            count = len(rows)
            if count == 0:
                messagebox.showinfo("Clear", "📭 No records to clear.")
                return
            if messagebox.askyesno(
                "Confirm",
                f"⚠️  WARNING: Delete ALL {count} records?\n\nThis action cannot be undone!",
            ):
                clear_all_records()
                messagebox.showinfo("Success", f"✅ All {count} records have been deleted.")
                self.refresh_display()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to clear records: {e}")

    # ── Display refresh ───────────────────────────────────────
    def toggle_server(self):
        """Start or stop the Flask server."""
        if self.server_process is None:
            self.start_server()
        else:
            self.stop_server()

    def start_server(self):
        """Start the Flask server in a subprocess."""
        try:
            # Get the path to server.py
            server_path = os.path.join(
                os.path.dirname(__file__), "api", "server.py"
            )

            # Start the server as a subprocess
            self.server_process = subprocess.Popen(
                [sys.executable, server_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            self.server_button.config(text="⏹️  Stop Server", style="")
            messagebox.showinfo(
                "Server Started", "✅ Flask server is running on http://0.0.0.0:5000"
            )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start server: {e}")

    def stop_server(self):
        """Stop the Flask server."""
        try:
            if self.server_process is not None:
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
                self.server_process = None
                self.server_button.config(text="🚀 Start Server")
                messagebox.showinfo("Server Stopped", "✅ Flask server has been stopped.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to stop server: {e}")
            if self.server_process is not None:
                self.server_process.kill()
                self.server_process = None

    def refresh_display(self):
        """Refreshes all tabs with current data from the database."""
        for widget in (self.waiting_text, self.history_text, self.stats_text):
            widget.config(state=tk.NORMAL)

        self.waiting_text.delete(1.0, tk.END)
        self.history_text.delete(1.0, tk.END)
        self.stats_text.delete(1.0, tk.END)
        try:
            # Waiting queue tab
            waiting_rows = get_waiting()
            if waiting_rows:
                self.waiting_text.insert(
                    tk.END, "--- 🕐 Waiting Queue ---\n\n"
                    "Ticket  |  Name  |  Priority  |  Created\n"
                    "----------------------------------------\n"
                )
                for row in waiting_rows:
                    ticket, name, created_at = row[:3]
                    priority = row[3] if len(row) > 3 else 0
                    priority_label = self._format_priority(priority)
                    self.waiting_text.insert(
                        tk.END,
                        f"{ticket}  |  {name}  |  {priority_label}  |  {created_at}\n",
                    )
                self.waiting_text.insert(tk.END, f"\nTotal waiting: {len(waiting_rows)}\n")
            else:
                self.waiting_text.insert(
                    tk.END, "📭 The queue is empty — no one is waiting.\n"
                )

            # History tab
            history_rows = get_history()
            if history_rows:
                self.history_text.insert(tk.END, "--- 📋 Full History ---\n\n")
                for row in history_rows:
                    ticket, name, status, created_at = row[:4]
                    self.history_text.insert(
                        tk.END, f"{ticket}  |  {name}  |  {status.upper()}  |  {created_at}\n"
                    )
                self.history_text.insert(
                    tk.END, f"\nTotal records: {len(history_rows)}\n"
                )
            else:
                self.history_text.insert(tk.END, "📭 No records found.\n")

            # Statistics tab
            s = get_stats()
            self.stats_text.insert(
                tk.END,
                f"--- 📊 STATISTICS ---\n\n"
                f"Waiting:     {s['waiting']}\n"
                f"Serving:     {s['serving']}\n"
                f"Done:        {s['done']}\n"
                f"──────────────────\n"
                f"Total:       {s['total']}\n",
            )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh display: {e}")
        finally:
            for widget in (self.waiting_text, self.history_text, self.stats_text):
                widget.config(state=tk.DISABLED)


def main():
    """Main entry point for the GUI."""
    create_tables()
    root = tk.Tk()
    app = QueueSystemGUI(root)

    def on_closing():
        """Handle graceful shutdown."""
        if app.server_process is not None:
            try:
                app.server_process.terminate()
                app.server_process.wait(timeout=3)
            except:
                app.server_process.kill()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
