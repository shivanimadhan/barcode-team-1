import tkinter as tk
from tkinter import ttk, filedialog

def create_popup(parent, description, row, title_label):
    """Helper to create a popup window describing the feature and place the icon."""
    info_icon = tk.Label(parent, text="ℹ️", font=("Arial", 12), bg=parent.winfo_toplevel().cget("bg"), fg="blue", relief="flat", borderwidth=0)
    info_icon.grid(row=row, column=0, sticky="w", padx=(title_label.winfo_reqwidth() + 30, 0))

    def show_popup(event):
        # Create popup
        popup = tk.Label(parent, text=description, bg="#202020", fg="white", relief="flat", borderwidth=4, wraplength=600)
        popup.place(x=info_icon.winfo_rootx() - parent.winfo_rootx() + info_icon.winfo_width() + 10, y=info_icon.winfo_rooty() - parent.winfo_rooty() - 20)
        popup.tkraise()

        def hide_popup(event):
            popup.destroy()  # Destroy popup
        info_icon.bind("<Leave>", hide_popup)

    info_icon.bind("<Enter>", show_popup)

def create_option_section(parent, row, var, title, description):
    """Helper to create option sections with a checkbox, description, and a popup icon."""
    tk.Checkbutton(parent, variable=var).grid(row=row, column=0, sticky="w", padx=5)

    normal = ("TkDefaultFont", 13)

    title_label = tk.Label(parent, text=title, font=normal)
    title_label.grid(row=row, column=0, sticky="w", padx=(25, 5))

    # Call the popup creation function to create and place the info icon
    create_popup(parent, description, row, title_label)