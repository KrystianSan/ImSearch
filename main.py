import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import hashlib
from PIL import Image, ImageTk


def change(path):
    output = ""
    for i in path:
        if i == '\\':
            output += "/"
        else:
            output += i
    return output


def calculate_image_hash(image_path):
    # calculate hash
    with open(image_path, 'rb') as file:
        image_data = file.read()
        image_hash = hashlib.sha256(image_data).hexdigest()
    return image_hash


def find_duplicates_hash(target_image_path, image_paths):
    target_hash = calculate_image_hash(target_image_path)
    duplicates = []
    for image_path in image_paths:
        if image_path == target_image_path:
            continue

        current_hash = calculate_image_hash(image_path)

        if current_hash == target_hash:
            duplicates.append(image_path)

    return duplicates


class ImSearch:
    def __init__(self, root):
        self.image1_rgb = None
        self.height_target = None
        self.width_target = None
        self.root = root
        self.root.title("ImSearch")
        self.root.geometry("1366x768")

        self.folder_path = None
        self.target_image = None
        self.target_image_path = None
        self.image_files = []

        # canvas
        self.canvas_uploaded = tk.Canvas(root, bg="white", relief=tk.SUNKEN)
        self.canvas_uploaded.place(x=64, y=200, height=512, width=400)

        self.canvas_selected = tk.Canvas(root, bg="white", relief=tk.SUNKEN)
        self.canvas_selected.place(x=902, y=200, height=512, width=400)

        # folder button
        add_folder = ttk.Button(root, text="Add Folder", command=self.add_folder)
        add_folder.place(x=1152, y=100, height=60, width=140)

        remove_folder = ttk.Button(root, text="Remove Folder", command=self.remove_folder)
        remove_folder.place(x=1152, y=20, height=60, width=140)

        folder_up = ttk.Button(root, text="UP", command=self.remove_folder)
        folder_up.place(x=, y=20)

        folder_down = ttk.Button(root, text="DOWN", command=self.remove_folder)
        folder_down.place(x=, y=20)


        # select image button
        select_target_button = ttk.Button(root, text="Upload Query Image", command=self.upload_query_image)
        select_target_button.place(x=174, y=620, height=52, width=180)

        # selected image label
        #self.target_image_label = tk.Label(root, text="Selected Target Image: None")
        #self.target_image_label.pack()

        # search button
        search_button = ttk.Button(root, text="Search For Duplicates", command=self.search_duplicates)
        search_button.place(x=696, y=232, height=34, width=160)

        folders_listbox = tk.Listbox(root, selectmode=tk.MULTIPLE)
        folders_listbox.place(x=232, y=20, height=140, width=902)

        self.duplicates_listbox = tk.Listbox(root, selectmode=tk.SINGLE)
        self.duplicates_listbox.place(x=540, y=335, height=340, width=272)

        delete_image_button = ttk.Button(root, text="Delete Selected",
                                         command=self.delete_selected)
        delete_image_button.place(x=750, y=688, height=40, width=44)

        self.duplicates_listbox.bind("<<ListboxSelect>>", self.display_selected)
        # self.canvas_selected.bind("<Configure>", self.on_window_resized)
        # self.canvas_uploaded.bind("<Configure>", self.on_window_resized)

    # def on_window_resized(event):
    #     event.display_selected_image()
    def upload_query_image(self):
        # file_path = filedialog.askopenfilename(
        #     filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.ppm *.pgm")])
        # if file_path:
        #     #self.target_image = file_path
        #     self.target_image_label.config(text=f"Selected Target Image: {os.path.basename(file_path)}")
        #     #self.display_image(file_path)
        #     self.target_image = Image.open(file_path, 'r')
        #     self.width_target, self.height_target = self.target_image.size
        #     # self.image1 = self.image1.resize((self.root.winfo_width(), self.root.winfo_height()))
        #     show_image1 = ImageTk.PhotoImage(self.target_image)
        #     # self.image_data1 = self.get_image_data(self.image1)
        #     # self.image1_rgb = self.image1.convert("RGB")
        #     # self.pixel_val_selected = self.target_image.load()
        #     self.canvas_selected.delete("all")
        #     show_image = self.canvas_selected.create_image(0, 0, anchor="nw", image=show_image1)
        #     self.canvas_selected.image = show_image
        #     #self.target_image.getdata()
        # else:
        #     self.target_image_label.config(text="Selected Target Image: None")
        #     messagebox.showinfo("Info", "No target image selected")

        file_path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.ppm *.pgm")])
        if file_path:
            file_path = change(file_path)
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
            self.folder_path = folder_path
            self.image_files = [os.path.join(folder_path, file) for file in os.listdir(folder_path) if
                                file.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".ppm"))]

            if not self.image_files:
                messagebox.showinfo("Info", "No image files found in the selected folder.")
            else:
                self.target_image_label.config(text="Selected Target Image: None")
    def remove_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.folder_path = folder_path
            self.image_files = [os.path.join(folder_path, file) for file in os.listdir(folder_path) if
                                file.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".ppm"))]

            if not self.image_files:
                messagebox.showinfo("Info", "No image files found in the selected folder.")
            else:
                self.target_image_label.config(text="Selected Target Image: None")

    def convert_to_grayscale(self):
        if self.image1:
            grayscale_image = self.convert_to_grayscale_image(self.image1)
            self.image_tk = ImageTk.PhotoImage(grayscale_image)
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor="nw", image=self.image_tk)

    def convert_to_grayscale_image(self, image):
        grayscale_image = Image.new("RGB", (self.width1, self.height1))

        for y in range(self.height1):
            for x in range(self.width1):
                r, g, b, a = image.getpixel((x, y))
                grayscale = int(0.299 * r + 0.587 * g + 0.114 * b)
                grayscale_image.putpixel((x, y), (grayscale, grayscale, grayscale))

        return grayscale_image

    # def create_properties_window(self):
    #     properties_window = tk.Toplevel(self.root)
    #     properties_window.title("Image Properties")
    #
    #     properties_frame = tk.Frame(properties_window)
    #     properties_frame.pack(padx=10, pady=10)
    #
    #     selected_file = self.duplicates_listbox.get(self.duplicates_listbox.curselection())
    #     selected_file_label = tk.Label(properties_frame, text="Selected File: " + selected_file)
    #     selected_file_label.pack()

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
        # Calculate scale factors
        width_factor = self.canvas_uploaded.winfo_width() / image.width
        height_factor = self.canvas_uploaded.winfo_height() / image.height

        # Choose the smaller scale factor to maintain aspect ratio
        scale_factor = min(width_factor, height_factor)

        # Resize the image
        resized_image = image.resize((int(image.width * scale_factor),
                                              int(image.height * scale_factor)))

        img = ImageTk.PhotoImage(resized_image)

        # Calculate the position to center the image
        x_position = (self.canvas_uploaded.winfo_width() - resized_image.width) // 2
        y_position = (self.canvas_uploaded.winfo_height() - resized_image.height) // 2

        # Assuming self.canvas_selected is a Tkinter Canvas widget
        self.canvas_uploaded.delete("all")
        show_image = self.canvas_uploaded.create_image(x_position, y_position, anchor=tk.NW, image=img)
        self.canvas_uploaded.image = img  # Keep a reference to prevent garbage collection

    def display_selected(self, event):
        selected_index = self.duplicates_listbox.curselection()
        if selected_index:
            selected_file_path = self.duplicates_listbox.get(selected_index)
            selected_file = Image.open(selected_file_path)

            # Calculate scale factors
            width_factor = self.canvas_selected.winfo_width() / selected_file.width
            height_factor = self.canvas_selected.winfo_height() / selected_file.height

            # Choose the smaller scale factor to maintain aspect ratio
            scale_factor = min(width_factor, height_factor)

            # Resize the image
            resized_image = selected_file.resize((int(selected_file.width * scale_factor),
                                                  int(selected_file.height * scale_factor)))

            img = ImageTk.PhotoImage(resized_image)

            # Calculate the position to center the image
            x_position = (self.canvas_selected.winfo_width() - resized_image.width) // 2
            y_position = (self.canvas_selected.winfo_height() - resized_image.height) // 2

            # Assuming self.canvas_selected is a Tkinter Canvas widget
            self.canvas_selected.delete("all")
            show_image = self.canvas_selected.create_image(x_position, y_position, anchor=tk.NW, image=img)
            self.canvas_selected.image = img  # Keep a reference to prevent garbage collection

            # Resize the canvas to fit the image
            self.canvas_selected.config(scrollregion=self.canvas_selected.bbox(tk.ALL))

    # image = Image.open(image_path)
    # photo = ImageTk.PhotoImage(image)
    #
    # image_label = tk.Label(self.control_frame, image=photo)
    # image_label.image = photo
    # image_label.pack()

    # def display_selected_image(self):

    # img = Image.open(selected_image)
    # img = ImageTk.PhotoImage(img)
    # self.canvas_duplicate.image = img  # Keep a reference to the image to avoid garbage collection
    # self.canvas_duplicate.create_image(0, 0, anchor=tk.NW, image=img)

    def search_duplicates(self):
        if not self.folder_path:
            messagebox.showinfo("Error", "No folder selected")
            return
        if not self.target_image:
            messagebox.showinfo("Error", "No file selected")
            return

        try:
            self.duplicates_listbox.delete(0, tk.END)
            duplicates = find_duplicates_hash(self.target_image_path, self.image_files)

            # result window
            # result_window = tk.Toplevel(self.root)
            # result_window.title("Results")

            # duplicates_frame = tk.Frame(result_window)
            # duplicates_frame.pack()

            # display results in listbox
            for duplicate in duplicates:
                self.duplicates_listbox.insert(tk.END, duplicate)

            # buttons


        except Exception as e:
            messagebox.showerror("Error", str(e))


if __name__ == "__main__":
    root = tk.Tk()
    app = ImSearch(root)
    root.mainloop()
