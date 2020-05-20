import os
from PIL import Image, ImageTk
import queue
import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
import pathlib


def btn_save_command():
    if settings.disable_editing:
        return

    pil_img = Image.new('RGB', (
                           settings.img_dimensions[0] * int(dimension_x.get()),
                           settings.img_dimensions[1] * int(dimension_y.get())
                          ))

    img_queue = queue.Queue()
    for i in settings.images:
        img_queue.put(i)

    for i in range(0, int(dimension_x.get())):
        for j in range(0, int(dimension_y.get())):
            pil_img.paste(img_queue.get(), (
                settings.img_dimensions[0] * i,
                settings.img_dimensions[1] * j
                ))

    path = settings.image_paths[0]

    pathlib.Path(path+'_').mkdir(exist_ok=True)

    for f in settings.image_paths:
        os.rename(f, os.path.join(path+'_', os.path.basename(f)))

    pil_img.save(path)

    settings.disable_editing = True
    redraw()


def btn_load_images():

    settings.image_paths = tk.filedialog.askopenfilenames()

    if len(settings.image_paths) == 0:
        return

    expected = int(dimension_x.get()) * int(dimension_y.get())

    if len(settings.image_paths) % int(dimension_x.get()) != 0:
        tk.messagebox.showerror("Error", f"Cannot execute: Expected settings.images: {expected}, got: {len(settings.image_paths)}")
        return
    else:
        dimension_y.set(int(len(settings.image_paths) / int(dimension_x.get())))

    settings.images = []

    img = Image.open(settings.image_paths[0])
    settings.img_dimensions = img.size

    settings.images.append(img)
    for p in settings.image_paths[1:]:
        settings.images.append(Image.open(p))

    settings.scale = 500/max(settings.img_dimensions[0]*int(dimension_x.get()), settings.img_dimensions[1]*int(dimension_y.get()))

    settings.disable_editing = True
    redraw()

    try:
        auto_sort()
    except Exception as ex:
        tk.messagebox.showerror("Error", f"Cannot sort:\n: {ex}")

    settings.disable_editing = False
    redraw()


class Img:
    class Side:
        line: list
        image: object
        similarity: int

        def __init__(self, line=None, image=None, difference=float('inf')):
            self.line = line
            self.image = image
            self.difference = difference

    image: Image

    left: Side
    right: Side
    top: Side
    bot: Side

    pos = None

    @staticmethod
    def shift(side, pos):
        return [x + y for x, y in zip({
            0: (0, -1),
            1: (1, 0),
            2: (0, 1),
            3: (-1, 0),
        }[side], pos)]

    def __init__(self, im: Image):
        self.image = im
        all = list(im.getdata())

        width, height = im.size
        pixels = [all[i * width:(i + 1) * width] for i in range(height)]

        self.top = Img.Side(line=pixels[0])
        self.bot = Img.Side(line=pixels[-1])
        self.left = Img.Side(line=[p[0] for p in pixels])
        self.right = Img.Side(line=[p[-1] for p in pixels])

        pass

    def sides(self):
        return [self.top, self.right, self.bot, self.left]

    @staticmethod
    def opposite(side):
        return {
            0: 2,
            1: 3,
            2: 0,
            3: 1
        }[side]

    def __eq__(self, other):
        return self.image == other.image

    def __repr__(self):
        return str(self.pos)

    @staticmethod
    def diffline(line1, line2):
        diff = 0
        for p1, p2 in zip(line1, line2):
            for c1, c2 in zip(p1, p2):
                diff += abs(c1 - c2)

        return diff

    def set_best(self, other: object):
        top_diff, right_diff, bot_diff, left_diff = self.compare(other, True)

        if self.top.difference > top_diff:
            self.top.image = other
            self.top.difference = top_diff

        if self.bot.difference > bot_diff:
            self.bot.image = other
            self.bot.difference = bot_diff

        if self.left.difference > left_diff:
            self.left.image = other
            self.left.difference = left_diff

        if self.right.difference > right_diff:
            self.right.image = other
            self.right.difference = right_diff

    def compare(self, other: object, ignore_set_values=False):
        top_diff = right_diff = bot_diff = left_diff = float('inf')

        if ignore_set_values or self.top.image is None:
            top_diff = self.diffline(self.top.line, other.bot.line)

        if ignore_set_values or self.right.image is None:
            right_diff = self.diffline(self.right.line, other.left.line)

        if ignore_set_values or self.bot.image is None:
            bot_diff = self.diffline(self.bot.line, other.top.line)

        if ignore_set_values or self.left.image is None:
            left_diff = self.diffline(self.left.line, other.right.line)

        return [top_diff, right_diff, bot_diff, left_diff]


