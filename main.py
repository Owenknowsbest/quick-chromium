import math
import os
from tkinter import *

import clipboard
from cefpython3 import cefpython as cef
import ctypes
import keyboard
import platform
user32 = ctypes.windll.user32


WindowUtils = cef.WindowUtils()
WINDOWS = (platform.system() == "Windows")
LINUX = (platform.system() == "Linux")
MAC = (platform.system() == "Darwin")


class App(Tk):
    active = True

    def __init__(self):
        super(App, self).__init__()
        self.overrideredirect(True)
        self.height = user32.GetSystemMetrics(1)
        self.pos = 0
        self.targetPos = 0
        self.update_pos()
        self.attributes("-topmost", True)
        # self.bind("<Enter>", self.open)
        # self.bind("<Leave>", self.close)
        keyboard.add_hotkey("ctrl+`", self.toggle)
        keyboard.add_hotkey("ctrl+alt+`", self.open_clipboard)
        self.after(100, self.move_pos)
        # Create the widgets
        self.browser = MainFrame(self)
        self.open()
        self.mainloop()

    def open_clipboard(self, *args):
        self.active = True
        self.open()
        self.browser.browser_frame.browser.LoadUrl(clipboard.paste())

    def toggle(self, *args):
        if self.active:
            self.close()
        else:
            self.open()
        self.active = not self.active

    def open(self, *args):
        self.targetPos = self.height + 1

    def close(self, *args):
        self.targetPos = 0

    def move_pos(self):
        self.pos += (self.targetPos - self.pos) / 100
        self.update_pos()
        self.after(1, self.move_pos)

    def update_pos(self):
        self.geometry(f"{user32.GetSystemMetrics(0)}x{self.height}+0+{math.floor(self.pos - self.height)}")


class MainFrame(Frame):

    def __init__(self, root):
        self.browser_frame = None
        self.navigation_bar = None
        self.root = root

        # Root
        self.root.geometry("900x640")
        Grid.rowconfigure(self.root, 0, weight=1)
        Grid.columnconfigure(self.root, 0, weight=1)

        # MainFrame
        Frame.__init__(self, self.root)
        self.master.title("Tkinter example")
        self.master.protocol("WM_DELETE_WINDOW", self.on_close)
        self.master.bind("<Configure>", self.on_root_configure)
        self.setup_icon()
        self.bind("<Configure>", self.on_configure)
        self.bind("<FocusIn>", self.on_focus_in)
        self.bind("<FocusOut>", self.on_focus_out)

        # NavigationBar
        self.navigation_bar = NavigationBar(self)
        self.navigation_bar.grid(row=0, column=0,
                                 sticky=(N + S + E + W))
        Grid.rowconfigure(self, 0, weight=0)
        Grid.columnconfigure(self, 0, weight=0)

        # BrowserFrame
        self.browser_frame = BrowserFrame(self, self.navigation_bar)
        self.browser_frame.grid(row=1, column=0,
                                sticky=(N + S + E + W))
        Grid.rowconfigure(self, 1, weight=1)
        Grid.columnconfigure(self, 0, weight=1)

        # Pack MainFrame
        self.pack(fill=BOTH, expand=YES)

    def on_root_configure(self, _):
        if self.browser_frame:
            self.browser_frame.on_root_configure()

    def on_configure(self, event):
        if self.browser_frame:
            width = event.width
            height = event.height
            if self.navigation_bar:
                height = height - self.navigation_bar.winfo_height()
            self.browser_frame.on_mainframe_configure(width, height)

    def on_focus_in(self, _):
        pass

    def on_focus_out(self, _):
        pass

    def on_close(self):
        if self.browser_frame:
            self.browser_frame.on_root_close()
            self.browser_frame = None
        else:
            self.master.destroy()

    def get_browser(self):
        if self.browser_frame:
            return self.browser_frame.browser
        return None

    def get_browser_frame(self):
        if self.browser_frame:
            return self.browser_frame
        return None

    def setup_icon(self):
        pass


