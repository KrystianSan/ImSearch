import tkinter as tk
import os
import hashlib
import cv2
from pathlib import Path
import time
from tkinter.ttk import *
from tkinter import filedialog, messagebox, ttk, simpledialog
import threading
import numpy as np
from PIL import Image, ImageTk
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

        self.search_combobox = ttk.Combobox(root, values=["Search For Duplicates", "Find Similar"], state="readonly")
        self.search_combobox.place(x=496, y=192, height=34, width=160)
        self.search_combobox.current(0)

        self.search_button = ttk.Button(root, text="Start Search", command=self.perform_search)
        self.search_button.place(x=710, y=192, height=34, width=160)

        self.stop_button = ttk.Button(self.root, text="Stop", command=self.stop_search)
        self.stop_button.place(x=710, y=236, height=34, width=160)
        self.stop_button.config(state=tk.DISABLED)

        self.subfolder_button = ttk.Checkbutton(self.root, text="Search subfolders", variable=self.subfolders,
                                                onvalue=1, offvalue=0)
        self.subfolder_button.place(x=636, y=272)

        self.folders_listbox = tk.Listbox(root, selectmode=tk.SINGLE)
        self.folders_listbox.place(x=232, y=20, height=140, width=902)

        # self.duplicates_listbox = tk.Listbox(root, selectmode=tk.SINGLE)
        # self.duplicates_listbox.place(x=505, y=360, height=320, width=360)

        self.tree = ttk.Treeview(root, columns=("Name", "Similarity"), show="headings", selectmode="browse")
        self.tree.heading("Name", text="Name")
        self.tree.heading("Similarity", text="Similarity (%)")
        self.tree.column("Name", width=250)
        self.tree.column("Similarity", width=110)
        self.tree.place(x=500, y=320, height=360, width=360)
        self.tree.bind("<<TreeviewSelect>>", self.display_selected)

        # self.duplicates_listbox.bind("<<ListboxSelect>>", self.display_selected)
        self.tree.bind("<<TreeviewSelect>>", self.display_selected)

        self.rng = tk.Spinbox(self.root, from_=0, to=100)
        self.rng.delete(0, "end")
        self.rng.insert(0, "50")
        self.rng.place(x=576, y=272, height=20, width=32)
        tk.Label(self.root, text="%", fg="gray").place(x=608, y=272, height=20, width=10)

        # Status Bar with Progress Bar
        self.status = tk.StringVar()
        self.status.set("Ready")
        self.status_bar = ttk.Label(self.root, textvariable=self.status, relief=tk.SUNKEN, anchor='w')
        self.status_bar.place(x=0, y=740, height=28, width=1366)

        self.progress = ttk.Progressbar(self.root, orient="horizontal", length=100, mode="determinate")
        self.progress.place(x=1216, y=742, height=26, width=150)

        # Save and Load Buttons
        save_button = ttk.Button(root, text="Save Results", command=self.save_results)
        save_button.place(x=1062, y=688, height=40, width=100)

        load_button = ttk.Button(root, text="Load Results", command=self.load_results)
        load_button.place(x=1162, y=688, height=40, width=100)

        open_images_button = ttk.Button(self.root, text="Open Images", command=self.open_images)
        open_images_button.place(x=962, y=688, height=40, width=100)

        open_in_explorer_button = ttk.Button(root, text="Open in Explorer", command=self.open_in_explorer)
        open_in_explorer_button.place(x=540, y=688, height=34, width=120)

        delete_image_button = ttk.Button(root, text="Delete Selected", command=self.delete_selected)
        delete_image_button.place(x=700, y=688, height=34, width=120)

    def upload_query_image(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.ppm *.pgm")])
        if file_path:
            self.target_image_path = file_path
            self.target_image_label.config(text=f"Selected Target Image: {os.path.basename(file_path)}")
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
        if selected_folder:
            self.folders_listbox.delete(selected_folder[0])

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

    # def search_subdir(self, target_image_path, folder_path):
    #     target_hash = calculate_image_hash(target_image_path)
    #     duplicates = []
    #     for self.root, _, files in os.walk(folder_path):
    #         for file in files:
    #             if file == target_image_path:
    #                 break
    #             file_path = os.path.join(self.root, file)
    #             current_hash = calculate_image_hash(file_path)
    #             if current_hash == target_hash:
    #                 duplicates.append(file)
    #     return duplicates

    def stop_search(self):
        self.stop_search_flag.set()

    def perform_search(self):
        if not self.target_image_path or not self.folder_path:
            tk.messagebox.showwarning("Warning", "Please set both file and folder.")
        else:
            self.stop_button.config(state=tk.NORMAL)
            self.tree.delete(*self.tree.get_children())
            include_subfolders = self.subfolders.get() == 1
            files = self.list_files(Path(self.folder_path), include_subfolders)
            total_files = len(files)
            self.progress["maximum"] = total_files
            search_type = self.search_combobox.get()
            self.stop_search_flag.clear()
            if search_type == "Search For Duplicates":
                self.search_duplicates()
            elif search_type == "Find Similar":
                self.search_similar()
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
        if not self.target_image_path or not self.folder_path:
            tk.messagebox.showwarning("Warning", "Please set both file and folder.")
        else:
            self.stop_search_flag.clear()
            self.tree.delete(*self.tree.get_children())
            include_subfolders = self.subfolders.get() == 1
            files = self.list_files(Path(self.folder_path), include_subfolders)
            source_hash = calculate_image_hash(self.target_image_path)

            self.progress["maximum"] = len(files)

            self.search_thread = threading.Thread(target=self._search_duplicates_thread,
                                                  args=(files, source_hash))
            self.search_thread.start()

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
                self.tree.insert("", tk.END, values=(file, "Duplicate"))
            self.progress["value"] = count
            self.root.update_idletasks()
        else:
            self.status.set(f"Completed. {analyzed_files_count} files analyzed")

        end_time = time.time()
        elapsed_time = end_time - start_time
        if not self.stop_search_flag.is_set():
            self.status.set(f"Completed in {elapsed_time:.2f} seconds, {analyzed_files_count} files analyzed")
            self.progress["value"] = 0

        self.reset_ui()
        self.stop_button.config(state=tk.DISABLED)

    def search_similar(self):
        if not self.folder_path:
            messagebox.showinfo("Error", "No folder selected")
            return
        if not self.target_image:
            messagebox.showinfo("Error", "No file selected")
            return

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
                if similarity >= int(self.rng.get()):
                    self.tree.insert("", tk.END, values=(file, f"{similarity:.2f}%"))
            self.progress["value"] = count
            self.root.update_idletasks()
        else:
            self.status.set(f"Completed. {analyzed_files_count} files analyzed")

        end_time = time.time()
        elapsed_time = end_time - start_time
        if not self.stop_search_flag.is_set():
            self.status.set(f"Completed in {elapsed_time:.2f} seconds, {analyzed_files_count} files analyzed")
            self.progress["value"] = 0

        self.reset_ui()
        self.stop_button.config(state=tk.DISABLED)

    def calculate_histogram(self, image):
        hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        h_hist = cv2.calcHist([hsv_image], [0], None, [256], [0, 256])
        return h_hist

    def compare_histograms(self, hist1, hist2):
        intersection = cv2.compareHist(hist1, hist2, cv2.HISTCMP_INTERSECT)
        similarity = (intersection / (hist1.sum() + hist2.sum() - intersection)) * 100
        return similarity

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

        similarity_threshold = self.rng.get()
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
                self.target_image = Image.open(target_image_path, 'r')
                self.display_uploaded(self.target_image)

            if similarity_threshold:
                self.rng.delete(0, tk.END)
                self.rng.insert(0, similarity_threshold)

            if search_subfolders:
                self.subfolders.set(1 if search_subfolders == "Yes" else 0)

            messagebox.showinfo("Info", f"Results loaded from {file_path}")

    def open_images(self):
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

if __name__ == "__main__":
    root = tk.Tk()
    app = ImSearch(root)
    root.mainloop()
