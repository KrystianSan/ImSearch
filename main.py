import tkinter as tk
import os, sys
import hashlib
import cv2
from pathlib import Path
import time
from tkinter.ttk import *
from tkinter import filedialog, messagebox, ttk, simpledialog, Menu
import pandas as pd
import threading
import numpy as np
from PIL import Image, ImageTk, UnidentifiedImageError
from skimage.metrics import structural_similarity
import csv

from concurrent.futures import ThreadPoolExecutor, as_completed


import torch
import torch.nn as nn
import torchvision.models as models
import torchvision.transforms as transforms
from torchvision.models import ResNet18_Weights


def calculate_image_hash(image_path):
    """Full file hash for final verification"""
    hasher = hashlib.sha256()
    with open(image_path, 'rb') as f:
        while chunk := f.read(131072):  # 128KB chunks
            hasher.update(chunk)
    return hasher.hexdigest()

def calculate_histogram(image):
    hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    h_hist = cv2.calcHist([hsv_image], [0], None, [256], [0, 256])
    return h_hist

def compare_histograms(hist1, hist2):
    intersection = cv2.compareHist(hist1, hist2, cv2.HISTCMP_INTERSECT)
    similarity = (intersection / (hist1.sum() + hist2.sum() - intersection)) * 100
    return similarity

VECTOR_ROOT = Path("vector_db")
VECTOR_FILE = "vectors.npy"
METADATA_FILE = "metadata.csv"


class FeatureExtractor:
    def __init__(self):
        self.weights = ResNet18_Weights.IMAGENET1K_V1
        self.model = models.resnet18(weights=self.weights)
        self.model = torch.nn.Sequential(*list(self.model.children())[:-1])  # Output: 512-dim vectors
        self.model.eval()
        self.transform = self.weights.transforms()

    def extract(self, image_path):
        try:
            img_bytes = np.fromfile(str(image_path), dtype=np.uint8)
            img = cv2.imdecode(img_bytes, cv2.IMREAD_COLOR)
            if img is None:
                return None
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            img_pil = Image.fromarray(img)
            img_tensor = self.transform(img_pil).unsqueeze(0)

            with torch.no_grad():
                features = self.model(img_tensor)

            features = features.squeeze().numpy()
            return features / np.linalg.norm(features)  # L2-normalize
        except Exception as e:
            print(f"Error processing {image_path.name}: {str(e)}")
            return None

