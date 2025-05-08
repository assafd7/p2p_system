# main_app.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from files_index import FileListComponent
from p2p_protocol import P2PProtocol
import os
import threading

class MainApplication:
    def __init__(self, root, user_info):
        self.root = root
        self.username = user_info['username']
        self.root.title("P2P File Sharing System")
        self.root.geometry("800x600")
        
        # Initialize P2P protocol
        self.p2p = P2PProtocol(host='0.0.0.0', port=9001)
        
        # Create menu bar
        self.menu_bar = tk.Menu(root)
        self.root.config(menu=self.menu_bar)
        
        # File menu
        self.file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="File", menu=self.file_menu)
        self.file_menu.add_command(label="Upload File", command=self.upload_file)
        self.file_menu.add_command(label="Download File", command=self.download_file)
        self.file_menu.add_command(label="Search Files", command=self.search_files)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.on_closing)
        
        # Create main frame
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Welcome label
        self.welcome_label = ttk.Label(self.main_frame, text=f"Welcome, {self.username}!")
        self.welcome_label.grid(row=0, column=0, columnspan=2, pady=10)
        
        # Status frame
        self.status_frame = ttk.LabelFrame(self.main_frame, text="Network Status", padding="5")
        self.status_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        self.peer_count_label = ttk.Label(self.status_frame, text="Connected Peers: 0")
        self.peer_count_label.grid(row=0, column=0, padx=5)
        
        self.file_count_label = ttk.Label(self.status_frame, text="Shared Files: 0")
        self.file_count_label.grid(row=0, column=1, padx=5)
        
        # Refresh button
        self.refresh_button = ttk.Button(self.status_frame, text="Refresh", command=self.refresh_peers)
        self.refresh_button.grid(row=0, column=2, padx=5)
        
        # Shared files list
        self.files_frame = ttk.LabelFrame(self.main_frame, text="Shared Files", padding="5")
        self.files_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        # Create treeview with scrollbars
        self.tree_frame = ttk.Frame(self.files_frame)
        self.tree_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.tree_scroll = ttk.Scrollbar(self.tree_frame)
        self.tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.files_tree = ttk.Treeview(self.tree_frame, columns=("name", "hash", "peers"), 
                                      show="headings", yscrollcommand=self.tree_scroll.set)
        self.tree_scroll.config(command=self.files_tree.yview)
        
        self.files_tree.heading("name", text="File Name")
        self.files_tree.heading("hash", text="File Hash")
        self.files_tree.heading("peers", text="Available Peers")
        
        self.files_tree.column("name", width=200)
        self.files_tree.column("hash", width=200)
        self.files_tree.column("peers", width=100)
        
        self.files_tree.pack(fill=tk.BOTH, expand=True)
        
        # Bind double-click event
        self.files_tree.bind("<Double-1>", self.show_file_details)
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(2, weight=1)
        self.files_frame.columnconfigure(0, weight=1)
        self.files_frame.rowconfigure(0, weight=1)
        
        # Start periodic updates
        self.update_status()
        
        # Set closing handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def update_status(self):
        """Update the status display"""
        try:
            # Update peer count
            peer_count = len(self.p2p.peers)
            self.peer_count_label.config(text=f"Connected Peers: {peer_count}")
            
            # Update file count
            file_count = len(self.p2p.shared_files)
            self.file_count_label.config(text=f"Shared Files: {file_count}")
            
            # Update files list
            self.files_tree.delete(*self.files_tree.get_children())
            for file_hash, file_info in self.p2p.shared_files.items():
                self.files_tree.insert("", "end", values=(
                    file_info['name'],
                    file_hash,
                    len(file_info['peers'])
                ))
            
            # Schedule next update
            self.root.after(5000, self.update_status)
        except Exception as e:
            print(f"Error updating status: {e}")
            self.root.after(5000, self.update_status)

    def upload_file(self):
        """Upload a file to share"""
        file_path = filedialog.askopenfilename()
        if not file_path:
            return
        
        try:
            # Share the file using P2P protocol
            file_hash = self.p2p.share_file(file_path)
            messagebox.showinfo("Success", f"File shared successfully!\nHash: {file_hash}")
            
            # Refresh the file list
            self.refresh_shared_files()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to share file: {str(e)}")

    def download_file(self):
        """Handle file download"""
        selected_item = self.files_tree.selection()
        if not selected_item:
            messagebox.showwarning("Warning", "Please select a file to download")
            return
        
        item = self.files_tree.item(selected_item[0])
        file_hash = item['values'][1]
        original_name = item['values'][0]
        
        # Ask for save location and name
        save_path = filedialog.asksaveasfilename(
            initialfile=original_name,
            defaultextension=os.path.splitext(original_name)[1]
        )
        
        if save_path:
            try:
                save_name = os.path.basename(save_path)
                file_path = self.p2p.request_file(file_hash, save_name)
                messagebox.showinfo("Success", f"File downloaded successfully!\nSaved as: {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to download file: {str(e)}")

    def search_files(self):
        """Handle file search"""
        search_dialog = tk.Toplevel(self.root)
        search_dialog.title("Search Files")
        search_dialog.geometry("400x300")
        
        ttk.Label(search_dialog, text="Search by file name or hash:").pack(pady=10)
        
        search_entry = ttk.Entry(search_dialog, width=40)
        search_entry.pack(pady=5)
        
        results_tree = ttk.Treeview(search_dialog, columns=("name", "hash", "peers"), show="headings")
        results_tree.heading("name", text="File Name")
        results_tree.heading("hash", text="File Hash")
        results_tree.heading("peers", text="Available Peers")
        
        results_tree.column("name", width=150)
        results_tree.column("hash", width=150)
        results_tree.column("peers", width=100)
        
        results_tree.pack(pady=10, fill=tk.BOTH, expand=True)
        
        def perform_search():
            query = search_entry.get().lower()
            results_tree.delete(*results_tree.get_children())
            
            for file_hash, file_info in self.p2p.shared_files.items():
                if (query in file_info['name'].lower() or 
                    query in file_hash.lower()):
                    results_tree.insert("", "end", values=(
                        file_info['name'],
                        file_hash,
                        len(file_info['peers'])
                    ))
        
        search_button = ttk.Button(search_dialog, text="Search", command=perform_search)
        search_button.pack(pady=5)
        
        def on_double_click(event):
            selected_item = results_tree.selection()
            if selected_item:
                item = results_tree.item(selected_item[0])
                file_hash = item['values'][1]
                original_name = item['values'][0]
                
                save_path = filedialog.asksaveasfilename(
                    initialfile=original_name,
                    defaultextension=os.path.splitext(original_name)[1]
                )
                
                if save_path:
                    try:
                        save_name = os.path.basename(save_path)
                        file_path = self.p2p.request_file(file_hash, save_name)
                        messagebox.showinfo("Success", f"File downloaded successfully!\nSaved as: {file_path}")
                    except Exception as e:
                        messagebox.showerror("Error", f"Failed to download file: {str(e)}")
        
        results_tree.bind("<Double-1>", on_double_click)
    
    def show_file_details(self, event):
        """Show file details dialog"""
        selected_item = self.files_tree.selection()
        if not selected_item:
            return
        
        item = self.files_tree.item(selected_item[0])
        file_name = item['values'][0]
        file_hash = item['values'][1]
        peer_count = item['values'][2]
        
        details_dialog = tk.Toplevel(self.root)
        details_dialog.title("File Details")
        details_dialog.geometry("400x200")
        
        ttk.Label(details_dialog, text=f"File Name: {file_name}").pack(pady=5)
        ttk.Label(details_dialog, text=f"File Hash: {file_hash}").pack(pady=5)
        ttk.Label(details_dialog, text=f"Available Peers: {peer_count}").pack(pady=5)
        
        def download_file():
            details_dialog.destroy()
            save_path = filedialog.asksaveasfilename(
                initialfile=file_name,
                defaultextension=os.path.splitext(file_name)[1]
            )
            
            if save_path:
                try:
                    save_name = os.path.basename(save_path)
                    file_path = self.p2p.request_file(file_hash, save_name)
                    messagebox.showinfo("Success", f"File downloaded successfully!\nSaved as: {file_path}")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to download file: {str(e)}")
        
        ttk.Button(details_dialog, text="Download", command=download_file).pack(pady=10)
    
    def refresh_peers(self):
        """Refresh the list of connected peers"""
        try:
            self.p2p.discover_peers()
            self.update_status()
            messagebox.showinfo("Success", "Peer list refreshed successfully")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh peers: {str(e)}")
    
    def refresh_shared_files(self):
        """Refresh the list of shared files"""
        try:
            self.update_status()
            messagebox.showinfo("Success", "File list refreshed successfully")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh files: {str(e)}")
    
    def on_closing(self):
        """Handle application closing"""
        try:
            self.p2p.stop()
            self.root.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Error during shutdown: {str(e)}")
            self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = MainApplication(root, "Test User")
    root.mainloop()
