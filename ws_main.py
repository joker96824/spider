import tkinter as tk
from ws_gui import WS_SpiderGUI

def main():
    root = tk.Tk()
    app = WS_SpiderGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main() 