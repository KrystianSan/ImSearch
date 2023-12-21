import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import hashlib
from PIL import Image, ImageTk


# def change(path):
#     output = ""
#     for i in path:
#         if i == '\\':
#             output += "/"
#         else:
#             output += i
#     return output


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
        self.root.geometry("1200x800")

        self.folder_path = None
        self.target_image = None
        self.target_image_path = None
        self.image_files = []

        # canvas
        self.canvas_uploaded = tk.Canvas(root, bg="white", relief=tk.GROOVE, bd=4)
        self.canvas_uploaded.pack(side=tk.LEFT, padx=10, pady=200, fill=tk.BOTH)

        self.canvas_selected = tk.Canvas(root, bg="white", relief=tk.GROOVE, bd=4)
        self.canvas_selected.pack(side=tk.RIGHT, padx=10, pady=200, fill=tk.BOTH)


        result_frame = tk.Frame(root)
        result_frame.pack(side=tk.TOP, padx=10, pady=10)

        control_frame = tk.Frame(root)
        control_frame.pack(side=tk.TOP, padx=10, pady=10)

        # folder button
        browse_button = ttk.Button(control_frame, text="Select Folder", command=self.browse_folder)
        browse_button.pack()

        # select image button
        select_target_button = ttk.Button(control_frame, text="Select Query Image", command=self.upload_query_image)
        select_target_button.pack()

        # selected image label
        self.target_image_label = tk.Label(control_frame, text="Selected Query Image: None")
        self.target_image_label.pack()

        # search button
        search_button = ttk.Button(control_frame, text="Search For Duplicates", command=self.search_duplicates)
        search_button.pack()

        self.folders_listbox = tk.Listbox(control_frame, selectmode=tk.MULTIPLE)
        self.folders_listbox.pack(side=tk.TOP, fill=tk.X)


        self.duplicates_listbox = tk.Listbox(result_frame, selectmode=tk.SINGLE)
        self.duplicates_listbox.pack(side=tk.BOTTOM, fill=tk.X)

        #view_properties_button = ttk.Button(control_frame, text="View Properties",
                                            #command=self.create_properties_window)
        #view_properties_button.pack()

        delete_image_button = ttk.Button(control_frame, text="Delete Selected",
                                         command=self.delete_selected)
        delete_image_button.pack()

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
            self.target_image_path = file_path
            self.target_image_label.config(text=f"Selected Target Image: {os.path.basename(file_path)}")
            self.target_image = Image.open(file_path, 'r')
            self.display_uploaded(self.target_image)
        else:
            self.target_image_label.config(text="Selected Target Image: None")
            messagebox.showinfo("Info", "No target image selected")
    def browse_folder(self):
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
        #self.width_target, self.height_target = image
        # self.image1 = self.image1.resize((self.root.winfo_width(), self.root.winfo_height()))
        img = ImageTk.PhotoImage(image)
        # self.image_data1 = self.get_image_data(self.image1)
        # self.image1_rgb = self.image1.convert("RGB")
        # self.pixel_val_selected = self.image1.load()
        self.canvas_uploaded.delete("all")
        show_image = self.canvas_uploaded.create_image(0, 0, anchor=tk.NW, image=img)
        self.canvas_uploaded.image = show_image
        self.image1_rgb.getdata()

    def display_selected(self):
        selected_index = self.duplicates_listbox.curselection()
        if selected_index:
            selected_file = self.duplicates_listbox.get(selected_index)
        # self.width_target, self.height_target = image
        # self.image1 = self.image1.resize((self.root.winfo_width(), self.root.winfo_height()))
            img = ImageTk.PhotoImage(selected_file)
        # self.image_data1 = self.get_image_data(self.image1)
        # self.image1_rgb = self.image1.convert("RGB")
        # self.pixel_val_selected = self.image1.load()
            self.canvas_selected.delete("all")
            show_image = self.canvas_selected.create_image(0, 0, anchor=tk.NW, image=img)
            self.canvas_selected.image = show_image
            self.image1_rgb.getdata()


        # image = Image.open(image_path)
        # photo = ImageTk.PhotoImage(image)
        #
        # image_label = tk.Label(self.control_frame, image=photo)
        # image_label.image = photo
        # image_label.pack()

    #def display_selected_image(self):

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
            #result_window = tk.Toplevel(self.root)
            #result_window.title("Results")

            #duplicates_frame = tk.Frame(result_window)
            #duplicates_frame.pack()

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