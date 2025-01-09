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
from PIL import Image, ImageTk
from skimage.metrics import structural_similarity
import csv


def calculate_image_hash(image_path):
    with open(image_path, 'rb') as file:
        image_data = file.read()
        image_hash = hashlib.sha256(image_data).hexdigest()
    return image_hash


class ImSearch:
    def __init__(self, root):
        self.subfolders = tk.IntVar()
        self.time = tk.IntVar()
        self.stop_search_flag = threading.Event()
        self.search_thread = None

        self.root = root
        self.root.title("ImSearch")
        self.root.geometry("1366x768")

        self.folder_count = 0
        self.folder_path = None
        self.query_image = None
        self.target_image_path = None
        self.target_image_label = None
        self.include_subfolders = None
        self.image_files = []

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
                "selected_image": "Selected Target Image: None",
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
                "selected_image": "Imagen Objetivo Seleccionada: Ninguna",
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

        # canvas
        self.canvas_uploaded = tk.Canvas(root, bg="white", relief=tk.SUNKEN, borderwidth=1)
        self.canvas_uploaded.place(x=12, y=96, height=535, width=428)

        self.canvas_selected = tk.Canvas(root, bg="white", relief=tk.SUNKEN, borderwidth=1)
        self.canvas_selected.place(x=926, y=96, height=535, width=428)

        self.folders_listbox = tk.Listbox(root, selectmode=tk.SINGLE)
        self.folders_listbox.place(x=166, y=10, height=80, width=1034)

        # folder button
        self.add_folder_button = ttk.Button(root, text=self.languages[self.current_language]["add_folder"], command=self.add_folder)
        self.add_folder_button.place(x=1212, y=50, height=40, width=140)

        self.remove_folder_button = ttk.Button(root, text=self.languages[self.current_language]["remove_folder"], command=self.remove_folder)
        self.remove_folder_button.place(x=1212, y=10, height=40, width=140)

        self.folder_up_button = ttk.Button(root, text=self.languages[self.current_language]["folder_up"], command=self.move_up)
        self.folder_up_button.place(x=14, y=10, height=40, width=140)

        self.folder_down_button = ttk.Button(root, text=self.languages[self.current_language]["folder_down"], command=self.move_down)
        self.folder_down_button.place(x=14, y=50, height=40, width=140)

        # select image button
        self.upload_image_button = ttk.Button(root, text=self.languages[self.current_language]["upload_image"], command=self.upload_query_image)
        self.upload_image_button.place(x=496, y=122, height=52, width=374)

        # selected image label
        self.target_image_label = ttk.Label(root, text="Selected Target Image: None")
        self.target_image_label.place(x=64, y=720)

        self.search_mode_label = ttk.Label(root, text=self.languages[self.current_language]["search_mode"])
        self.search_mode_label.place(x=496, y=200)

        self.search_settings_label = ttk.Label(root, text=self.languages[self.current_language]["search_settings"])
        self.search_settings_label.place(x=496, y=240)

        self.similarity_threshold_label = ttk.Label(root, text=self.languages[self.current_language]["similarity_threshold"])
        self.similarity_threshold_label.place(x=496, y=280)

        self.sim = tk.Spinbox(self.root, from_=0, to=100)
        self.sim.delete(0, "end")
        self.sim.insert(0, "50")
        self.sim.place(x=650, y=282, height=20, width=32)
        tk.Label(self.root, text="%", fg="black").place(x=682, y=283, height=20, width=10)

        self.search_combobox = ttk.Combobox(root, values=["Find Similar", "Find Duplicates", "Duplicate Pairs", "SSIM Compare"], state="readonly")
        self.search_combobox.place(x=650, y=192, height=34, width=220)
        self.search_combobox.current(0)

        self.start_search_button = ttk.Button(root, text=self.languages[self.current_language]["start_search"], command=self.run_search)
        self.start_search_button.place(x=710, y=280, height=34, width=160)

        self.stop_search_button = ttk.Button(self.root, text=self.languages[self.current_language]["stop_search"], command=self.stop_search)
        self.stop_search_button.place(x=710, y=324, height=34, width=160)
        self.stop_search_button.config(state=tk.DISABLED)

        self.subfolder_button = ttk.Checkbutton(self.root, text=self.languages[self.current_language]["search_subfolders"], variable=self.subfolders,
                                                onvalue=1, offvalue=0)
        self.subfolder_button.place(x=650, y=243)

        self.tree_frame = Frame(root)
        self.tree = ttk.Treeview(self.tree_frame, columns=("path", "similarity"), show="headings", selectmode="browse")
        verscrlbar = ttk.Scrollbar(self.tree_frame,
                                   orient="vertical",
                                   command=self.tree.yview)
        verscrlbar.pack(side="right", fill="y", pady=1, padx=1)
        self.tree.configure(yscrollcommand=verscrlbar.set)
        self.tree.heading("path", text="Image path")
        self.tree.heading("similarity", text="Similarity (%)")
        self.tree.column("path")
        self.tree.column("similarity")
        self.tree.place(x=0, y=0, height=100, width=1340)
        self.tree_frame.place(x=14, y=640, height=100, width=1340)
        self.tree.bind("<<TreeviewSelect>>", self.display_selected)

        # Status Bar with Progress Bar
        self.status = tk.StringVar()
        self.status.set("Ready")
        self.status_bar = ttk.Label(self.root, textvariable=self.status, relief=tk.SUNKEN, anchor='w')
        self.status_bar.place(x=0, y=748, height=20, width=1366)

        self.progress = ttk.Progressbar(self.root, orient="horizontal", length=100, mode="determinate")
        self.progress.place(x=1216, y=750, height=17, width=148)

        # Save and Load Buttons
        save_button = ttk.Button(root, text="Save Results", command=self.save_results)
        save_button.place(x=708, y=500, height=40, width=100)

        self.load_button = ttk.Button(root, text="Load Results", command=self.load_results)
        self.load_button.place(x=604, y=500, height=40, width=100)

        self.show_images_button = ttk.Button(self.root, text="Show in full size", command=self.show_images)
        self.show_images_button.place(x=496, y=440, height=40, width=374)

        self.open_in_explorer_button = ttk.Button(root, text="Open in Explorer", command=self.open_in_explorer)
        self.open_in_explorer_button.place(x=540, y=584, height=34, width=120)

        self.delete_selected_button = ttk.Button(root, text=self.languages[self.current_language]["delete_selected"], command=self.delete_selected)
        self.delete_selected_button.place(x=700, y=584, height=34, width=120)


    def upload_query_image(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.ppm *.pgm")])
        if file_path:
            self.target_image_path = file_path
            self.target_image_label.config(text=f"Selected Target Image: {os.path.basename(file_path)}")
            self.query_image = Image.open(file_path, 'r')
            self.display_uploaded(self.query_image)
        else:
            self.target_image_label.config(text="Selected Target Image: None")
            messagebox.showinfo("Info", "No target image selected")

    def add_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.folders_listbox.insert(self.folder_count, folder_path)
            self.folder_count += 1

            self.folder_path = folder_path
            self.image_files = [os.path.join(folder_path, file) for file in os.listdir(folder_path) if
                                file.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".ppm"))]

            # if not self.image_files:
            #     messagebox.showinfo("Info", "No image files found in the selected folder.")
            # else:
            self.target_image_label.config(text="Selected Target Image: None")

    def remove_folder(self):
        selected_folder = self.folders_listbox.curselection()
        if selected_folder:
            self.folders_listbox.delete(selected_folder[0])
            self.folder_path = None

    def move_up(self):
        selected_index = self.folders_listbox.curselection()
        if selected_index and selected_index[0] > 0:
            text = self.folders_listbox.get(selected_index)
            self.folders_listbox.delete(selected_index)
            self.folders_listbox.insert(selected_index[0] - 1, text)
            self.folders_listbox.selection_set(selected_index[0] - 1)

    def move_down(self):
        selected_index = self.folders_listbox.curselection()
        if selected_index and selected_index[0] < self.folders_listbox.size() - 1:
            text = self.folders_listbox.get(selected_index)
            self.folders_listbox.delete(selected_index)
            self.folders_listbox.insert(selected_index[0] + 1, text)
            self.folders_listbox.selection_set(selected_index[0] + 1)

    def stop_search(self):
        self.stop_search_flag.set()

    def run_search(self):
        if self.search_combobox.get() == "Duplicate Pairs" and not self.folder_path:
            tk.messagebox.showinfo("Info", "Please set search folder.")
        elif not self.query_image and self.folder_path and self.search_combobox.get() != "Duplicate Pairs":
            tk.messagebox.showinfo("Info", "No file selected. Upload query image to start the search")
        elif not self.query_image and not self.folder_path and self.search_combobox.get() != "Duplicate Pairs":
            tk.messagebox.showinfo("Info", "Please set both file and folder.")
        elif self.query_image and not self.folder_path:
            tk.messagebox.showinfo("Info", "Please set search folder.")
        else:
            self.stop_search_button.config(state=tk.NORMAL)
            self.tree.delete(*self.tree.get_children())
            include_subfolders = self.subfolders.get() == 1
            files = self.list_files(Path(self.folder_path), include_subfolders)
            total_files = len(files)
            self.progress["maximum"] = total_files
            search_type = self.search_combobox.get()
            self.stop_search_flag.clear()

            if search_type == "Find Duplicates":
                self.search_duplicates()
            elif search_type == "Find Similar":
                self.search_similar()
            elif search_type == "Duplicate Pairs":
                self.tree.heading(0, text="Image 1")
                self.tree.heading(1, text="Image 2")
                self.duplicate_pairs()
            elif search_type == "SSIM Compare":
                self.ssim_compare()
            elif search_type == "SIFT Compare":
                self.sift_compare()
            #self.stop_button.config(state=tk.DISABLED) #executes before the if statement

    def reset_ui(self):
        #self.status.set("Ready")
        self.progress["value"] = 0
        self.stop_search_flag.clear()

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
        selected_item = self.tree.selection()
        if self.search_combobox.get() == "Duplicate Pairs" and selected_item:
            file1, file2 = self.tree.item(selected_item)["values"]  # Retrieve paths of the selected files
            if Path(file1).is_file() and Path(file2).is_file():
                # Display file1 on the left canvas
                image1 = Image.open(file1)
                self.display_uploaded(image1)

                # Display file2 on the right canvas
                image2 = Image.open(file2)
                width_factor = self.canvas_selected.winfo_width() / image2.width
                height_factor = self.canvas_selected.winfo_height() / image2.height
                scale_factor = min(width_factor, height_factor)
                resized_image = image2.resize(
                    (int(image2.width * scale_factor), int(image2.height * scale_factor)))
                img = ImageTk.PhotoImage(resized_image)
                x_position = (self.canvas_selected.winfo_width() - resized_image.width) // 2
                y_position = (self.canvas_selected.winfo_height() - resized_image.height) // 2
                self.canvas_selected.delete("all")
                self.canvas_selected.create_image(x_position, y_position, anchor=tk.NW, image=img)
                self.canvas_selected.image = img
                return

        if selected_item:
            selected_file_path = self.tree.item(selected_item)['values'][0]
            selected_file_path = selected_file_path.split(" Similarity:")[0]  # Handle paths with spaces
            selected_file_path = selected_file_path.strip("\"")  # Remove surrounding quotes
            selected_file = Image.open(selected_file_path, 'r')
            width_factor = self.canvas_selected.winfo_width() / selected_file.width
            height_factor = self.canvas_selected.winfo_height() / selected_file.height
            scale_factor = min(width_factor, height_factor)
            resized_image = selected_file.resize(
                (int(selected_file.width * scale_factor), int(selected_file.height * scale_factor)))
            img = ImageTk.PhotoImage(resized_image)
            x_position = (self.canvas_selected.winfo_width() - resized_image.width) // 2
            y_position = (self.canvas_selected.winfo_height() - resized_image.height) // 2
            self.canvas_selected.delete("all")
            self.canvas_selected.create_image(x_position, y_position, anchor=tk.NW, image=img)
            self.canvas_selected.image = img

    def list_files(self, path=Path('.'), include_subfolders=False):
        files = []
        ext = [".png", ".jpg", ".jpeg", ".bmp", ".ppm", ".pgm"]
        path = Path(path)
        try:
            for entry in path.iterdir():
                if entry.is_file() and entry.suffix.lower() in ext:
                    files.append(entry)
                elif entry.is_dir() and include_subfolders:
                    files.extend(self.list_files(entry, include_subfolders))
        except Exception as e:
            print(f"Error accessing {path}: {e}")
        return files

    def search_duplicates(self):
        try:
            self.tree.delete(*self.tree.get_children())
        except Exception as e:
            messagebox.showerror("Error", str(e))

        include_subfolders = self.subfolders.get() == 1
        files = self.list_files(Path(self.folder_path), include_subfolders)
        source_hash = calculate_image_hash(self.target_image_path)

        self.progress["maximum"] = len(files)

        self.search_thread = threading.Thread(target=self._search_duplicates_thread,
                                              args=(files, source_hash))
        self.search_thread.start()

        # if not self.target_image_path or not self.folder_path:
        #     tk.messagebox.showinfo("Info", "Please set both file and folder.")
        # else:
        #     self.stop_search_flag.clear()
        #     self.tree.delete(*self.tree.get_children())
        #     include_subfolders = self.subfolders.get() == 1
        #     files = self.list_files(Path(self.folder_path), include_subfolders)
        #     source_hash = calculate_image_hash(self.target_image_path)
        #
        #     self.progress["maximum"] = len(files)
        #
        #     self.search_thread = threading.Thread(target=self._search_duplicates_thread,
        #                                           args=(files, source_hash))
        #     self.search_thread.start()

    def _search_duplicates_thread(self, files, source_hash):
        start_time = time.time()
        analyzed_files_count = 0
        for count, file in enumerate(files, start=1):
            if self.stop_search_flag.is_set():
                self.status.set(f"Search stopped by user. {analyzed_files_count} files analyzed")
                break
            self.status.set(f"Analyzing {file.name} ({count}/{len(files)})")
            self.root.update_idletasks()
            analyzed_files_count += 1
            if source_hash == calculate_image_hash(file) and self.target_image_path != file:
                print(file)
                self.tree.insert("", tk.END, values=(file, "Duplicate"))
            self.progress["value"] = count
            self.root.update_idletasks()
        else:
            self.status.set(f"Completed. {analyzed_files_count} files analyzed")

        end_time = time.time()
        elapsed_time = end_time - start_time
        if not self.stop_search_flag.is_set() and analyzed_files_count != 0:
            self.status.set(f"Completed in {elapsed_time:.2f} seconds, {analyzed_files_count} files analyzed")
            self.progress["value"] = 0
        else:
            self.status.set(f"No image files found in selected folders. Try ticking the \"Search subfolders\" option")
            self.progress["value"] = 0

        self.reset_ui()
        self.stop_search_button.config(state=tk.DISABLED)

    def duplicate_pairs(self):
        if not self.folder_path:
            tk.messagebox.showinfo("Info", "Please select a folder.")
            return

        self.stop_search_button.config(state=tk.NORMAL)
        self.stop_search_flag.clear()
        self.status.set("Searching for all duplicate pairs...")
        self.progress['value'] = 0

        search_thread = threading.Thread(target=self._duplicate_pairs_thread)
        search_thread.start()

    def _duplicate_pairs_thread(self):
        start_time = time.time()
        self.tree.delete(*self.tree.get_children())  # Clear previous results

        include_subfolders = self.subfolders.get() == 1
        files = self.list_files(Path(self.folder_path), include_subfolders)
        total_files = len(files)
        analyzed_count = 0

        for i, file1 in enumerate(files):
            if self.stop_search_flag.is_set():
                break
            for file2 in files[i + 1:]:
                if self.stop_search_flag.is_set():
                    break
                analyzed_count += 1
                self.status.set(f"Analyzed {analyzed_count} pairs of files")
                self.progress['value'] = (analyzed_count / (total_files * (total_files - 1) / 2)) * 100

                if calculate_image_hash(file1) == calculate_image_hash(file2):
                    self.tree.insert("", "end", values=(file1, file2))

        # After completing the search, display the first duplicate pair (if any)
        if self.tree.get_children():
            first_item = self.tree.get_children()[0]
            file1, file2 = self.tree.item(first_item)["values"]
            self.display_uploaded(Image.open(file1))  # Display file1 in the left canvas
            self.display_selected(Image.open(file2))  # Display file2 in the right canvas

        execution_time = time.time() - start_time
        self.status.set(f"Finished in {execution_time:.2f} seconds.")
        self.stop_search_button.config(state=tk.DISABLED)
        self.progress['value'] = 0

    def search_similar(self):
        try:
            self.tree.delete(*self.tree.get_children())
        except Exception as e:
            messagebox.showerror("Error", str(e))

        try:
            image_uploaded = cv2.imdecode(np.fromfile(self.target_image_path, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
            hist1 = self.calculate_histogram(image_uploaded)
        except Exception as e:
            tk.messagebox.showerror("Error", f"Unable to read source image: {e}")
            return

        include_subfolders = self.subfolders.get() == 1
        files = self.list_files(Path(self.folder_path), include_subfolders)

        self.progress["maximum"] = len(files)

        self.search_thread = threading.Thread(target=self._search_similar_thread,
                                              args=(files, hist1))
        self.search_thread.start()

    def _search_similar_thread(self, files, hist1):
        start_time = time.time()
        analyzed_files_count = 0
        for count, file in enumerate(files, start=1):
            if self.stop_search_flag.is_set():
                self.status.set(f"Search stopped by user. {analyzed_files_count} files analyzed")
                break
            self.status.set(f"Analyzing {file.name} ({count}/{len(files)})")
            self.root.update_idletasks()
            analyzed_files_count += 1
            if file != self.target_image_path:
                image_queued = cv2.imdecode(np.fromfile(file, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
                hist2 = self.calculate_histogram(image_queued)
                similarity = self.compare_histograms(hist1, hist2)
                if similarity >= int(self.sim.get()):
                    self.tree.insert("", tk.END, values=(file, f"{similarity:.2f}"))
            self.progress["value"] = count
            self.root.update_idletasks()
        else:
            self.status.set(f"Completed. {analyzed_files_count} files analyzed")

        end_time = time.time()
        elapsed_time = end_time - start_time
        if not self.stop_search_flag.is_set() and analyzed_files_count != 0:
            self.status.set(f"Completed in {elapsed_time:.2f} seconds, {analyzed_files_count} files analyzed")
            self.progress["value"] = 0
        else:
            self.status.set(f"No image files found in selected folders. Try ticking the \"Search subfolders\" option")
            self.progress["value"] = 0

        self.reset_ui()
        self.stop_search_button.config(state=tk.DISABLED)

    def calculate_histogram(self, image):
        hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        h_hist = cv2.calcHist([hsv_image], [0], None, [256], [0, 256])
        return h_hist

    def compare_histograms(self, hist1, hist2):
        intersection = cv2.compareHist(hist1, hist2, cv2.HISTCMP_INTERSECT)
        similarity = (intersection / (hist1.sum() + hist2.sum() - intersection)) * 100
        return similarity

    # def sift_compare(self):
    #     try:
    #         self.tree.delete(*self.tree.get_children())
    #     except Exception as e:
    #         messagebox.showerror("Error", str(e))
    #
    #     include_subfolders = self.subfolders.get() == 1
    #     files = self.list_files(Path(self.folder_path), include_subfolders)
    #     source_hash = calculate_image_hash(self.target_image_path)
    #
    #     self.progress["maximum"] = len(files)
    #
    #     self.search_thread = threading.Thread(target=self._sift_compare_thread,
    #                                           args=(files, source_hash))
    #     self.search_thread.start()
    #
    # def _sift_compare_thread(self, files):
    #     start_time = time.time()
    #     analyzed_files_count = 0
    #     for count, file in enumerate(files, start=1):
    #         if self.stop_search_flag.is_set():
    #             self.status.set(f"Search stopped by user. {analyzed_files_count} files analyzed")
    #             break
    #
    #         self.status.set(f"Analyzing {file.name} ({count}/{len(files)})")
    #         self.root.update_idletasks()
    #
    #         analyzed_files_count += 1
    #         image = cv2.imdecode(np.fromfile(self.target_image_path, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    #         compare = cv2.imdecode(np.fromfile(file, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    #
    #         sift = cv2.SIFT_create()
    #
    #         kp_1, desc_1 = sift.detectAndCompute(image, None)
    #
    #         kp_2, desc_2 = sift.detectAndCompute(compare, None)
    #
    #
    #
    #         # Convert images to grayscale
    #         first_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    #         second_gray = cv2.cvtColor(compare, cv2.COLOR_BGR2GRAY)
    #
    #         # Compute SSIM between two images
    #         score, diff = structural_similarity(first_gray, second_gray, full=True)
    #         if score <= int(self.sim.get()):
    #             self.tree.insert("", tk.END, values=(file, f"{score * 100:.2f}%"))
    #         print("Similarity Score: {:.3f}%".format(score * 100))
    #
    #         # The diff image contains the actual image differences between the two images
    #         # and is represented as a floating point data type so we must convert the array
    #         # to 8-bit unsigned integers in the range [0,255] before we can use it with OpenCV
    #         diff = (diff * 255).astype("uint8")
    #
    #         # Threshold the difference image, followed by finding contours to
    #         # obtain the regions that differ between the two images
    #         thresh = cv2.threshold(diff, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    #         contours = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    #         contours = contours[0] if len(contours) == 2 else contours[1]
    #
    #         # Highlight differences
    #         # mask = np.zeros(image.shape, dtype='uint8')
    #         # filled = file.copy()
    #
    #         # for c in contours:
    #         #     area = cv2.contourArea(c)
    #         #     if area > 100:
    #         #         x, y, w, h = cv2.boundingRect(c)
    #         #         cv2.rectangle(image, (x, y), (x + w, y + h), (36, 255, 12), 2)
    #         #         cv2.rectangle(compare, (x, y), (x + w, y + h), (36, 255, 12), 2)
    #         #         cv2.drawContours(mask, [c], 0, (0, 255, 0), -1)
    #         # cv2.drawContours(filled, [c], 0, (0, 255, 0), -1)
    #
    #         # if source_hash == calculate_image_hash(file) and self.target_image_path != file:
    #         #     self.tree.insert("", tk.END, values=(file, "Duplicate"))
    #         self.progress["value"] = count
    #         self.root.update_idletasks()
    #     else:
    #         self.status.set(f"Completed. {analyzed_files_count} files analyzed")
    #
    #     end_time = time.time()
    #     elapsed_time = end_time - start_time
    #     if not self.stop_search_flag.is_set():
    #         self.status.set(f"Completed in {elapsed_time:.2f} seconds, {analyzed_files_count} files analyzed")
    #         self.progress["value"] = 0
    #
    #     self.reset_ui()
    #     self.stop_button.config(state=tk.DISABLED)

    def ssim_compare(self):
        try:
            self.tree.delete(*self.tree.get_children())
        except Exception as e:
            messagebox.showerror("Error", str(e))

        include_subfolders = self.subfolders.get() == 1
        files = self.list_files(Path(self.folder_path), include_subfolders)

        self.progress["maximum"] = len(files)

        self.search_thread = threading.Thread(target=self._ssim_compare_thread,
                                              args=files)
        self.search_thread.start()

    def _ssim_compare_thread(self, *files):
        start_time = time.time()
        analyzed_files_count = 0
        for count, file in enumerate(files, start=1):
            if self.stop_search_flag.is_set():
                self.status.set(f"Search stopped by user. {analyzed_files_count} files analyzed")
                break

            self.status.set(f"Analyzing {file.name} ({count}/{len(files)})")
            self.root.update_idletasks()

            if Image.open(self.target_image_path).width == Image.open(file).width and Image.open(self.target_image_path).height == Image.open(file).height:
                analyzed_files_count += 1

                image = cv2.imdecode(np.fromfile(self.target_image_path, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
                compare = cv2.imdecode(np.fromfile(file, dtype=np.uint8), cv2.IMREAD_UNCHANGED)

                # Convert images to grayscale
                first_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                second_gray = cv2.cvtColor(compare, cv2.COLOR_BGR2GRAY)

                # Compute SSIM between two images
                score, diff = structural_similarity(first_gray, second_gray, full=True)
                if score*100 >= int(self.sim.get()):
                    self.tree.insert("", tk.END, values=(file, f"{score*100:.2f}%"))

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
        if not self.stop_search_flag.is_set() and analyzed_files_count != 0:
            self.status.set(f"Completed in {elapsed_time:.2f} seconds, {analyzed_files_count} files analyzed")
            self.progress["value"] = 0
        else:
            self.status.set(f"No image files found in selected folders. Try ticking the \"Search subfolders\" option")
            self.progress["value"] = 0

        self.reset_ui()
        self.stop_search_button.config(state=tk.DISABLED)

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
        self.target_image_label.config(text=self.languages[language]["selected_image"])
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
            language_menu.add_command(label=lang, command=lambda lang=lang: self.change_language(lang))
        settings_menu.add_cascade(label=self.languages[self.current_language]["language"], menu=language_menu)


#run from terminal, experimental
def findSimilar5(self, img_path, folder_path, method):
    try:
        image1 = cv2.imread(Path(img_path))
        hist1 = self.calculate_histogram(image1)
    except Exception as e:
        tk.messagebox.showerror("Error", f"Unable to read source image: {e}")
        return
    files = self.listFiles(Path(folder_path))
    # if method == 1:
    #     self.search_duplicates()
    # elif method == 2:
    #     self.search_similar()
    # elif method == 3:
    #     self.ssim_compare()
    # elif method == 4:
    #     self.duplicate_pairs()
    for file in files:
        if file != img_path:  # Exclude the source image itself
            try:
                image2 = cv2.imread(str(file))
                hist2 = self.calculate_histogram(image2)
                similarity = self.compare_histogram(hist1, hist2)
                if similarity >= 1:
                    print(f"{file} Similarity: {similarity:.2f}%")
            except Exception as e:
                print(f"Error processing file {file}: {e}")


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