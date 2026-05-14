import os
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gio, Gdk

from git.repository import GitRepository
from ui.dialogs.new_repo_dialog import NewRepoDialog
from ui.dialogs.open_repo_dialog import OpenRepoDialog
from ui.widgets.repo_tab import RepoTab


class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, application):
        super().__init__(application=application, title="MySourceTree")

        self.set_default_size(1280, 860)
        self._css_provider = None

        self._build_menu_bar()
        self._load_css()
        self._build_ui()

    def _load_css(self):
        css_path = os.path.join(os.path.dirname(__file__), "..", "ui", "style.css")
        abs_css_path = os.path.abspath(css_path)

        self._css_provider = Gtk.CssProvider()
        if os.path.exists(abs_css_path):
            self._css_provider.load_from_path(abs_css_path)
        else:
            print(f"CSS file not found: {abs_css_path}")
            return

        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            self._css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _build_menu_bar(self):
        """Build a full menu bar matching the SourceTree HTML mockup."""
        menubar = Gtk.PopoverMenuBar()

        # ── 文件(F) ──
        file_menu = Gio.Menu()
        file_menu.append("新建仓库...", "app.new_repo")
        file_menu.append("打开仓库...", "app.open_repo")
        file_menu.append("克隆仓库...", "app.clone_repo")
        file_menu.append("关闭仓库", "app.close_repo")
        file_section = Gio.Menu()
        file_section.append("退出", "app.quit")
        file_menu.append_section(None, file_section)

        file_item = Gtk.PopoverMenuItem.new_from_model(file_menu, "文件(F)")
        menubar.append_item(file_item)

        # ── 编辑(E) ──
        edit_menu = Gio.Menu()
        edit_menu.append("撤销", "app.undo")
        edit_menu.append("重做", "app.redo")
        edit_menu.append("剪切", "app.cut")
        edit_menu.append("复制", "app.copy")
        edit_menu.append("粘贴", "app.paste")

        edit_item = Gtk.PopoverMenuItem.new_from_model(edit_menu, "编辑(E)")
        menubar.append_item(edit_item)

        # ── 查看(V) ──
        view_menu = Gio.Menu()
        view_menu.append("刷新", "app.refresh")
        view_menu.append("显示所有分支", "app.show_all_branches")
        view_menu.append("显示远程分支", "app.show_remote_branches")

        view_item = Gtk.PopoverMenuItem.new_from_model(view_menu, "查看(V)")
        menubar.append_item(view_item)

        # ── 仓库(R) ──
        repo_menu = Gio.Menu()
        repo_menu.append("仓库设置...", "app.repo_settings")
        repo_menu.append("打开终端", "app.open_terminal")
        repo_menu.append("资源管理器", "app.file_manager")

        repo_item = Gtk.PopoverMenuItem.new_from_model(repo_menu, "仓库(R)")
        menubar.append_item(repo_item)

        # ── 操作(A) ──
        action_menu = Gio.Menu()
        action_menu.append("提交...", "app.commit")
        action_menu.append("拉取", "app.pull")
        action_menu.append("推送", "app.push")
        action_menu.append("获取", "app.fetch")
        action_section = Gio.Menu()
        action_section.append("贮藏...", "app.stash")
        action_section.append("合并...", "app.merge")
        action_section.append("创建标签...", "app.create_tag")
        action_menu.append_section(None, action_section)

        action_item = Gtk.PopoverMenuItem.new_from_model(action_menu, "操作(A)")
        menubar.append_item(action_item)

        # ── 工具(T) ──
        tools_menu = Gio.Menu()
        tools_menu.append("Git工作流", "app.git_flow")
        tools_menu.append("命令行模式", "app.terminal_mode")
        tools_menu.append("设置...", "app.settings")

        tools_item = Gtk.PopoverMenuItem.new_from_model(tools_menu, "工具(T)")
        menubar.append_item(tools_item)

        # ── 帮助(H) ──
        help_menu = Gio.Menu()
        help_menu.append("关于 MySourceTree", "app.about")
        help_menu.append("帮助...", "app.help")

        help_item = Gtk.PopoverMenuItem.new_from_model(help_menu, "帮助(H)")
        menubar.append_item(help_item)

        self._menubar = menubar

    def _build_ui(self):
        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # Menu bar
        menu_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        menu_box.add_css_class("menu-bar")
        menu_box.append(self._menubar)
        main_vbox.append(menu_box)

        # Repo notebook (tab bar)
        self.repo_notebook = Gtk.Notebook()
        self.repo_notebook.set_scrollable(True)
        self.repo_notebook.add_css_class("tab-bar")
        self.repo_notebook.connect("switch-page", self.on_switch_repo_tab)

        empty_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        empty_box.set_valign(Gtk.Align.CENTER)
        empty_box.set_halign(Gtk.Align.CENTER)
        empty_lbl = Gtk.Label(label="点击上方 新建/打开 按钮打开仓库\n\n或使用菜单 文件 → 打开仓库")
        empty_lbl.set_halign(Gtk.Align.CENTER)
        empty_lbl.add_css_class("detail-value")
        empty_box.append(empty_lbl)
        self.repo_notebook.append_page(empty_box, Gtk.Label(label="+"))

        main_vbox.append(self.repo_notebook)

        # Status bar
        status_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        status_bar.add_css_class("status-bar")
        self.status_label = Gtk.Label(label="就绪")
        self.status_label.set_halign(Gtk.Align.START)
        self.status_label.set_margin_start(8)
        status_bar.append(self.status_label)
        main_vbox.append(status_bar)

        self.set_child(main_vbox)

    def get_current_repo_tab(self):
        current_page = self.repo_notebook.get_current_page()
        if current_page >= 0:
            child = self.repo_notebook.get_nth_page(current_page)
            if isinstance(child, RepoTab):
                return child
        return None

    def on_switch_repo_tab(self, notebook, page, page_num):
        tab = self.get_current_repo_tab()
        if tab:
            self.status_label.set_label(f"当前仓库: {tab.repo_path}")

    def on_new_button_clicked(self, button):
        self.show_new_repo_dialog()

    def on_open_button_clicked(self, button):
        self.show_open_repo_dialog()

    def show_new_repo_dialog(self):
        dialog = NewRepoDialog(self)
        dialog.connect("response", self.on_new_repo_response)
        dialog.present()

    def show_open_repo_dialog(self):
        dialog = OpenRepoDialog(self)
        dialog.connect("response", self.on_open_repo_response)
        dialog.present()

    def on_new_repo_response(self, dialog, response_id):
        if response_id == Gtk.ResponseType.OK:
            path = dialog.get_path()
            bare = dialog.get_bare()
            try:
                repo = GitRepository()
                repo.create(path, bare=bare)
                self.add_repo_tab(path)
                self.status_label.set_label(f"已创建仓库: {path}")
            except Exception as e:
                self.show_error_dialog(f"创建仓库失败: {str(e)}")
        dialog.destroy()

    def on_open_repo_response(self, dialog, response_id):
        if response_id == Gtk.ResponseType.OK:
            path = dialog.get_path()
            try:
                self.add_repo_tab(path)
                self.status_label.set_label(f"已打开仓库: {path}")
            except Exception as e:
                self.show_error_dialog(f"打开仓库失败: {str(e)}")
        dialog.destroy()

    def add_repo_tab(self, path):
        for i in range(self.repo_notebook.get_n_pages()):
            child = self.repo_notebook.get_nth_page(i)
            if isinstance(child, RepoTab) and child.repo_path == path:
                self.repo_notebook.set_current_page(i)
                return

        tab_label = Gtk.Label(label=os.path.basename(path))
        tab_label.set_margin_end(4)

        close_btn = Gtk.Button()
        close_btn.set_icon_name("window-close-symbolic")
        close_btn.set_has_frame(False)
        close_btn.add_css_class("flat")
        close_btn.connect("clicked", self._on_close_tab, path)

        tab_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        tab_box.append(tab_label)
        tab_box.append(close_btn)

        repo_tab = RepoTab(self, path)
        self.repo_notebook.append_page(repo_tab, tab_box)
        self.repo_notebook.set_current_page(self.repo_notebook.get_n_pages() - 1)
        self.status_label.set_label(f"已打开: {path}")

    def _on_close_tab(self, button, path):
        for i in range(self.repo_notebook.get_n_pages()):
            child = self.repo_notebook.get_nth_page(i)
            if isinstance(child, RepoTab) and child.repo_path == path:
                self.repo_notebook.remove_page(i)
                self.status_label.set_label(f"已关闭: {path}")
                break

    def show_error_dialog(self, message):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="错误",
        )
        dialog.format_secondary_text(message)
        dialog.present()
        dialog.connect("response", lambda dlg, resp: dlg.destroy())

    def do_close_request(self):
        self.get_application().quit()
        return False


