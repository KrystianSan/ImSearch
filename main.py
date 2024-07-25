import tkinter as tk
import os
import hashlib
import cv2
from pathlib import Path
import time
from tkinter.ttk import *
from tkinter import filedialog, messagebox, ttk

import numpy as np
from PIL import Image, ImageTk


def calculate_image_hash(image_path):
    with open(image_path, 'rb') as file:
        image_data = file.read()
        image_hash = hashlib.sha256(image_data).hexdigest()

    return image_hash


class ImSearch:
    def __init__(self, root):
        self.subfolders = tk.IntVar()
        self.time = tk.IntVar()

        self.root = root
        self.root.title("ImSearch")
        self.root.geometry("1366x768")

        self.folder_count = 0
        self.folder_path = None
        self.target_image = None
        self.target_image_path = None
        self.target_image_label = None
        self.include_subfolders = None
        self.image_files = []

        # canvas
        self.canvas_uploaded = tk.Canvas(root, bg="white", relief=tk.SUNKEN)
        self.canvas_uploaded.place(x=64, y=200, height=512, width=400)

        self.canvas_selected = tk.Canvas(root, bg="white", relief=tk.SUNKEN)
        self.canvas_selected.place(x=902, y=200, height=512, width=400)

        # progress bar
        # self.progress = Progressbar(root, orient=tk.HORIZONTAL, length=100, mode='determinate')

        # search time
        # tk.Label = tk.Label(root, self.textvariable=time)

        # folder button
        add_folder = ttk.Button(root, text="Add Folder", command=self.add_folder)
        add_folder.place(x=1162, y=100, height=60, width=140)

        remove_folder = ttk.Button(root, text="Remove Folder", command=self.remove_folder)
        remove_folder.place(x=1162, y=20, height=60, width=140)

        folder_up = ttk.Button(root, text="UP", command=self.move_up)
        folder_up.place(x=64, y=20, height=60, width=140)

        folder_down = ttk.Button(root, text="DOWN", command=self.move_down)
        folder_down.place(x=64, y=100, height=60, width=140)

        # select image button
        select_target_button = ttk.Button(root, text="Upload Query Image", command=self.upload_query_image)
        select_target_button.place(x=174, y=620, height=52, width=180)

        # selected image label
        self.target_image_label = tk.Label(root, text="Selected Target Image: None")
        self.target_image_label.place(x=64, y=720)

        # search button
        duplicate_button = ttk.Button(root, text="Search For Duplicates", command=self.search_duplicates)
        duplicate_button.place(x=696, y=232, height=34, width=160)

        similar_button = ttk.Button(self.root, text="Find Similar", command=self.search_similar)
        similar_button.place(x=516, y=232, height=34, width=160)

        self.subfolder_button = ttk.Checkbutton(self.root, text="Search subfolders", variable=self.subfolders,
                                                onvalue=1, offvalue=0)
        self.subfolder_button.place(x=636, y=272)

        self.folders_listbox = tk.Listbox(root, selectmode=tk.SINGLE)
        self.folders_listbox.place(x=232, y=20, height=140, width=902)

        self.duplicates_listbox = tk.Listbox(root, selectmode=tk.SINGLE)
        self.duplicates_listbox.place(x=505, y=320, height=360, width=360)

        delete_image_button = ttk.Button(root, text="Delete Selected",
                                         command=self.delete_selected)
        delete_image_button.place(x=750, y=688, height=40, width=44)

        self.rng = tk.Spinbox(self.root, from_=0, to=100)
        self.rng.place(x=576, y=272, height=20, width=32)
        tk.Label(self.root, text="%", fg="gray").place(x=608, y=272, height=20, width=10)

        self.duplicates_listbox.bind("<<ListboxSelect>>", self.display_selected)

    def upload_query_image(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.ppm *.pgm")])
        if file_path:
            self.target_image_path = file_path
            self.target_image_label.config(text=f"Selected Target Image: {os.path.basename(file_path)}")
            print(self.target_image_path)
            self.target_image = Image.open(file_path, 'r')
            self.display_uploaded(self.target_image)
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

            if not self.image_files:
                messagebox.showinfo("Info", "No image files found in the selected folder.")
            else:
                self.target_image_label.config(text="Selected Target Image: None")

    def remove_folder(self):
        selected_folder = self.folders_listbox.curselection()
        self.folders_listbox.delete(selected_folder[0])

    def move_up(self):
        selected_index = self.folders_listbox.curselection()
        if selected_index == 0:
            return
        text = self.folders_listbox.get(selected_index)
        self.folders_listbox.delete(selected_index)
        self.folders_listbox.insert(selected_index[0] - 1, text)

    def move_down(self):
        selected_index = self.folders_listbox.curselection()

        if selected_index and selected_index[0] < self.duplicates_listbox.size() - 1:
            selected_item = self.duplicates_listbox.get(selected_index)

            self.folders_listbox.delete(selected_index)

            self.folders_listbox.insert(selected_index[0] + 1, selected_item)

            self.folders_listbox.selection_set(selected_index[0] + 1)

    def search_subdir(self, target_image_path, folder_path):
        target_hash = calculate_image_hash(target_image_path)
        duplicates = []
        for self.root, _, files in os.walk(folder_path):
            for file in files:
                if file == target_image_path:
                    break
                print(file)
                print(target_image_path)
                file_path = os.path.join(self.root, file)
                current_hash = calculate_image_hash(file_path)

                if current_hash == target_hash:
                    duplicates.append(file)

        return duplicates

    def delete_selected(self):
        selected_index = self.duplicates_listbox.curselection()
        if not selected_index:
            messagebox.showinfo("Info", "No image selected")
            return

        selected_file = self.duplicates_listbox.get(selected_index)
        confirmation = messagebox.askyesno("Confirm",
                                           f"Do you want to delete {selected_file}? The file will be deleted from disk")

        if confirmation:
            try:
                os.remove(selected_file)
                self.duplicates_listbox.delete(selected_index)
                messagebox.showinfo("Info", f"Image {selected_file} has been deleted.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete image: {str(e)}")

    def display_uploaded(self, image):
        width_factor = self.canvas_uploaded.winfo_width() / image.width
        height_factor = self.canvas_uploaded.winfo_height() / image.height

        scale_factor = min(width_factor, height_factor)

        resized_image = image.resize((int(image.width * scale_factor),
                                      int(image.height * scale_factor)))

        img = ImageTk.PhotoImage(resized_image)

        x_position = (self.canvas_uploaded.winfo_width() - resized_image.width) // 2
        y_position = (self.canvas_uploaded.winfo_height() - resized_image.height) // 2

        self.canvas_uploaded.delete("all")
        self.canvas_uploaded.create_image(x_position, y_position, anchor=tk.NW, image=img)
        self.canvas_uploaded.image = img

    def display_selected(self, event):
        selected_index = self.duplicates_listbox.curselection()
        if selected_index:
            selected_file_path = self.duplicates_listbox.get(selected_index)
            pos = selected_file_path.find(" Similarity:")
            if pos > -1: selected_file_path = selected_file_path[:pos]
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

    def listFiles(self, path=Path('.'), include_subfolders=False):
        files = []
        ext = [".png", ".jpg", ".jpeg", ".bmp", ".ppm", ".pgm"]
        path = Path(path)
        try:
            for entry in path.iterdir():
                if entry.is_file() and entry.suffix.lower() in ext:
                    files.append(entry)
                elif entry.is_dir() and include_subfolders:
                    files.extend(self.listFiles(entry, include_subfolders))
        except Exception as e:
            print(f"Error accessing {path}: {e}")
        return files

    def search_duplicates(self):
        if not self.target_image_path or not self.folder_path:
            tk.messagebox.showwarning("Warning", "Please set both file and folder.")
        else:
            self.duplicates_listbox.delete(0, tk.END)
            include_subfolders = self.subfolders.get() == 1
            files = self.listFiles(Path(self.folder_path), include_subfolders)
            source_hash = calculate_image_hash(self.target_image_path)
            for file in files:
                if source_hash == calculate_image_hash(file) and self.target_image_path != file:
                    self.duplicates_listbox.insert(tk.END, file)

    def search_similar(self):
        if not self.folder_path:
            messagebox.showinfo("Error", "No folder selected")
            return
        if not self.target_image:
            messagebox.showinfo("Error", "No file selected")
            return

        try:
            self.duplicates_listbox.delete(0, tk.END)
        except Exception as e:
            messagebox.showerror("Error", str(e))

        try:
            image_uploaded = cv2.imdecode(np.fromfile(self.target_image_path, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
            hist1 = self.calculate_histogram(image_uploaded)
        except Exception as e:
            tk.messagebox.showerror("Error", f"Unable to read source image: {e}")
            return

        include_subfolders = self.subfolders.get() == 1
        files = self.listFiles(Path(self.folder_path), include_subfolders)
        for file in files:
            if file != self.target_image_path:
                print(file)
                image_queued = cv2.imdecode(np.fromfile(file, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
                hist2 = self.calculate_histogram(image_queued)
                similarity = self.compare_histograms(hist1, hist2)
                if similarity >= int(self.rng.get()):
                    self.duplicates_listbox.insert(tk.END, f"{file} Similarity: {similarity:.2f}%")


    def calculate_histogram(self, image):
        hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        h_hist = cv2.calcHist([hsv_image], [0], None, [256], [0, 256])

        return h_hist

    def compare_histograms(self, hist1, hist2):

        intersection = cv2.compareHist(hist1, hist2, cv2.HISTCMP_INTERSECT)

        similarity = (intersection / (hist1.sum() + hist2.sum() - intersection)) * 100
        return similarity


if __name__ == "__main__":
    root = tk.Tk()
    app = ImSearch(root)
    root.mainloop()