class BrowserFrame(Frame):

    def __init__(self, mainframe, navigation_bar=None):
        self.navigation_bar = navigation_bar
        self.closing = False
        self.browser = None
        Frame.__init__(self, mainframe)
        self.mainframe = mainframe
        self.bind("<FocusIn>", self.on_focus_in)
        self.bind("<FocusOut>", self.on_focus_out)
        self.bind("<Configure>", self.on_configure)
        """For focus problems see Issue #255 and Issue #535. """
        self.focus_set()

    def embed_browser(self):
        window_info = cef.WindowInfo()
        rect = [0, 0, self.winfo_width(), self.winfo_height()]
        window_info.SetAsChild(self.get_window_handle(), rect)
        self.browser = cef.CreateBrowserSync(window_info,
                                             url="file://"+os.getcwd()+"/index.html")
        assert self.browser
        self.browser.SetClientHandler(LifespanHandler(self))
        self.browser.SetClientHandler(LoadHandler(self))
        self.browser.SetClientHandler(FocusHandler(self))
        self.message_loop_work()

    def get_window_handle(self):
        if MAC:
            # Do not use self.winfo_id() on Mac, because of these issues:
            # 1. Window id sometimes has an invalid negative value (Issue #308).
            # 2. Even with valid window id it crashes during the call to NSView.setAutoresizingMask:
            #    https://github.com/cztomczak/cefpython/issues/309#issuecomment-661094466
            #
            # To fix it using PyObjC package to obtain window handle. If you change structure of windows then you
            # need to do modifications here as well.
            #
            # There is still one issue with this solution. Sometimes there is more than one window, for example when application
            # didn't close cleanly last time Python displays an NSAlert window asking whether to Reopen that window. In such
            # case app will crash and you will see in console:
            # > Fatal Python error: PyEval_RestoreThread: NULL tstate
            # > zsh: abort      python tkinter_.py
            # Error messages related to this: https://github.com/cztomczak/cefpython/issues/441
            #
            # There is yet another issue that might be related as well:
            # https://github.com/cztomczak/cefpython/issues/583

            # noinspection PyUnresolvedReferences
            from AppKit import NSApp
            # noinspection PyUnresolvedReferences
            import objc
            # noinspection PyUnresolvedReferences
            content_view = objc.pyobjc_id(NSApp.windows()[-1].contentView())
            return content_view
        elif self.winfo_id() > 0:
            return self.winfo_id()
        else:
            raise Exception("Couldn't obtain window handle")

    def message_loop_work(self):
        cef.MessageLoopWork()
        self.after(10, self.message_loop_work)

    def on_configure(self, _):
        if not self.browser:
            self.embed_browser()

    def on_root_configure(self):
        # Root <Configure> event will be called when top window is moved
        if self.browser:
            self.browser.NotifyMoveOrResizeStarted()

    def on_mainframe_configure(self, width, height):
        if self.browser:
            if WINDOWS:
                ctypes.windll.user32.SetWindowPos(
                    self.browser.GetWindowHandle(), 0,
                    0, 0, width, height, 0x0002)
            elif LINUX:
                self.browser.SetBounds(0, 0, width, height)
            self.browser.NotifyMoveOrResizeStarted()

    def on_focus_in(self, _):
        if self.browser:
            self.browser.SetFocus(True)

    def on_focus_out(self, _):
        """For focus problems see Issue #255 and Issue #535. """
        if LINUX and self.browser:
            self.browser.SetFocus(False)

    def on_root_close(self):
        if self.browser:
            self.browser.CloseBrowser(True)
            self.clear_browser_references()
        else:
            self.destroy()

    def clear_browser_references(self):
        # Clear browser references that you keep anywhere in your
        # code. All references must be cleared for CEF to shutdown cleanly.
        self.browser = None


