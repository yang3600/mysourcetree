import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gio

from .window import MainWindow


class MySourceTreeApplication(Gtk.Application):
    def __init__(self):
        super().__init__(
            application_id='com.example.MySourceTree',
            flags=Gio.ApplicationFlags.FLAGS_NONE
        )

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = MainWindow(application=self)
        win.present()

    def do_startup(self):
        Gtk.Application.do_startup(self)
        self._build_menus()

    def _build_menus(self):
        # ── File actions ──
        for name, callback, param_type in [
            ("new_repo", self.on_new_repo, None),
            ("open_repo", self.on_open_repo, None),
            ("clone_repo", self.on_clone_repo, None),
            ("close_repo", self.on_close_repo, None),
            ("quit", self.on_quit, None),
            # ── Edit actions ──
            ("undo", self._noop, None),
            ("redo", self._noop, None),
            ("cut", self._noop, None),
            ("copy", self._noop, None),
            ("paste", self._noop, None),
            # ── View actions ──
            ("refresh", self.on_refresh, None),
            ("show_all_branches", self._noop, None),
            ("show_remote_branches", self._noop, None),
            # ── Repo actions ──
            ("repo_settings", self._noop, None),
            ("open_terminal", self._noop, None),
            ("file_manager", self._noop, None),
            # ── Action actions ──
            ("commit", self._noop, None),
            ("pull", self._noop, None),
            ("push", self._noop, None),
            ("fetch", self._noop, None),
            ("stash", self._noop, None),
            ("merge", self._noop, None),
            ("create_tag", self._noop, None),
            # ── Tool actions ──
            ("git_flow", self._noop, None),
            ("terminal_mode", self._noop, None),
            ("settings", self._noop, None),
            # ── Help actions ──
            ("about", self.on_about, None),
            ("help", self._noop, None),
        ]:
            action = Gio.SimpleAction.new(name, param_type)
            action.connect("activate", callback)
            self.add_action(action)

    # ── Action handlers ─────────────────────────────────────
    def _noop(self, action, param):
        pass

    def on_new_repo(self, action, param):
        win = self.props.active_window
        if win:
            win.show_new_repo_dialog()

    def on_open_repo(self, action, param):
        win = self.props.active_window
        if win:
            win.show_open_repo_dialog()

    def on_clone_repo(self, action, param):
        win = self.props.active_window
        if win:
            win.show_error_dialog("克隆功能开发中...")

    def on_close_repo(self, action, param):
        win = self.props.active_window
        if win:
            tab = win.get_current_repo_tab()
            if tab:
                win._on_close_tab(None, tab.repo_path)

    def on_refresh(self, action, param):
        win = self.props.active_window
        if win:
            tab = win.get_current_repo_tab()
            if tab:
                tab.refresh_ui()
                win.status_label.set_label("已刷新")
            else:
                win.show_error_dialog("请先打开一个仓库")

    def on_about(self, action, param):
        win = self.props.active_window
        dialog = Gtk.AboutDialog(
            transient_for=win,
            program_name="MySourceTree",
            version="1.0.0",
            comments="Linux 原生 Git 客户端 - 类似 SourceTree",
            license_type=Gtk.License.MIT_X11,
        )
        dialog.present()
        dialog.connect("response", lambda dlg, resp: dlg.destroy())

    def on_quit(self, action, param):
        self.quit()