def auto_sort():
    # todo: Rewrite and optimize shit out if this

    class Best:
        def __init__(self, to: Img, img: Img, diff: float, side: int):
            self.to = to
            self.img = img
            self.diff = diff
            self.side = side

    imglist = [Img(image) for image in settings.images]

    for i in imglist:
        for i2 in imglist:
            if i != i2:
                i.set_best(i2)

    sorting = True

    start = min(imglist, key=lambda i: i.bot.difference + i.right.difference + i.top.difference + i.left.difference)

    imglist = [Img(image) for image in settings.images]

    imglist.remove(start)

    done = [start]

    for side in start.sides():
        side.image = None
        side.difference = float('inf')

    matrix = []
    for i in range(int(dimension_x.get()) * 5):
        matrix.append([None] * int(dimension_y.get()) * 5)

    start.pos = [int(dimension_x.get())*2, int(dimension_y.get())*2]

    matrix[start.pos[0]][start.pos[1]] = start


    while not len(imglist) == 0:
        best = Best(start, start, float('inf'), 0)
        for d in done:
            for img in imglist:
                cmp = d.compare(img)
                for s, c in enumerate(cmp):
                    if c < best.diff:
                        best = Best(to=d, img=img, diff=c, side=s)

        best.to.sides()[best.side].image = best.img
        best.to.sides()[best.side].difference = best.diff
        best.img.pos = Img.shift(best.side, best.to.pos)
        try:
            if matrix[best.img.pos[0]][best.img.pos[1]] is not None:
                redraw()
                raise Exception("that should have been empty")
        except Exception as ex:
            raise

        matrix[best.img.pos[0]][best.img.pos[1]] = best.img

        imglist.remove(best.img)
        done.append(best.img)

        # fix sides
        for y, line in enumerate(matrix):
            for x, img in enumerate(line):
                # check if cell is not empty
                if img is not None:
                    img: Img
                    for side, s in enumerate(img.sides()):
                        s: Img.Side
                        #check if image's side is not empty
                        if s.image is not None:
                            shift = Img.shift(side, img.pos)
                            m = matrix[shift[0]][shift[1]]
                            if m is None:
                                raise Exception("there should have been image")
                            m: Img
                            m.sides()[Img.opposite(side)].image = img

    settings.images = []

    for x in matrix:
        for y in x:
            if y is not None:
                y: Img
                settings.images.append(y.image)

    pass


def redraw():
    pil_img = Image.new('RGB', (
                           settings.img_dimensions[0] * int(dimension_x.get()),
                           settings.img_dimensions[1] * int(dimension_y.get())
                          ))

    img_queue = queue.Queue()
    for i in settings.images:
        img_queue.put(i)

    for i in range(0, int(dimension_x.get())):
        for j in range(0, int(dimension_y.get())):
            pil_img.paste(img_queue.get(), (
                settings.img_dimensions[0] * i,
                settings.img_dimensions[1] * j
                ))

    # pil_img.show()

    pil_img.thumbnail((500, 500))

    if settings.disable_editing:
        pil_img = pil_img.convert('L')

    global tki
    tki = ImageTk.PhotoImage(image=pil_img, master=canvas)

    canvas.create_image(0, 0, anchor=tk.NW, image=tki)

    for i in range(0, int(dimension_x.get())):
        for j in range(0, int(dimension_y.get())):
            canvas.create_rectangle(
                settings.img_dimensions[0] * i * settings.scale+1,
                settings.img_dimensions[1] * j * settings.scale+1,
                settings.img_dimensions[0] * (i+1) * settings.scale,
                settings.img_dimensions[1] * (j+1) * settings.scale,
                )

    canvas.update()


def mouse_left_click(event):
    if settings.disable_editing:
        return

    global selected
    for i in range(0, int(dimension_x.get())):
        for j in range(0, int(dimension_y.get())):
            if settings.img_dimensions[1] * j * settings.scale+1 < event.y < settings.img_dimensions[1] * (j+1) * settings.scale+1 and \
               settings.img_dimensions[0] * i * settings.scale+1 < event.x < settings.img_dimensions[0] * (i+1) * settings.scale+1:
                new = int(dimension_y.get()) * i + j
                if selected == -1:
                    selected = new
                    canvas.create_rectangle(
                        settings.img_dimensions[0] * i * settings.scale + 1,
                        settings.img_dimensions[1] * j * settings.scale + 1,
                        settings.img_dimensions[0] * (i + 1) * settings.scale,
                        settings.img_dimensions[1] * (j + 1) * settings.scale,
                        outline="red"
                    )
                else:
                    settings.images[new], settings.images[selected] = settings.images[selected], settings.images[new]
                    selected = -1
                    redraw()
    pass


class Settings:
    def __init__(self):
        self.images = []
        self.img_dimensions = (0, 0)
        self.image_paths = None
        self.disable_editing = True


if __name__ == '__main__':
    settings = Settings()

    root = tk.Tk()

    tki = None
    dimensions = 3, 3
    selected = -1

    dimension_x = tk.StringVar()
    dimension_y = tk.StringVar()

    dimension_x.set(3)
    dimension_y.set(4)

    top_frame = tk.Frame(root)
    top_frame.pack(side=tk.TOP)

    tb_x = tk.Entry(top_frame, width=5, text="x", textvariable=dimension_x)
    tb_x.pack(side=tk.LEFT)

    tb_y = tk.Entry(top_frame, width=5, text="y", textvariable=dimension_y)
    tb_y.pack(side=tk.LEFT)

    btn_add_images = tk.Button(top_frame, text="Load images", command=btn_load_images)
    btn_add_images.pack(side=tk.LEFT)

    canvas = tk.Canvas(root, width=500, height=500)
    canvas.bind("<Button-1>", mouse_left_click)
    canvas.pack()

    btn_save = tk.Button(root, text="Save image", command=btn_save_command)
    btn_save.pack()

    # btn_load_settings.images()

    tk.mainloop()