class LifespanHandler(object):

    def __init__(self, tkFrame):
        self.tkFrame = tkFrame

    def OnBeforeClose(self, browser, **_):
        self.tkFrame.quit()


class LoadHandler(object):

    def __init__(self, browser_frame):
        self.browser_frame = browser_frame

    def OnLoadStart(self, browser, **_):
        if self.browser_frame.master.navigation_bar:
            self.browser_frame.master.navigation_bar.set_url(browser.GetUrl())


class FocusHandler(object):
    """For focus problems see Issue #255 and Issue #535. """

    def __init__(self, browser_frame):
        self.browser_frame = browser_frame

    def OnTakeFocus(self, next_component, **_):
        pass

    def OnSetFocus(self, source, **_):
        if LINUX:
            return False
        else:
            return True

    def OnGotFocus(self, **_):
        if LINUX:
            self.browser_frame.focus_set()


class NavigationBar(Frame):

    def __init__(self, master):
        self.back_state = NONE
        self.forward_state = NONE
        self.back_image = None
        self.forward_image = None
        self.reload_image = None

        Frame.__init__(self, master)

        # Home button
        self.back_button = Button(self, text="Home", command=self.home)
        self.back_button.grid(row=0, column=0)

        # Back button
        self.back_button = Button(self, text="Back", command=self.go_back)
        self.back_button.grid(row=0, column=1)

        # Forward button
        self.forward_button = Button(self, text="Forward", command=self.go_forward)
        self.forward_button.grid(row=0, column=2)

        # Reload button
        self.reload_button = Button(self, text="Reload", command=self.reload)
        self.reload_button.grid(row=0, column=3)

        # Url entry
        self.url_entry = Entry(self)
        self.url_entry.bind("<Return>", self.on_load_url)
        self.url_entry.bind("<Button-1>", self.on_button1)
        self.url_entry.grid(row=0, column=4,
                            sticky=(N + S + E + W))
        Grid.rowconfigure(self, 0, weight=100)
        Grid.columnconfigure(self, 4, weight=100)

        # Update state of buttons
        self.update_state()

    def home(self):
        if self.master.get_browser():
            self.master.get_browser().LoadUrl("file://"+os.getcwd()+"/index.html")

    def go_back(self):
        if self.master.get_browser():
            self.master.get_browser().GoBack()

    def go_forward(self):
        if self.master.get_browser():
            self.master.get_browser().GoForward()

    def reload(self):
        if self.master.get_browser():
            self.master.get_browser().Reload()

    def set_url(self, url):
        self.url_entry.delete(0, END)
        self.url_entry.insert(0, url)

    def on_load_url(self, _):
        if self.master.get_browser():
            self.master.get_browser().StopLoad()
            self.master.get_browser().LoadUrl(self.url_entry.get())

    def on_button1(self, _):
        """For focus problems see Issue #255 and Issue #535. """
        self.master.master.focus_force()

    def update_state(self):
        browser = self.master.get_browser()
        if not browser:
            if self.back_state != DISABLED:
                self.back_button.config(state=DISABLED)
                self.back_state = DISABLED
            if self.forward_state != DISABLED:
                self.forward_button.config(state=DISABLED)
                self.forward_state = DISABLED
            self.after(100, self.update_state)
            return
        if browser.CanGoBack():
            if self.back_state != NORMAL:
                self.back_button.config(state=NORMAL)
                self.back_state = NORMAL
        else:
            if self.back_state != DISABLED:
                self.back_button.config(state=DISABLED)
                self.back_state = DISABLED
        if browser.CanGoForward():
            if self.forward_state != NORMAL:
                self.forward_button.config(state=NORMAL)
                self.forward_state = NORMAL
        else:
            if self.forward_state != DISABLED:
                self.forward_button.config(state=DISABLED)
                self.forward_state = DISABLED
        self.after(100, self.update_state)


cef.Initialize({})
app = App()
cef.Shutdown()
