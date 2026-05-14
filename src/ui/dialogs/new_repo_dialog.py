import os
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk


class NewRepoDialog(Gtk.Dialog):
    def __init__(self, parent):
        super().__init__(title="创建新仓库", transient_for=parent)
        self.add_buttons(
            "取消", Gtk.ResponseType.CANCEL,
            "创建", Gtk.ResponseType.OK
        )

        self.path = ""
        self.bare = False

        box = self.get_content_area()
        box.set_spacing(10)

        path_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        path_label = Gtk.Label(label="路径:")
        path_label.set_width_chars(10)
        self.path_entry = Gtk.Entry()
        self.path_entry.set_hexpand(True)
        browse_button = Gtk.Button(label="浏览...")
        browse_button.connect("clicked", self.on_browse_clicked)
        path_box.append(path_label)
        path_box.append(self.path_entry)
        path_box.append(browse_button)
        box.append(path_box)

        self.bare_check = Gtk.CheckButton(label="创建为裸仓库")
        box.append(self.bare_check)

        box.show()

    def on_browse_clicked(self, button):
        dialog = Gtk.FileChooserDialog(
            title="选择新仓库的目录",
            transient_for=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER
        )
        dialog.add_buttons(
            "取消", Gtk.ResponseType.CANCEL,
            "选择", Gtk.ResponseType.OK
        )

        def on_response(dlg, response):
            if response == Gtk.ResponseType.OK:
                self.path_entry.set_text(dlg.get_filename())
            dlg.destroy()

        dialog.connect("response", on_response)
        dialog.present()

    def get_path(self):
        return self.path_entry.get_text()

    def get_bare(self):
        return self.bare_check.get_active()