# ── Dialogs ─────────────────────────────────────────────────

class CommitDialog(Gtk.Dialog):
    def __init__(self, parent):
        super().__init__(title="提交", transient_for=parent)
        self.add_buttons("取消", Gtk.ResponseType.CANCEL, "提交", Gtk.ResponseType.OK)
        self.set_default_size(400, 250)

        box = self.get_content_area()
        box.set_spacing(10)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)

        box.append(Gtk.Label(label="提交消息:"))
        self.text_view = Gtk.TextView()
        self.text_view.set_size_request(380, 160)
        self.text_view.set_wrap_mode(Gtk.WrapMode.WORD)

        scroll = Gtk.ScrolledWindow()
        scroll.set_child(self.text_view)
        box.append(scroll)

    def get_message(self):
        buf = self.text_view.get_buffer()
        return buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True)


class MergeDialog(Gtk.Dialog):
    def __init__(self, parent):
        super().__init__(title="合并分支", transient_for=parent)
        self.add_buttons("取消", Gtk.ResponseType.CANCEL, "合并", Gtk.ResponseType.OK)

        box = self.get_content_area()
        box.set_spacing(10)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)

        name_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        name_box.append(Gtk.Label(label="目标分支:"))
        self.name_entry = Gtk.Entry()
        self.name_entry.set_hexpand(True)
        name_box.append(self.name_entry)
        box.append(name_box)

    def get_branch_name(self):
        return self.name_entry.get_text()
