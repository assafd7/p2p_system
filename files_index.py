import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from p2p_protocol import P2PProtocol


class FileListComponent(ttk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        # Current directory for browsing
        self.current_directory = os.path.expanduser("~")
        self.files = []

        # Create main frame
        self.main_frame = ttk.Frame(self, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Create header with current path and browse button
        self.path_frame = ttk.Frame(self.main_frame)
        self.path_frame.pack(fill=tk.X, pady=(0, 10))

        self.path_label = ttk.Label(self.path_frame, text="Current Directory:")
        self.path_label.pack(side=tk.LEFT, padx=(0, 5))

        self.path_var = tk.StringVar(value=self.current_directory)
        self.path_entry = ttk.Entry(self.path_frame, textvariable=self.path_var, width=50)
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        self.browse_button = ttk.Button(self.path_frame, text="Browse", command=self.browse_directory)
        self.browse_button.pack(side=tk.RIGHT)

        # Create search frame
        self.search_frame = ttk.Frame(self.main_frame)
        self.search_frame.pack(fill=tk.X, pady=(0, 10))

        self.search_label = ttk.Label(self.search_frame, text="Search:")
        self.search_label.pack(side=tk.LEFT, padx=(0, 5))

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self.filter_files)
        self.search_entry = ttk.Entry(self.search_frame, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Create file list with scrollbar
        self.list_frame = ttk.Frame(self.main_frame)
        self.list_frame.pack(fill=tk.BOTH, expand=True)

        self.columns = ('filename', 'size', 'type', 'status')
        self.file_list = ttk.Treeview(self.list_frame, columns=self.columns, show='headings')

        # Define headings
        self.file_list.heading('filename', text='Filename')
        self.file_list.heading('size', text='Size')
        self.file_list.heading('type', text='Type')
        self.file_list.heading('status', text='Status')

        # Define columns
        self.file_list.column('filename', width=250)
        self.file_list.column('size', width=100)
        self.file_list.column('type', width=100)
        self.file_list.column('status', width=100)

        # Add scrollbars
        self.scrollbar_y = ttk.Scrollbar(self.list_frame, orient=tk.VERTICAL, command=self.file_list.yview)
        self.file_list.configure(yscroll=self.scrollbar_y.set)

        self.scrollbar_x = ttk.Scrollbar(self.list_frame, orient=tk.HORIZONTAL, command=self.file_list.xview)
        self.file_list.configure(xscroll=self.scrollbar_x.set)

        # Pack elements
        self.file_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)

        # Button frame
        self.button_frame = ttk.Frame(self.main_frame)
        self.button_frame.pack(fill=tk.X, pady=(10, 0))

        self.refresh_button = ttk.Button(self.button_frame, text="Refresh", command=self.refresh_files)
        self.refresh_button.pack(side=tk.LEFT, padx=(0, 5))

        self.open_button = ttk.Button(self.button_frame, text="Open", command=self.open_file)
        self.open_button.pack(side=tk.LEFT, padx=(0, 5))

        self.share_button = ttk.Button(self.button_frame, text="Share", command=self.share_file)
        self.share_button.pack(side=tk.LEFT)

        # Context menu
        self.context_menu = tk.Menu(self.winfo_toplevel(), tearoff=0)
        self.context_menu.add_command(label="Open", command=self.open_file)
        self.context_menu.add_command(label="Share", command=self.share_file)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Copy Path", command=self.copy_path)

        # Bind events
        self.file_list.bind("<Double-1>", lambda e: self.open_file())
        self.file_list.bind("<Button-3>", self.show_context_menu)

        # Initialize the file list
        self.refresh_files()

    def browse_directory(self):
        """Open directory browser and update current directory"""
        directory = filedialog.askdirectory(initialdir=self.current_directory)
        if directory:
            self.current_directory = directory
            self.path_var.set(directory)
            self.refresh_files()

    def refresh_files(self):
        """Refresh the file list from the current directory"""
        # Clear the current list
        for item in self.file_list.get_children():
            self.file_list.delete(item)

        try:
            # Get all files in the directory
            self.files = []
            for item in os.listdir(self.current_directory):
                item_path = os.path.join(self.current_directory, item)
                try:
                    # Get file information
                    size = os.path.getsize(item_path)
                    # Format size
                    if size < 1024:
                        size_str = f"{size} B"
                    elif size < 1024 * 1024:
                        size_str = f"{size / 1024:.1f} KB"
                    elif size < 1024 * 1024 * 1024:
                        size_str = f"{size / (1024 * 1024):.1f} MB"
                    else:
                        size_str = f"{size / (1024 * 1024 * 1024):.1f} GB"

                    # Determine type
                    if os.path.isdir(item_path):
                        type_str = "Folder"
                    else:
                        # Get file extension
                        _, ext = os.path.splitext(item)
                        type_str = ext[1:].upper() if ext else "File"

                    # Check if file is shared
                    status = "Local"
                    if hasattr(self.master, 'p2p') and item_path in self.master.p2p.local_files.values():
                        status = "Shared"

                    self.files.append((item, size_str, type_str, status, item_path))

                except (FileNotFoundError, PermissionError):
                    # Skip files we can't access
                    continue

            # Apply any current filter
            self.filter_files()

        except (FileNotFoundError, PermissionError) as e:
            messagebox.showerror("Error", f"Could not access directory: {str(e)}")

    def filter_files(self, *args):
        """Filter files based on search text"""
        # Clear the current list
        for item in self.file_list.get_children():
            self.file_list.delete(item)

        search_text = self.search_var.get().lower()

        # Add matching files to the list
        for file_info in self.files:
            filename, size, file_type, status, _ = file_info
            if search_text in filename.lower():
                self.file_list.insert('', tk.END, values=(filename, size, file_type, status))

    def open_file(self):
        """Open the selected file or navigate to the selected directory"""
        selected_item = self.file_list.selection()
        if not selected_item:
            return

        # Get the filename of the selected item
        filename = self.file_list.item(selected_item, 'values')[0]
        file_path = os.path.join(self.current_directory, filename)

        if os.path.isdir(file_path):
            # If it's a directory, navigate to it
            self.current_directory = file_path
            self.path_var.set(file_path)
            self.refresh_files()
        else:
            # If it's a file, try to open it with the default application
            try:
                import subprocess
                if os.name == 'nt':  # Windows
                    os.startfile(file_path)
                elif os.name == 'posix':  # macOS, Linux
                    subprocess.call(('xdg-open', file_path))
            except Exception as e:
                messagebox.showerror("Error", f"Could not open file: {str(e)}")

    def share_file(self):
        """Share the selected file using P2P protocol"""
        selected_item = self.file_list.selection()
        if not selected_item:
            messagebox.showinfo("Info", "Please select a file to share")
            return

        filename = self.file_list.item(selected_item, 'values')[0]
        file_path = os.path.join(self.current_directory, filename)

        if not hasattr(self.master, 'p2p'):
            messagebox.showerror("Error", "P2P protocol not initialized")
            return

        try:
            # Share the file using P2P protocol
            file_hash = self.master.p2p.share_file(file_path)
            messagebox.showinfo("Share File", f"File shared successfully!\nHash: {file_hash}")
            self.refresh_files()  # Update the status
        except Exception as e:
            messagebox.showerror("Error", f"Failed to share file: {str(e)}")

    def copy_path(self):
        """Copy the path of the selected file to clipboard"""
        selected_item = self.file_list.selection()
        if not selected_item:
            return

        filename = self.file_list.item(selected_item, 'values')[0]
        file_path = os.path.join(self.current_directory, filename)

        # Copy to clipboard
        self.winfo_toplevel().clipboard_clear()
        self.winfo_toplevel().clipboard_append(file_path)
        messagebox.showinfo("Info", "Path copied to clipboard")

    def show_context_menu(self, event):
        """Show context menu on right click"""
        selected_item = self.file_list.identify_row(event.y)
        if selected_item:
            self.file_list.selection_set(selected_item)
            self.context_menu.post(event.x_root, event.y_root)


# Example usage in a parent application:
class MainApplication(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("P2P File Sharing")
        self.geometry("800x600")

        # Main content frame
        self.content_frame = ttk.Frame(self)
        self.content_frame.pack(fill=tk.BOTH, expand=True)

        # Create a button to toggle file list
        self.toggle_button = ttk.Button(self.content_frame, text="Toggle File Browser", command=self.toggle_file_list)
        self.toggle_button.pack(pady=10)

        # Create a container frame for the file list
        self.file_list_container = ttk.Frame(self.content_frame)
        self.file_list_container.pack(fill=tk.BOTH, expand=True)

        # Create the file list component
        self.file_list = FileListComponent(self.file_list_container)
        self.file_list.pack(fill=tk.BOTH, expand=True)

        # Initially visible
        self.file_list_visible = True

    def toggle_file_list(self):
        if self.file_list_visible:
            self.file_list.pack_forget()
            self.toggle_button.configure(text="Show File Browser")
        else:
            self.file_list.pack(fill=tk.BOTH, expand=True)
            self.toggle_button.configure(text="Hide File Browser")
        self.file_list_visible = not self.file_list_visible


# Standalone testing
if __name__ == "__main__":
    app = MainApplication()
    app.mainloop()