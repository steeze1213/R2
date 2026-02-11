import tkinter as tk
from model import Model
from view import View
from controller import Controller

class Dataanal_program(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('data analysis program')
        window = self.geometry('1080x720')

        model = Model()
        view = View(self)
        controller = Controller(model, view)
        view.set_controller(controller)

if __name__ == '__main__':
    app = Dataanal_program()
    app.mainloop()