class ImSearch:
    def __init__(self, root):
        self.subfolders = tk.IntVar()
        self.time = tk.IntVar()
        self.stop_search_flag = threading.Event()
        self.search_thread = None

        self.root = root
        self.root.title("ImSearch")
        self.root.geometry("1366x768")
        root.columnconfigure(0, weight=1)
        root.columnconfigure(1, weight=1)
        root.columnconfigure(2, weight=1)
        root.rowconfigure(0, weight=0)
        root.rowconfigure(1, weight=1)
        root.rowconfigure(2, weight=0)

        self.folder_count = 0
        self.folder_path = None
        self.query_image = None
        self.target_image_path = None
        self.include_subfolders = None
        self.files_list = []
        self.added_folders = []
        self.analyzed_files_count = 0

        self.quick_hash_cache = {}

        self.vector_extractor = FeatureExtractor()
        self.vectors = []

        self.duplicate_groups = {}

        self.feature_cache = {}  # {file: (kp, des)}
        self.cache_version = "1.0"

        self.sift = self._initialize_sift()

        self.current_language = "English"

        self.languages = {
            "English": {
                "add_folder": "Add Folder",
                "remove_folder": "Remove Folder",
                "folder_up": "Priority up",
                "folder_down": "Priority down",
                "upload_image": "Upload Query Image",
                "search_mode": "Choose search mode",
                "search_settings": "Choose search settings",
                "similarity_threshold": "Similarity threshold",
                "delete_selected": "Delete Selected",
                "search_subfolders": "Search subfolders",
                "language": "Language",
                "start_search": "Start search",
                "stop_search": "Stop search"
            },
            "Spanish": {
                "add_folder": "Agregar Carpeta",
                "remove_folder": "Eliminar Carpeta",
                "folder_up": "Prioridad arriba",
                "folder_down": "Prioridad abajo",
                "upload_image": "Subir Imagen de Consulta",
                "search_mode": "Elija el modo de búsqueda",
                "search_settings": "Elija la configuración de búsqueda",
                "similarity_threshold": "Umbral de similitud",
                "delete_selected": "Eliminar Seleccionado",
                "search_subfolders": "Buscar en subcarpetas",
                "language": "Idioma",
                "start_search": "Iniciar búsqueda",
                "stop_search": "Detener la búsqueda"
            }
            # Additional languages can be added here.
        }

        menubar = Menu(root)
        root.config(menu=menubar)

        settings_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Settings", menu=settings_menu)

        language_menu = Menu(settings_menu, tearoff=0)
        for language in self.languages.keys():
            language_menu.add_command(label=language, command=lambda lang=language: self.change_language(lang))
        settings_menu.add_cascade(label=self.languages[self.current_language]["language"], menu=language_menu)


        folders_frame = Frame(root)
        #folders_frame.columnconfigure(weight=1)
        folders_frame.grid(row=0, column=0, sticky="news", columnspan=3)
        folders_frame.rowconfigure(0, weight=1)
        folders_frame.rowconfigure(1, weight=1)
        folders_frame.rowconfigure(2, weight=1)

        folders_frame.columnconfigure(0, weight=1)
        folders_frame.columnconfigure(1, weight=5)
        folders_frame.columnconfigure(2, weight=1)


        search_frame = Frame(root)
        search_frame.grid(row=1, column=1, sticky="new")

        results_frame = Frame(root)
        results_frame.grid(row=2, column=0, sticky="news", columnspan=3)


        self.canvas_uploaded = tk.Canvas(root, bg="white", relief=tk.SUNKEN, borderwidth=1)
        #self.canvas_uploaded.place(x=12, y=96, height=535, width=428)

        self.canvas_selected = tk.Canvas(root, bg="white", relief=tk.SUNKEN, borderwidth=1)
        #self.canvas_selected.place(x=926, y=96, height=535, width=428)

        self.canvas_uploaded.grid(row=1, column=0, sticky="news")
        self.canvas_selected.grid(row=1, column=2, sticky="news")

        self.folders_listbox = tk.Listbox(folders_frame, selectmode=tk.SINGLE)
        #self.folders_listbox.place(x=166, y=10, height=80, width=1034)
        self.folders_listbox.grid(row=0, column=1, sticky="nsew", padx=5, pady=5, rowspan=2)

        # folder button
        self.add_folder_button = ttk.Button(folders_frame, text=self.languages[self.current_language]["add_folder"],
                                            command=self.add_folder)
        #self.add_folder_button.place(x=1212, y=50, height=40, width=140)
        self.add_folder_button.grid(row=1, column=2, sticky="nsew", padx=5, pady=5)

        self.remove_folder_button = ttk.Button(folders_frame, text=self.languages[self.current_language]["remove_folder"],
                                               command=self.remove_folder)
        #self.remove_folder_button.place(x=1212, y=10, height=40, width=140)
        self.remove_folder_button.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)

        self.folder_up_button = ttk.Button(folders_frame, text=self.languages[self.current_language]["folder_up"],
                                           command=self.move_up)
        #self.folder_up_button.place(x=14, y=10, height=40, width=140)
        self.folder_up_button.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        self.folder_down_button = ttk.Button(folders_frame, text=self.languages[self.current_language]["folder_down"],
                                             command=self.move_down)
        #self.folder_down_button.place(x=14, y=50, height=40, width=140)
        self.folder_down_button.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        # select image button
        self.upload_image_button = ttk.Button(search_frame, text=self.languages[self.current_language]["upload_image"], command=self.upload_query_image)
        #self.upload_image_button.place(x=496, y=122, height=52, width=374)
        self.upload_image_button.pack()
        # selected image label
        # self.target_image_label = ttk.Label(root, text="Selected Target Image: None")
        # self.target_image_label.place(x=64, y=720)

        # self.search_mode_label = ttk.Label(search_frame, text=self.languages[self.current_language]["search_mode"])
        # #self.search_mode_label.place(x=496, y=200)
        # self.search_mode_label.pack()
        # self.search_settings_label = ttk.Label(search_frame, text=self.languages[self.current_language]["search_settings"])
        # #self.search_settings_label.place(x=496, y=240)
        # self.search_settings_label.pack()
        self.similarity_threshold_label = ttk.Label(search_frame, text=self.languages[self.current_language]["similarity_threshold"])
        #self.similarity_threshold_label.place(x=496, y=280)
        self.similarity_threshold_label.pack()

        self.sim = tk.Spinbox(search_frame, from_=0, to=100)
        # Change default similarity threshold
        self.sim.delete(0, "end")
        self.sim.insert(0, "50")
        self.sim.pack()

        #self.sim.place(x=650, y=282, height=20, width=32)
        #tk.Label(search_frame, text="%", fg="black").place(x=682, y=283, height=20, width=10)
        tk.Label(search_frame, text="%", fg="black").pack()


        self.search_combobox = ttk.Combobox(search_frame, values=["Vector Similarity", "Histogram Similarity", "Find Duplicates", "Duplicate Pairs", "SSIM Compare", "SIFT Compare"], state="readonly")
        #self.search_combobox.place(x=650, y=192, height=34, width=220)
        self.search_combobox.pack()

        self.search_combobox.current(0)

        self.start_search_button = ttk.Button(search_frame, text=self.languages[self.current_language]["start_search"], command=self.run_search)
        #self.start_search_button.place(x=710, y=280, height=34, width=160)
        self.start_search_button.pack()

        self.stop_search_button = ttk.Button(search_frame, text=self.languages[self.current_language]["stop_search"], command=self.stop_search)
        #self.stop_search_button.place(x=710, y=324, height=34, width=160)
        self.stop_search_button.pack()
        self.stop_search_button.config(state=tk.DISABLED)

        self.subfolder_button = ttk.Checkbutton(search_frame, text=self.languages[self.current_language]["search_subfolders"], variable=self.subfolders,
                                                onvalue=1, offvalue=0)
        #self.subfolder_button.place(x=650, y=243)
        self.subfolder_button.pack()

        self.reprocess_button = ttk.Button(search_frame, text="Reprocess Folders", command=self.reprocess_folders)
        self.reprocess_button.pack()
        # select image button
        # self.upload_image_button = ttk.Button(root, text=self.languages[self.current_language]["upload_image"],
        #                                       command=self.upload_query_image)
        # self.upload_image_button.place(x=496, y=122, height=52, width=374, anchor="w")
        #
        # # selected image label
        # self.target_image_label = ttk.Label(root, text="Selected Target Image: None")
        # self.target_image_label.place(x=64, y=720, anchor="center")
        #
        # self.search_mode_label = ttk.Label(root, text=self.languages[self.current_language]["search_mode"])
        # self.search_mode_label.place(x=496, y=200, anchor="center")
        #
        # self.search_settings_label = ttk.Label(root, text=self.languages[self.current_language]["search_settings"])
        # self.search_settings_label.place(x=496, y=240, anchor="center")
        #
        # self.similarity_threshold_label = ttk.Label(root,
        #                                             text=self.languages[self.current_language]["similarity_threshold"])
        # self.similarity_threshold_label.place(x=496, y=280, anchor="center")
        #
        # self.sim = tk.Spinbox(self.root, from_=0, to=100)
        # self.sim.delete(0, "end")
        # self.sim.insert(0, "50")
        # self.sim.place(x=650, y=282, height=20, width=32, anchor="center")
        # tk.Label(self.root, text="%", fg="black").place(x=682, y=283, height=20, width=10, anchor="center")
        #
        # self.search_combobox = ttk.Combobox(root, values=["Find Similar", "Find Duplicates", "Duplicate Pairs",
        #                                                   "SSIM Compare"], state="readonly")
        # self.search_combobox.place(x=650, y=192, height=34, width=220, anchor="center")
        # self.search_combobox.current(0)
        #
        # self.start_search_button = ttk.Button(root, text=self.languages[self.current_language]["start_search"],
        #                                       command=self.run_search)
        # self.start_search_button.place(x=710, y=280, height=34, width=160, anchor="center")
        #
        # self.stop_search_button = ttk.Button(self.root, text=self.languages[self.current_language]["stop_search"],
        #                                      command=self.stop_search)
        # self.stop_search_button.place(x=710, y=324, height=34, width=160, anchor="center")
        # self.stop_search_button.config(state=tk.DISABLED)
        #
        # self.subfolder_button = ttk.Checkbutton(self.root,
        #                                         text=self.languages[self.current_language]["search_subfolders"],
        #                                         variable=self.subfolders,
        #                                         onvalue=1, offvalue=0)
        # self.subfolder_button.place(x=650, y=243, anchor="center")


        tree_frame = Frame(root)
        #tree_frame.pack(side="right", fill="y", pady=1, padx=1)
        # self.tree.heading("#0", text="Duplicate Group")
        # self.tree.heading("File Path", text="File Path")
        # self.tree = ttk.Treeview(
        #     results_frame,
        #     columns=("File 1", "File 2"),
        #     show="tree headings",  # For group nodes, use show="tree headings"
        #     height=10
        # )
        # self.tree.heading("File 1", text="Primary File")
        # self.tree.heading("File 2", text="Duplicate File")\
        # self.tree = ttk.Treeview(
        #     results_frame,
        #     columns=("File 1", "File 2"),
        #     show="headings",  # For group nodes, use show="tree headings"
        #     height=8
        # )
        # self.tree.heading("File 1", text="Primary File")
        # self.tree.heading("File 2", text="Duplicate File")
        self.tree = ttk.Treeview(results_frame, columns=("path", "similarity"), show="headings", height=8, selectmode="browse")
        verscrlbar = ttk.Scrollbar(results_frame,
                                   orient="vertical",
                                   command=self.tree.yview)
        verscrlbar.pack(side="right", fill="y", pady=1, padx=1)
        self.tree.configure(yscrollcommand=verscrlbar.set)
        self.tree.heading("path", text="Image path")
        self.tree.heading("similarity", text="Similarity (%)")
        self.tree.column("path")
        self.tree.column("similarity")
        #self.tree.place(x=0, y=0, height=100, width=1340)
        self.tree.pack(padx=10, pady=10, fill=tk.BOTH)
        #tree_frame.place(x=14, y=640, height=100, width=1340)
        #tree_frame.grid
        self.tree.bind("<<TreeviewSelect>>", self.display_selected)

        # Status Bar with Progress Bar
        self.status = tk.StringVar()
        self.status.set("Ready")
        self.status_bar = ttk.Label(results_frame, textvariable=self.status, relief=tk.SUNKEN, anchor='w')
        #self.status_bar.place(x=0, y=748, height=20, width=1366)
        self.status_bar.pack(fill=tk.BOTH)

        self.progress = ttk.Progressbar(results_frame, orient="horizontal", length=100, mode="determinate")
        #self.progress.place(x=1216, y=750, height=17, width=148)
        self.progress.pack(fill=tk.BOTH)

        # Save and Load Buttons
        self.save_button = ttk.Button(search_frame, text="Save Results", command=self.save_results)
        #self.save_button.place(x=708, y=500, height=40, width=100)
        self.save_button.pack()

        self.load_button = ttk.Button(search_frame, text="Load Results", command=self.load_results)
        #self.load_button.place(x=604, y=500, height=40, width=100)
        self.load_button.pack()

        self.show_images_button = ttk.Button(search_frame, text="Show in full size", command=self.show_images)
        #self.show_images_button.place(x=496, y=440, height=40, width=374)
        self.show_images_button.pack()

        self.open_in_explorer_button = ttk.Button(search_frame, text="Open in Explorer", command=self.open_in_explorer)
        #self.open_in_explorer_button.place(x=540, y=584, height=34, width=120)
        self.open_in_explorer_button.pack()

        self.delete_selected_button = ttk.Button(search_frame, text=self.languages[self.current_language]["delete_selected"], command=self.delete_selected)
        #self.delete_selected_button.place(x=700, y=584, height=34, width=120)
        self.delete_selected_button.pack()

        # Add processing control variables
        self.processing_flag = threading.Event()
        self.current_processing_thread = None

    def reset_ui(self):
        self.progress["value"] = 0
        self.stop_search_flag.clear()

    def upload_query_image(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.ppm *.pgm")])
        if file_path:
            self.target_image_path = file_path
            self.status.set(f"Selected Target Image: {os.path.basename(file_path)}")
            self.query_image = Image.open(file_path, 'r')
            self.display_uploaded(self.query_image)
        elif self.target_image_path:
            pass
        else:
            self.status.set(f"Selected Target Image: None")
            messagebox.showinfo("Info", "No target image selected")

    def add_folder(self):
        folder_path = filedialog.askdirectory()
        if not folder_path:
            return

        # Simple duplicate check (exact match only)
        if folder_path in self.added_folders:
            messagebox.showinfo("Info", "This exact folder path is already added")
            return

        self.added_folders.append(folder_path)
        self.folders_listbox.insert(tk.END, folder_path)
        self.folder_count += 1

    def remove_folder(self):
        selected_folder_name = self.folders_listbox.get(self.folders_listbox.curselection())
        selected_folder_index = self.folders_listbox.get(0, tk.END).index(selected_folder_name)
        if selected_folder_name:
            self.folders_listbox.delete(selected_folder_index)
            self.folder_path = None
            self.added_folders.remove(selected_folder_name)

    def move_up(self):
        selected_index = self.folders_listbox.curselection()
        if selected_index and selected_index[0] > 0:
            idx = selected_index[0]
            # Swap in listbox
            self.folders_listbox.insert(idx - 1, self.folders_listbox.get(idx))
            self.folders_listbox.delete(idx + 1)
            # Swap in data storage
            self.added_folders.insert(idx - 1, self.added_folders.pop(idx))
            # Maintain selection
            self.folders_listbox.selection_clear(0, tk.END)
            self.folders_listbox.selection_set(idx - 1)

    def move_down(self):
        selected_index = self.folders_listbox.curselection()
        if selected_index and selected_index[0] < self.folders_listbox.size() - 1:
            idx = selected_index[0]
            # Swap in listbox
            self.folders_listbox.insert(idx + 2, self.folders_listbox.get(idx))
            self.folders_listbox.delete(idx)
            # Swap in data storage
            self.added_folders.insert(idx + 1, self.added_folders.pop(idx))
            # Maintain selection
            self.folders_listbox.selection_clear(0, tk.END)
            self.folders_listbox.selection_set(idx + 1)

    def stop_search(self):
        self.stop_search_flag.set()

    def delete_selected(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showinfo("Info", "No image selected")
            return

        selected_file = self.tree.item(selected_item)['values'][0]
        confirmation = messagebox.askyesno("Confirm",
                                           f"Do you really want to delete {selected_file}? The file will be deleted from disk")

        if confirmation:
            try:
                os.remove(selected_file)
                self.tree.delete(selected_item)
                messagebox.showinfo("Info", f"Image {selected_file} has been deleted.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete image: {str(e)}")

    def display_uploaded(self, image):
        width_factor = self.canvas_uploaded.winfo_width() / image.width
        height_factor = self.canvas_uploaded.winfo_height() / image.height
        scale_factor = min(width_factor, height_factor)
        resized_image = image.resize((int(image.width * scale_factor), int(image.height * scale_factor)))
        img = ImageTk.PhotoImage(resized_image)
        x_position = (self.canvas_uploaded.winfo_width() - resized_image.width) // 2
        y_position = (self.canvas_uploaded.winfo_height() - resized_image.height) // 2
        self.canvas_uploaded.delete("all")
        self.canvas_uploaded.create_image(x_position, y_position, anchor=tk.NW, image=img)
        self.canvas_uploaded.image = img

    def display_selected(self, event):
        selected_items = self.tree.selection()
        if not selected_items:
            return

        selected_item = selected_items[0]
        current_mode = self.search_combobox.get()

        # Clear canvases first
        self.canvas_selected.delete("all")

        def display_image(file_path, canvas):
            """Helper to display an image fitted within canvas while maintaining aspect ratio"""
            try:
                image = Image.open(file_path)
                canvas.update_idletasks()  # Get accurate canvas dimensions
                canvas_width = canvas.winfo_width()
                canvas_height = canvas.winfo_height()

                # Calculate scaling to fit within canvas
                width_ratio = canvas_width / image.width
                height_ratio = canvas_height / image.height
                scale = min(width_ratio, height_ratio)

                # Only resize if needed
                if scale < 1 or scale > 1:  # Handle both upsizing and downsizing
                    new_size = (int(image.width * scale), int(image.height * scale))
                    image = image.resize(new_size, Image.Resampling.LANCZOS)

                img_tk = ImageTk.PhotoImage(image)
                canvas.delete("all")
                canvas.image = img_tk  # Keep reference

                # Center the image in canvas
                x = (canvas_width - image.width) // 2
                y = (canvas_height - image.height) // 2

                canvas.create_image(
                    x, y,
                    anchor=tk.NW,
                    image=img_tk
                )

            except Exception as e:
                print(f"Error displaying {file_path}: {str(e)}")

        if current_mode == "Duplicate Pairs":
            # Check if selected item is a group (parent) or file (child)
            children = self.tree.get_children(selected_item)

            if children:
                # Group selected: Show first file on uploaded canvas, second on selected
                file_paths = []
                for child in self.tree.get_children(selected_item):
                    child_file = self.tree.item(child)["values"][0].split(" Similarity:")[0].strip('\"')
                    if Path(child_file).exists():
                        file_paths.append(child_file)

                # Update both canvases
                if file_paths:
                    # Always keep first image on uploaded canvas
                    display_image(file_paths[0], self.canvas_uploaded)
                    # Show second image on selected canvas if available
                    if len(file_paths) > 1:
                        display_image(file_paths[1], self.canvas_selected)
            else:
                # File selected: Keep group's first image on left, show selected file on right
                parent = self.tree.parent(selected_item)
                if parent:
                    # Get first file from the group to keep on uploaded canvas
                    group_files = []
                    for child in self.tree.get_children(parent):
                        child_file = self.tree.item(child)["values"][0].split(" Similarity:")[0].strip('\"')
                        if Path(child_file).exists():
                            group_files.append(child_file)
                    if group_files:
                        # Maintain first image on uploaded canvas
                        display_image(group_files[0], self.canvas_uploaded)

                # Show selected file on right canvas
                file_path = self.tree.item(selected_item)["values"][0].split(" Similarity:")[0].strip('\"')
                if Path(file_path).exists():
                    display_image(file_path, self.canvas_selected)
        else:
            # Original behavior for non-group modes
            file_path = self.tree.item(selected_item)['values'][0].split(" Similarity:")[0].strip('\"')
            if Path(file_path).exists():
                display_image(file_path, self.canvas_selected)

    def list_files(self, folders=None, include_subfolders=False):
        """Process folders in listbox order, prioritizing subfolders of earlier entries"""
        files = []
        valid_ext = {".png", ".jpg", ".jpeg", ".bmp", ".ppm", ".pgm"}
        processed_paths = set()

        # Convert to resolved Path objects
        folders = [Path(f).resolve() for f in folders]

        # Process in listbox order while filtering subpaths
        for folder in folders:
            # Skip if already processed as subfolder of previous entry
            if any(folder.is_relative_to(p) for p in processed_paths):
                continue

            processed_paths.add(folder)

            try:
                if include_subfolders:
                    # Depth-first search to prioritize subfolders of current folder
                    dir_stack = [folder]
                    while dir_stack:
                        current_dir = dir_stack.pop()
                        entries = sorted(current_dir.iterdir(), key=lambda x: (x.is_file(), x.name), reverse=True)

                        for entry in entries:
                            entry_path = entry.resolve()
                            if entry.is_file() and entry.suffix.lower() in valid_ext:
                                files.append(entry_path)
                            elif entry.is_dir():
                                # Add subdirectories to stack first (depth-first)
                                dir_stack.append(entry_path)
                else:
                    # Process top-level files
                    for entry in folder.iterdir():
                        if entry.is_file() and entry.suffix.lower() in valid_ext:
                            files.append(entry.resolve())

            except Exception as e:
                print(f"Error processing {folder}: {e}")

        return files

    def run_search(self):
        # Check if a search is already running
        if self.search_thread and self.search_thread.is_alive():
            messagebox.showinfo("Info", "A search is already in progress. Please wait or stop the current search.")
            return

        # Existing condition checks remain unchanged
        has_folders = bool(self.added_folders)

        if self.search_combobox.get() == "Duplicate Pairs" and not has_folders:
            tk.messagebox.showinfo("Info", "Please add search folders.")
        elif not self.query_image and has_folders and self.search_combobox.get() != "Duplicate Pairs":
            tk.messagebox.showinfo("Info", "No file selected. Upload query image to start the search")
        elif not self.query_image and not has_folders and self.search_combobox.get() != "Duplicate Pairs":
            tk.messagebox.showinfo("Info", "Please add folders and select a query image.")
        elif self.query_image and not has_folders:
            tk.messagebox.showinfo("Info", "Please add search folders.")
        else:
            self.tree.delete(*self.tree.get_children())
            include_subfolders = self.subfolders.get() == 1

            # Get files from all added folders once
            self.files_list = self.list_files(self.added_folders, include_subfolders)
            total_files = len(self.files_list)
            self.progress["maximum"] = total_files
            search_type = self.search_combobox.get()
            self.stop_search_button.config(state=tk.NORMAL)

            # Assign all search threads to self.search_thread
            if search_type == "Vector Similarity":
                self.search_thread = threading.Thread(target=self.vector_search)
                self.search_thread.start()
            elif search_type == "Find Duplicates":
                self.search_thread = threading.Thread(target=self.search_duplicates)
                self.search_thread.start()
            elif search_type == "Histogram Similarity":
                image_uploaded = cv2.imdecode(np.fromfile(self.target_image_path, dtype=np.uint8), cv2.IMREAD_COLOR)
                hist1 = calculate_histogram(image_uploaded)
                self.search_thread = threading.Thread(target=self.search_histogram,
                                                      args=(self.files_list, hist1))
                self.search_thread.start()
            elif search_type == "Duplicate Pairs":
                self.search_thread = threading.Thread(target=self.duplicate_pairs)
                self.search_thread.start()
            elif search_type == "SSIM Compare":
                self.search_thread = threading.Thread(target=self.ssim_compare,
                                                      args=self.files_list)
                self.search_thread.start()
            elif search_type == "SIFT Compare":
                self.search_thread = threading.Thread(target=self.sift_compare)
                self.search_thread.start()

    def get_vector_path(self, folder_path):
        """Get standardized vector storage path for a folder"""
        folder_path = Path(folder_path).resolve()
        rel_path = folder_path.relative_to(folder_path.anchor)
        vector_dir = VECTOR_ROOT / rel_path
        vector_dir.mkdir(parents=True, exist_ok=True)
        return vector_dir / VECTOR_FILE, vector_dir / METADATA_FILE

    def process_folder(self, folder_path, include_subfolders=False):
        """Process folder and save vectors to .npy file"""
        # Convert input to Path object immediately
        folder_path = Path(folder_path)
        vector_path, meta_path = self.get_vector_path(folder_path)

        # Ensure vector storage directory exists
        vector_path.parent.mkdir(parents=True, exist_ok=True)

        # Check existing metadata
        existing = {}
        if meta_path.exists():
            try:
                meta_df = pd.read_csv(meta_path)
                existing = {row['path']: row['mtime'] for _, row in meta_df.iterrows()}
            except Exception as e:
                print(f"Error reading metadata: {e}")
                # Reset corrupted metadata
                meta_path.unlink(missing_ok=True)

        # Process files using proper Path operations
        new_vectors = []
        new_meta = []
        image_count = 0

        # Use appropriate search pattern
        search_pattern = folder_path.rglob('*') if include_subfolders else folder_path.glob('*')

        for entry in search_pattern:
            if self.stop_search_flag.is_set():
                break

            try:
                if entry.is_file() and entry.suffix.lower() in ('.jpg', '.jpeg', '.png'):
                    # Get path as POSIX string for consistent metadata
                    entry_str = entry.as_posix()
                    current_mtime = entry.stat().st_mtime

                    # Skip already processed unchanged files
                    if entry_str in existing and existing[entry_str] == current_mtime:
                        continue

                    # Extract features
                    vector = self.vector_extractor.extract(entry)
                    if vector is not None:
                        new_vectors.append(vector)
                        new_meta.append({
                            'path': entry_str,
                            'mtime': current_mtime
                        })
                        image_count += 1
            except Exception as e:
                print(f"Error processing {entry}: {str(e)}")
                continue

        # Update storage if new files found
        if new_vectors:
            try:
                # Load existing vectors if any
                if vector_path.exists():
                    existing_vectors = np.load(vector_path)
                    updated_vectors = np.vstack([existing_vectors, new_vectors])
                else:
                    updated_vectors = np.array(new_vectors)

                # Save updated vectors
                np.save(vector_path, updated_vectors)

                # Update metadata
                new_meta_df = pd.DataFrame(new_meta)
                if meta_path.exists():
                    existing_meta_df = pd.read_csv(meta_path)
                    updated_meta_df = pd.concat([existing_meta_df, new_meta_df])
                    # Remove duplicates keeping last modified
                    updated_meta_df = updated_meta_df.drop_duplicates('path', keep='last')
                else:
                    updated_meta_df = new_meta_df

                updated_meta_df.to_csv(meta_path, index=False)

            except Exception as e:
                print(f"Error saving vectors: {str(e)}")
                # Clean up partial saves
                vector_path.unlink(missing_ok=True)
                meta_path.unlink(missing_ok=True)
                return 0

        return image_count

    def process_all_folders(self, folders, include_subfolders):
        """Process folders sequentially with intra-folder parallelism"""
        all_folders = self._get_folder_structure(folders, include_subfolders)
        total = len(all_folders)
        self.root.after(0, self._update_progress_max, total)

        for folder_idx, main_folder in enumerate(folders, 1):
            if self.processing_flag.is_set():
                break

            # Get all subfolders for current main folder
            folder_group = [f for f in all_folders if Path(f).is_relative_to(main_folder)]

            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = {executor.submit(self.process_folder, Path(f)): f
                           for f in folder_group}

                for future in futures:
                    if self.processing_flag.is_set():
                        executor.shutdown(wait=False)
                        break

                    try:
                        future.result()
                    except Exception as e:
                        print(f"Error in {futures[future]}: {e}")

                    # Update progress for current folder group
                    self.root.after(0, self._update_progress,
                                    folder_idx * len(folder_group), total)

    def reprocess_folders(self):
        """Force reprocessing of all folders in a background thread"""
        if self.current_processing_thread and self.current_processing_thread.is_alive():
            self.processing_flag.set()
            self.current_processing_thread.join(timeout=5)

        # Retrieve Tkinter data in the main thread
        folders = list(self.folders_listbox.get(0, tk.END))
        include_subfolders = self.subfolders.get() == 1

        self.processing_flag.clear()
        self.current_processing_thread = threading.Thread(
            target=self._reprocess_all_folders,
            args=(folders, include_subfolders),
            daemon=True
        )
        self.current_processing_thread.start()
        #elif inna_metoda_indeksowania()

    def _reprocess_all_folders(self, folders, include_subfolders):
        """Background thread logic for reprocessing"""
        # Delete existing files first
        all_folders = set()
        for folder in folders:
            if include_subfolders:
                for root, dirs, _ in os.walk(folder):
                    all_folders.add(root)
            else:
                all_folders.add(folder)

        # Delete existing vector/meta files
        for folder in all_folders:
            vec_path, meta_path = self.get_vector_path(folder)
            if vec_path.exists():
                os.remove(vec_path)
            if meta_path.exists():
                os.remove(meta_path)

        # Now reprocess (reuse the existing processing logic)
        self.process_all_folders(folders, include_subfolders)

        # Show completion message in the main thread
        self.root.after(0, lambda: messagebox.showinfo(
            "Info", "All folders reprocessed with current model"
        ))

    def _update_progress_max(self, total):
        """Thread-safe progress max setup"""
        self.progress["maximum"] = total
        self.status.set("Starting folder processing...")

    def _update_progress(self, current, total):
        """Thread-safe progress update"""
        self.progress["value"] = current
        self.status.set(f"Processed {current}/{total} folders")

    def _finalize_processing(self):
        """Thread-safe finalization"""
        self.status.set("Folder processing completed"
                        if not self.processing_flag.is_set()
                        else "Processing interrupted")
        self.progress["value"] = 0
        self.processing_flag.clear()

    def start_folder_processing(self):
        """Start/Restart folder processing with thread management"""
        if self.current_processing_thread and self.current_processing_thread.is_alive():
            self.processing_flag.set()
            self.current_processing_thread.join(timeout=5)

        # Retrieve Tkinter data in the main thread
        folders = list(self.folders_listbox.get(0, tk.END))
        include_subfolders = self.subfolders.get() == 1

        self.processing_flag.clear()
        self.current_processing_thread = threading.Thread(
            target=self.process_all_folders,
            args=(folders, include_subfolders),
            daemon=True
        )
        self.current_processing_thread.start()

    def _get_folder_structure(self, folders, include_subfolders):
        """Get ordered list of folders with hierarchy"""
        ordered_folders = []
        for folder in folders:
            if include_subfolders:
                ordered_folders.extend([str(p) for p in Path(folder).rglob('')
                                        if p.is_dir()])
            else:
                ordered_folders.append(str(folder))
        return ordered_folders

    def _update_vector_progress(self, current, total, folder):
        """Thread-safe progress update for vector search"""
        self.progress["value"] = current
        self.status.set(f"Searching {folder} ({current}/{total})")

    def _complete_vector_search(self, results, elapsed_time):
        """Finalize search in main thread"""
        self.tree.delete(*self.tree.get_children())
        max_results = max(100, int(len(results) * 0.01))
        for path, similarity in sorted(results, key=lambda x: -x[1])[:max_results]:
            self.tree.insert("", tk.END, values=(path, f"{similarity:.2f}%"))

        self.status.set(f"Found {len(results)} matches in {elapsed_time:.2f}s")
        self.progress["value"] = 0
        self.stop_search_button.config(state=tk.DISABLED)

    def vector_search(self):
        """Entry point with explicit folder order"""
        try:
            self.tree.delete(*self.tree.get_children())
            query_vector = self.vector_extractor.extract(Path(self.target_image_path))

            if query_vector is None:
                messagebox.showerror("Error", "Feature extraction failed")
                return

            # Get folders in listbox order
            folders = list(self.folders_listbox.get(0, tk.END))
            include_subfolders = self.subfolders.get() == 1

            # Generate ordered vector file list
            vector_files = []
            for folder in folders:
                folder_path = Path(folder)
                if include_subfolders:
                    for root, _, _ in os.walk(folder_path):
                        vec_file = self.get_vector_path(root)[0]
                        if vec_file.exists():
                            vector_files.append(vec_file)
                else:
                    vec_file = self.get_vector_path(folder_path)[0]
                    if vec_file.exists():
                        vector_files.append(vec_file)

            if not vector_files:
                messagebox.showinfo("Info", "Process folders first")
                return

            # Start thread with ordered files
            self.progress["maximum"] = len(vector_files)
            self.search_thread = threading.Thread(
                target=self._vector_search_thread,
                args=(vector_files, query_vector),
                daemon=True
            )
            self.stop_search_button.config(state=tk.NORMAL)
            self.search_thread.start()

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _vector_search_thread(self, vector_files, query_vector):
        """Threaded vector search with ordered processing"""
        try:
            # Validate vector dimensions first
            if query_vector.shape[0] != 512:
                self.root.after(0, messagebox.showerror,
                                "Error", "Query vector dimension mismatch (expected 512)")
                return

            results = []
            start_time = time.time()
            total_files = len(vector_files)

            for idx, vec_file in enumerate(vector_files, 1):
                if self.stop_search_flag.is_set():
                    break

                # Update progress in main thread
                self.root.after(0, self._update_vector_progress,
                                idx, total_files, vec_file.parent)

                # Process current vector file
                try:
                    vectors = np.load(vec_file, mmap_mode='r')
                    meta_file = vec_file.parent / METADATA_FILE
                    meta_df = pd.read_csv(meta_file)

                    # Calculate similarities
                    similarities = np.dot(vectors, query_vector)
                    euclidean_dists = np.linalg.norm(vectors - query_vector, axis=1)

                    # Apply thresholds
                    for i, (sim, dist) in enumerate(zip(similarities, euclidean_dists)):
                        sim_percent = sim * 100
                        if (sim_percent >= max(int(self.sim.get()), 70) and
                                dist <= 0.5 and
                                sim_percent >= self._calculate_adaptive_threshold(similarities)):
                            results.append((meta_df.iloc[i]['path'], sim_percent))

                except Exception as e:
                    print(f"Error processing {vec_file}: {str(e)}")

            # Finalize in main thread
            elapsed = time.time() - start_time
            self.root.after(0, self._complete_vector_search, results, elapsed)

        except Exception as e:
            self.root.after(0, messagebox.showerror,
                            "Search Error", str(e))

    def _calculate_adaptive_threshold(self, similarities):
        """Calculate dynamic threshold based on similarity distribution"""
        similarities = np.array(similarities)
        if len(similarities) == 0:
            return 0

        # Use 90th percentile as baseline
        threshold = np.percentile(similarities, 90) * 100
        return max(threshold, 70)  # Minimum 70% threshold

    def search_histogram(self, files, hist1):
        start_time = time.time()
        analyzed_files_count = 0
        files_found = 0

        for count, file in enumerate(files, start=1):
            if self.stop_search_flag.is_set():
                self.status.set(f"Search stopped by user. {analyzed_files_count} files analyzed")
                break
            self.status.set(f"Analyzing {file.name} ({count}/{len(files)}) - {files_found} matches found")
            self.root.update_idletasks()
            analyzed_files_count += 1
            if file != self.target_image_path:
                image_queued = cv2.imdecode(np.fromfile(file, dtype=np.uint8), cv2.IMREAD_COLOR)
                hist2 = calculate_histogram(image_queued)
                similarity = compare_histograms(hist1, hist2)
                if similarity >= int(self.sim.get()):
                    self.tree.insert("", tk.END, values=(file, f"{similarity:.2f}"))
                    files_found += 1
            self.progress["value"] = count
            self.root.update_idletasks()
        else:
            self.status.set(f"Completed. {analyzed_files_count} files analyzed")

        end_time = time.time()
        elapsed_time = end_time - start_time
        if analyzed_files_count != 0:
            self.status.set(f"Completed in {elapsed_time:.2f} seconds, {analyzed_files_count} files analyzed, {files_found} similar images found")
            self.progress["value"] = 0
        else:
            messagebox.showinfo("Error", f"No image files found in selected folders. Try ticking the \"Search subfolders\" option")
            self.progress["value"] = 0

        self.reset_ui()
        self.stop_search_button.config(state=tk.DISABLED)

        self.search_thread = None

    def search_duplicates(self):
        """Find all duplicates of the target image using parallel processing"""
        try:
            self.tree.delete(*self.tree.get_children())
        except Exception as e:
            messagebox.showerror("Error", str(e))

        include_subfolders = self.subfolders.get() == 1
        # Use added_folders instead of folder_path
        files = self.list_files(self.added_folders, include_subfolders)
        self.progress["maximum"] = len(files)

        # Pre-calculate target hash once
        target_hash = calculate_image_hash(self.target_image_path)

        self.search_thread = threading.Thread(target=self._search_duplicates_thread,
                                              args=(files, target_hash))
        self.search_thread.start()

    def calculate_quick_hash(self, image_path):
        """Fast partial hash of first and middle 8KB chunks"""
        chunk_size = 8192  # 8KB chunks
        file_size = os.path.getsize(image_path)
        hasher = hashlib.sha256()

        try:
            with open(image_path, 'rb') as f:
                # First chunk
                hasher.update(f.read(chunk_size))

                # Middle chunk
                if file_size > chunk_size * 2:
                    f.seek(file_size // 2)
                    hasher.update(f.read(chunk_size))

                # Last chunk for files > 1MB
                if file_size > 1024 * 1024:
                    f.seek(-chunk_size, os.SEEK_END)
                    hasher.update(f.read(chunk_size))

            return hasher.hexdigest()
        except Exception as e:
            print(f"Error reading {image_path}: {str(e)}")
            return None

    def _search_duplicates_thread(self, files, source_hash):
        """Modified thread with quick checksum filtering"""
        start_time = time.time()
        analyzed_files_count = 0

        # Precompute target quick hash
        target_quick_hash = self.calculate_quick_hash(self.target_image_path)
        target_size = os.path.getsize(self.target_image_path)

        for count, file in enumerate(files, start=1):
            if self.stop_search_flag.is_set():
                self.status.set(f"Search stopped. Analyzed {analyzed_files_count} files")
                break

            try:
                # First check: File size comparison
                file_size = os.path.getsize(file)
                if file_size != target_size:
                    continue

                # Second check: Quick hash comparison
                file_quick_hash = self.calculate_quick_hash(file)
                if file_quick_hash != target_quick_hash:
                    continue

                # Final check: Full hash comparison
                analyzed_files_count += 1
                self.status.set(f"Deep analyzing {file.name} ({count}/{len(files)})")
                file_hash = calculate_image_hash(file)

                if file_hash == source_hash and self.target_image_path != file:
                    self.tree.insert("", tk.END, values=(file, "Duplicate"))

            except Exception as e:
                print(f"Error processing {file}: {str(e)}")

            self.progress["value"] = count
            self.root.update_idletasks()

        elapsed_time = time.time() - start_time
        self.status.set(f"Found {self.tree.get_children().__len__()} duplicates in {elapsed_time:.1f}s")
        self.progress["value"] = 0
        self.stop_search_button.config(state=tk.DISABLED)

        self.search_thread = None

    def duplicate_pairs(self):
        """Find all duplicate groups in the dataset using hash grouping"""
        if not self.folder_path:
            tk.messagebox.showinfo("Info", "Please select a folder.")
            return

        self.status.set("Searching for duplicate groups...")
        self.progress['value'] = 0

        # Thread management now handled in run_search
        self._duplicate_pairs_thread()

    def _duplicate_pairs_thread(self):
        """Threaded duplicate group search with optimized grouping"""
        start_time = time.time()
        self.tree.delete(*self.tree.get_children())

        include_subfolders = self.subfolders.get() == 1
        files = self.list_files(Path(self.folder_path), include_subfolders)
        hash_groups = {}

        # Phase 1: Group files by hash
        with ThreadPoolExecutor(max_workers=os.cpu_count() * 2) as executor:
            future_to_file = {executor.submit(calculate_image_hash, file): file for file in files}
            processed = 0

            for future in future_to_file:
                if self.stop_search_flag.is_set():
                    break

                file = future_to_file[future]
                try:
                    file_hash = future.result()
                    if file_hash in hash_groups:
                        hash_groups[file_hash].append(file)
                    else:
                        hash_groups[file_hash] = [file]

                    processed += 1
                    if processed % 100 == 0:
                        self.progress["value"] = processed
                        self.status.set(f"Processed {processed}/{len(files)} files")
                        self.root.update_idletasks()

                except Exception as e:
                    print(f"Error processing {file}: {str(e)}")

        # Phase 2: Insert groups into Treeview hierarchically
        group_id = 0
        for file_hash, group in hash_groups.items():
            if len(group) >= 2:
                if len(group) == 2:
                    # Insert as direct pair in columns 1 and 2
                    self.tree.insert("", "end", values=(group[0], group[1]))
                else:
                    # Create parent node with first two files preview
                    parent = self.tree.insert(
                        "", "end",
                        text=f"Group {group_id + 1} ({len(group)} duplicates)",
                        values=(group[0], group[1])
                    )
                    # Add children with individual paths
                    for file in group:
                        self.tree.insert(parent, "end", values=(file, ""))
                    group_id += 1

        elapsed_time = time.time() - start_time
        self.status.set(f"Found {len(hash_groups)} groups in {elapsed_time:.2f}s")
        self.progress['value'] = 0
        self.stop_search_button.config(state=tk.DISABLED)

        self.search_thread = None

    def _initialize_sift(self):
        """Initialize SIFT detector with version checking"""
        try:
            # Try modern SIFT (OpenCV ≥ 4.4.0)
            return cv2.SIFT_create()
        except AttributeError:
            try:
                # Fallback to legacy SIFT (OpenCV 3.x)
                from cv2.xfeatures2d import SIFT_create
                return SIFT_create()
            except ImportError:
                messagebox.showerror("SIFT Error",
                                     "SIFT requires opencv-contrib-python")
                return None
        except Exception as e:
            messagebox.showerror("SIFT Error", f"Failed to initialize SIFT: {str(e)}")
            return None

    def sift_compare(self):
        """Entry point for SIFT-based similarity search"""
        try:
            self.tree.delete(*self.tree.get_children())
            self.stop_search_flag.clear()  # Reset stop flag when starting new search
        except Exception as e:
            messagebox.showerror("Error", str(e))

        include_subfolders = self.subfolders.get() == 1
        files = self.list_files(Path(self.folder_path), include_subfolders)
        self.progress["maximum"] = len(files)

        # Limit thread count to reduce CPU load (adjust max_workers as needed)
        max_workers = max(2, os.cpu_count() // 2)  # Reduced from full CPU count
        self.search_thread = threading.Thread(target=self._sift_compare_thread,
                                              args=(files, max_workers))
        self.search_thread.start()

    def _sift_compare_thread(self, files, max_workers):
        start_time = time.time()
        processed_count = 0
        files_found = 0  # Track matching files

        sift = cv2.SIFT_create(contrastThreshold=0.07, edgeThreshold=5)
        query_img = cv2.imread(self.target_image_path, cv2.IMREAD_GRAYSCALE)
        kp1, des1 = sift.detectAndCompute(query_img, None)

        if des1 is None or len(des1) < 10:
            self.status.set("No features found in query image")
            return

        bf = cv2.BFMatcher(cv2.NORM_L2, crossCheck=False)
        MIN_MATCHES = 5
        RATIO_THRESH = 0.9
        total_files = len(files)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for file in files:
                if self.stop_search_flag.is_set():
                    break
                futures.append(executor.submit(
                    self._process_sift_file,
                    file, bf, des1, MIN_MATCHES, RATIO_THRESH
                ))

            # Process completed tasks and update progress
            for future in as_completed(futures):
                if self.stop_search_flag.is_set():
                    for f in futures:
                        f.cancel()
                    break

                processed_count += 1
                self.progress["value"] = processed_count

                # Update status every 5 files or when processing takes time
                if processed_count % 5 == 0 or processed_count == total_files:
                    self.status.set(
                        f"Analyzing files ({processed_count}/{total_files}) - "
                        f"{files_found} matches found"
                    )
                    self.root.update_idletasks()

                try:
                    result = future.result()
                    if result:
                        self.tree.insert("", tk.END, values=result)
                        files_found += 1
                except Exception as e:
                    continue

        elapsed_time = time.time() - start_time
        stop_status = "stopped" if self.stop_search_flag.is_set() else "completed"
        status_message = (
            f"{stop_status.capitalize()} in {elapsed_time:.2f}s - "
            f"{processed_count} files analyzed, "
            f"{files_found} matches found"
        )
        self.status.set(status_message)
        self.progress["value"] = 0
        self.stop_search_button.config(state=tk.DISABLED)
        self.stop_search_flag.clear()
        self.search_thread = None

    def _process_sift_file(self, file, bf, des1, min_matches, ratio_thresh):
        if self.stop_search_flag.is_set():
            return None

        try:
            target_img = cv2.imread(str(file), cv2.IMREAD_GRAYSCALE)
            if target_img is None:
                return None

            # Check stop flag before heavy computation
            if self.stop_search_flag.is_set():
                return None

            sift = cv2.SIFT_create(contrastThreshold=0.01, edgeThreshold=5)
            kp2, des2 = sift.detectAndCompute(target_img, None)

            if des2 is None or len(des2) < min_matches:
                return None

            matches = bf.knnMatch(des1, des2, k=2)
            good = []
            for m, n in matches:
                if m.distance < ratio_thresh * n.distance:
                    good.append(m)
                if self.stop_search_flag.is_set():
                    return None

            if len(good) < min_matches:
                return None

            def _sift_compare_thread(self, files, max_workers):
                start_time = time.time()
                processed_count = 0  # Track total processed files

                sift = cv2.SIFT_create(contrastThreshold=0.07, edgeThreshold=5)
                query_img = cv2.imread(self.target_image_path, cv2.IMREAD_GRAYSCALE)
                kp1, des1 = sift.detectAndCompute(query_img, None)

                if des1 is None or len(des1) < 10:
                    self.status.set("No features found in query image")
                    return

                bf = cv2.BFMatcher(cv2.NORM_L2, crossCheck=False)
                MIN_MATCHES = 5
                RATIO_THRESH = 0.9

                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = []
                    for file in files:
                        if self.stop_search_flag.is_set():
                            break
                        futures.append(executor.submit(
                            self._process_sift_file,
                            file, bf, des1, MIN_MATCHES, RATIO_THRESH
                        ))

                    # Process completed tasks and update progress
                    for future in as_completed(futures):
                        if self.stop_search_flag.is_set():
                            for f in futures:
                                f.cancel()
                            break

                        processed_count += 1
                        self.progress["value"] = processed_count
                        self.root.update_idletasks()

                        try:
                            result = future.result()
                            if result:
                                self.tree.insert("", tk.END, values=result)
                        except Exception as e:
                            continue

                elapsed_time = time.time() - start_time
                stop_status = "stopped" if self.stop_search_flag.is_set() else "completed"
                self.status.set(
                    f"SIFT compare {stop_status} in {elapsed_time:.2f}s - Processed {processed_count} files")
                self.progress["value"] = 0
                self.stop_search_button.config(state=tk.DISABLED)
                self.stop_search_flag.clear()
                self.search_thread = None

        except Exception as e:
            print(f"Error processing {file}: {str(e)}")
        return None

    def ssim_compare(self, *files):
        start_time = time.time()
        analyzed_files_count = 0
        files_found = 0
        for count, file in enumerate(files, start=1):
            analyzed_files_count += 1
            if self.stop_search_flag.is_set():
                self.status.set(f"Search stopped by user. {analyzed_files_count} files analyzed")
                break

            self.status.set(f"Analyzing ({count}/{len(files)}) - {files_found} matches found")
            self.root.update_idletasks()

            if Image.open(self.target_image_path).width == Image.open(file).width and Image.open(self.target_image_path).height == Image.open(file).height:
                image = cv2.imdecode(np.fromfile(self.target_image_path, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
                compare = cv2.imdecode(np.fromfile(file, dtype=np.uint8), cv2.IMREAD_UNCHANGED)

                # Convert images to grayscale
                first_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                second_gray = cv2.cvtColor(compare, cv2.COLOR_BGR2GRAY)

                # Compute SSIM between two images
                score, diff = structural_similarity(first_gray, second_gray, full=True)
                if score*100 >= int(self.sim.get()):
                    self.tree.insert("", tk.END, values=(file, f"{score*100:.2f}%"))
                    files_found += 1

                # The diff image contains the actual image differences between the two images
                # and is represented as a floating point data type so we must convert the array
                # to 8-bit unsigned integers in the range [0,255] before we can use it with OpenCV
                diff = (diff * 255).astype("uint8")

                # Threshold the difference image, followed by finding contours to
                # obtain the regions that differ between the two images
                thresh = cv2.threshold(diff, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
                contours = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                contours = contours[0] if len(contours) == 2 else contours[1]

                # Highlight differences
                #mask = np.zeros(image.shape, dtype='uint8')
                #filled = file.copy()

                # for c in contours:
                #     area = cv2.contourArea(c)
                #     if area > 100:
                #         x, y, w, h = cv2.boundingRect(c)
                #         cv2.rectangle(image, (x, y), (x + w, y + h), (36, 255, 12), 2)
                #         cv2.rectangle(compare, (x, y), (x + w, y + h), (36, 255, 12), 2)
                #         cv2.drawContours(mask, [c], 0, (0, 255, 0), -1)
                        #cv2.drawContours(filled, [c], 0, (0, 255, 0), -1)

                # if source_hash == calculate_image_hash(file) and self.target_image_path != file:
                #     self.tree.insert("", tk.END, values=(file, "Duplicate"))
                self.progress["value"] = count
                self.root.update_idletasks()
        else:
            self.status.set(f"Completed. {analyzed_files_count} files analyzed")

        end_time = time.time()
        elapsed_time = end_time - start_time
        if analyzed_files_count != 0:
            self.status.set(f"Completed in {elapsed_time:.2f} seconds, {analyzed_files_count} files analyzed, {files_found} similar images found")
            self.progress["value"] = 0
        else:
            messagebox.showinfo("Error", f"No image files found in selected folders. Try ticking the \"Search subfolders\" option")
            self.progress["value"] = 0

        self.reset_ui()
        self.stop_search_button.config(state=tk.DISABLED)

        self.search_thread = None

    def save_results(self):
        if not self.tree.get_children():
            messagebox.showinfo("Info", "No search results to save.")
            return

        default_save_dir = "C:/ImSearchResults"

        if not os.path.exists(default_save_dir):
            os.makedirs(default_save_dir)

        count = 0
        for file in os.listdir(default_save_dir):
            if file.startswith("result_") and file.endswith(".csv"):
                count += 1

        proposed_filename = f"result_{count + 1}.csv"

        file_path = filedialog.asksaveasfilename(
            initialdir=default_save_dir,
            title="Save Results",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile=proposed_filename
        )

        if not file_path:
            return

        similarity_threshold = self.sim.get()
        search_subfolders = "Yes" if self.subfolders.get() == 1 else "No"

        # save to file
        with open(file_path, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Target Image", self.target_image_path])
            writer.writerow(["Similarity Threshold (%)", similarity_threshold])
            writer.writerow(["Search Subfolders", search_subfolders])
            writer.writerow([])
            writer.writerow(["Name", "Similarity"])
            for item in self.tree.get_children():
                file_name, similarity = self.tree.item(item, "values")
                writer.writerow([file_name, similarity])

        messagebox.showinfo("Info", f"Results saved to {file_path}")

    def load_results(self):
        file_path = filedialog.askopenfilename(
            title="Load Results",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialdir="C:/ImSearchResults"
        )

        if not file_path:
            return

        with open(file_path, mode='r') as file:
            reader = csv.reader(file)

            self.tree.delete(*self.tree.get_children())

            target_image_path = None
            similarity_threshold = None
            search_subfolders = None

            for row in reader:
                if not row:  # empty rows
                    continue

                if row[0] == "Target Image":
                    target_image_path = row[1]
                    continue
                elif row[0] == "Similarity Threshold (%)":
                    similarity_threshold = row[1]
                    continue
                elif row[0] == "Search Subfolders":
                    search_subfolders = row[1]
                    continue
                elif row[0] == "Name" and row[1] == "Similarity":
                    continue  # skip header

                if len(row) == 2:
                    file_name, similarity = row
                    self.tree.insert("", tk.END, values=(file_name, similarity))

            if target_image_path:
                self.target_image_path = target_image_path
                self.query_image = Image.open(target_image_path, 'r')
                self.display_uploaded(self.query_image)

            if similarity_threshold:
                self.sim.delete(0, tk.END)
                self.sim.insert(0, similarity_threshold)

            if search_subfolders:
                self.subfolders.set(1 if search_subfolders == "Yes" else 0)

            messagebox.showinfo("Info", f"Results loaded from {file_path}")

    def show_images(self):
        selected_item = self.tree.selection()
        if selected_item:
            selected_file_path = self.tree.item(selected_item)['values'][0]
            pos = selected_file_path.find(" Similarity:")
            if pos > -1:
                selected_file_path = selected_file_path[:pos]

            target_image_full = Image.open(self.target_image_path, 'r')
            selected_image_full = Image.open(selected_file_path, 'r')

            target_width, target_height = target_image_full.size
            selected_width, selected_height = selected_image_full.size

            window_width = max(target_width, selected_width) * 2
            window_height = max(target_height, selected_height)

            new_window = tk.Toplevel(self.root)
            new_window.title("Full Size Images")
            new_window.geometry(f"{window_width}x{window_height}")

            canvas_target = tk.Canvas(new_window, bg="white", relief=tk.SUNKEN, width=target_width,
                                      height=target_height)
            canvas_target.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            canvas_selected = tk.Canvas(new_window, bg="white", relief=tk.SUNKEN, width=selected_width,
                                        height=selected_height)
            canvas_selected.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

            target_image_full = ImageTk.PhotoImage(target_image_full)
            canvas_target.create_image(0, 0, anchor=tk.NW, image=target_image_full)
            canvas_target.image = target_image_full

            selected_image_full = ImageTk.PhotoImage(selected_image_full)
            canvas_selected.create_image(0, 0, anchor=tk.NW, image=selected_image_full)
            canvas_selected.image = selected_image_full

    def open_in_explorer(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showinfo("Info", "No image selected")
            return
        selected_file = self.tree.item(selected_item)['values'][0]
        if " Similarity:" in selected_file:
            selected_file = selected_file.split(" Similarity:")[0]
        selected_file = Path(selected_file).resolve()
        if selected_file.exists():
            if os.name == 'nt':  # Windows
                os.system(f'explorer /select,"{selected_file}"')
            elif os.name == 'posix':
                # macOS
                try:
                    os.system(f'open -R "{selected_file}"')
                except:
                    # Linux
                    os.system(f'xdg-open "{selected_file.parent}"')
        else:
            messagebox.showinfo("Info", f"File {selected_file} does not exist")

    def change_language(self, language):
        """Change application language and update UI text."""
        self.current_language = language

        # Update all UI elements with new language text
        self.add_folder_button.config(text=self.languages[language]["add_folder"])
        self.remove_folder_button.config(text=self.languages[language]["remove_folder"])
        self.folder_up_button.config(text=self.languages[language]["folder_up"])
        self.folder_down_button.config(text=self.languages[language]["folder_down"])
        self.upload_image_button.config(text=self.languages[language]["upload_image"])
        self.search_mode_label.config(text=self.languages[language]["search_mode"])
        self.search_settings_label.config(text=self.languages[language]["search_settings"])
        self.similarity_threshold_label.config(text=self.languages[language]["similarity_threshold"])
        self.delete_selected_button.config(text=self.languages[language]["delete_selected"])
        self.subfolder_button.config(text=self.languages[language]["search_subfolders"])
        self.start_search_button.config(text=self.languages[language]["start_search"])
        self.stop_search_button.config(text=self.languages[language]["stop_search"])

        # Update language menu label
        menubar = self.root.winfo_toplevel().config(menu=None)
        menubar = Menu(self.root)
        self.root.config(menu=menubar)
        settings_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Settings", menu=settings_menu)

        # Rebuild language menu with updated text
        language_menu = Menu(settings_menu, tearoff=0)
        for lang in self.languages.keys():
            language_menu.add_command(label=lang, command=lambda: self.change_language(lang))
        settings_menu.add_cascade(label=self.languages[self.current_language]["language"], menu=language_menu)


#run from terminal, experimental
def findSimilar5(self, img_path, folder_path, method):
    try:
        image1 = cv2.imread(Path(img_path))
        hist1 = calculate_histogram(image1)
    except Exception as e:
        tk.messagebox.showerror("Error", f"Unable to read source image: {e}")
        return
    files = self.listFiles(Path(folder_path))
    # if method == 1:
    #     self.search_duplicates()
    # elif method == 2:
    #     self.search_histogram()
    # elif method == 3:
    #     self.ssim_compare()
    # elif method == 4:
    #     self.duplicate_pairs()
    for file in files:
        if file != img_path:  # Exclude the source image itself
            try:
                image2 = cv2.imread(str(file))
                hist2 = calculate_histogram(image2)
                similarity = self.compare_histogram(hist1, hist2)
                if similarity >= 1:
                    print(f"{file} Similarity: {similarity:.2f}%")
            except Exception as e:
                print(f"Error processing file {file}: {e}")

# class Folder_frame(Frame):
#     def __init__(self, parent):
#         super().__init__(parent)
#
#         self.pack(pady=10)


if __name__ == "__main__":
    match len(sys.argv):
        case 1:
            root = tk.Tk()
            app = ImSearch(root)
            root.mainloop()
        case 4:
            img = sys.argv[1]
            path = sys.argv[2]
            method = sys.argv[3]
            if method=="1":findSimilar5(img, path, method)
        case _:print("Error\n Correct command main.py [query image_path] [folder_search path] [search_method]")