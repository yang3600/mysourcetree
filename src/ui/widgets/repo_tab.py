import os
import math
import datetime
import cairo
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk, Pango, Graphene, Gsk, GLib

from git.repository import GitRepository


# ── Branch colour palette ──
BRANCH_COLORS = [
    (0xe7, 0x4c, 0x3c),  # red
    (0x2e, 0xcc, 0x71),  # green
    (0xf3, 0x9c, 0x12),  # orange
    (0x9b, 0x59, 0xb6),  # purple
    (0x34, 0x98, 0xdb),  # blue
    (0x1a, 0xbc, 0x9c),  # teal
    (0xe6, 0x7e, 0x22),  # dark orange
    (0x95, 0xa5, 0xa6),  # grey
    (0xf1, 0xc4, 0x0f),  # yellow
    (0x8e, 0x44, 0xad),  # deep purple
]

LANE_WIDTH = 20
DOT_RADIUS = 5


def _color_hex(r, g, b):
    return f"#{r:02x}{g:02x}{b:02x}"


class GraphLaneTracker:
    """Computes lane positions for branch lines across commits."""

    def __init__(self):
        self._branch_lanes = {}   # branch_name -> lane index
        self._lane_branches = {}  # lane index -> branch_name
        self._next_lane = 0
        self._free_lanes = []

    def assign(self, branch_name):
        if branch_name in self._branch_lanes:
            return self._branch_lanes[branch_name]
        if self._free_lanes:
            lane = self._free_lanes.pop(0)
        else:
            lane = self._next_lane
            self._next_lane += 1
        self._branch_lanes[branch_name] = lane
        self._lane_branches[lane] = branch_name
        return lane

    def release(self, branch_name):
        if branch_name in self._branch_lanes:
            lane = self._branch_lanes.pop(branch_name)
            self._lane_branches.pop(lane, None)
            self._free_lanes.append(lane)
            self._free_lanes.sort()

    def get_color(self, branch_name):
        idx = hash(branch_name) % len(BRANCH_COLORS)
        return BRANCH_COLORS[idx]

    def get_lane(self, branch_name):
        return self._branch_lanes.get(branch_name)


class CommitGraphWidget(Gtk.DrawingArea):
    """Custom drawing widget for a single row's commit graph."""

    def __init__(self, row_data=None):
        super().__init__()
        self.row_data = row_data or {}
        self.set_size_request(200, 26)
        self.set_draw_func(self._draw)

    def _draw(self, area, cr, width, height):
        data = self.row_data
        if not data:
            return

        cr.set_line_width(2.5)
        mid_y = height / 2

        lanes = data.get("lanes", {})
        merges = data.get("merges", [])
        dot_color = data.get("dot_color")
        dot_lane = data.get("dot_lane", 0)
        labels = data.get("labels", [])
        is_first = data.get("is_first_row", False)
        is_last = data.get("is_last_row", False)

        # Draw vertical lane lines
        for lane_idx in sorted(lanes.keys()):
            x = 20 + lane_idx * LANE_WIDTH
            r, g, b = lanes[lane_idx]
            cr.set_source_rgb(r / 255, g / 255, b / 255)

            top_y = 0 if is_first else 0
            bottom_y = height if is_last else height

            cr.move_to(x, top_y)
            cr.line_to(x, bottom_y)
            cr.stroke()

        # Draw merge curves
        for merge in merges:
            from_lane = merge["from"]
            to_lane = merge["to"]
            color = merge.get("color", BRANCH_COLORS[0])
            cr.set_source_rgb(color[0] / 255, color[1] / 255, color[2] / 255)
            cr.set_line_width(2.0)

            x1 = 20 + from_lane * LANE_WIDTH
            x2 = 20 + to_lane * LANE_WIDTH
            cx = (x1 + x2) / 2

            cr.move_to(x1, 0 if is_first else 0)
            cr.curve_to(x1, mid_y - 4, cx, mid_y - 4, x2 if merges.index(merge) == len(merges) - 1 else cx, mid_y)
            cr.stroke()

            cr.set_line_width(2.5)

        # Draw commit dot
        if dot_color:
            dot_x = 20 + dot_lane * LANE_WIDTH
            r, g, b = dot_color
            cr.set_source_rgb(r / 255, g / 255, b / 255)
            cr.arc(dot_x, mid_y, DOT_RADIUS, 0, 2 * math.pi)
            cr.fill()

            # White stroke around dot
            cr.set_source_rgb(1, 1, 1)
            cr.set_line_width(2)
            cr.arc(dot_x, mid_y, DOT_RADIUS, 0, 2 * math.pi)
            cr.stroke()

        # Draw branch labels next to the graph
        label_x = 20 + (max(lanes.keys()) + 1) * LANE_WIDTH + 8 if lanes else 100
        cr.set_font_size(10)
        for label_info in labels:
            cr.set_source_rgb(
                label_info["color"][0] / 255,
                label_info["color"][1] / 255,
                label_info["color"][2] / 255,
            )
            cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            cr.move_to(label_x, mid_y + 4)
            cr.show_text(label_info["text"])
            label_x += cr.text_extents(label_info["text"]).width + 14


class RepoTab(Gtk.Box):
    def __init__(self, parent, repo_path):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.parent_window = parent
        self.repo_path = repo_path
        self.repo = GitRepository()
        self.repo.open(repo_path)

        self._graph_rows = []
        self._branch_commits = {}
        self._build_action_bar()
        self._build_main_area()
        self.refresh_ui()

    # ── Action Bar ──────────────────────────────────────────
    def _build_action_bar(self):
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        bar.set_margin_top(4)
        bar.set_margin_bottom(4)

        # Group 1: Commit / Pull / Push / Fetch
        g1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        g1.set_margin_start(8)
        for icon, label, cb in [
            ("↑", "提交", self.on_commit),
            ("↓", "拉取", self.on_pull),
            ("↑", "推送", self.on_push),
            ("↓", "获取", self.on_fetch),
        ]:
            btn = self._make_action_btn(icon, label, cb)
            g1.append(btn)
        bar.append(g1)
        bar.append(self._vsep())

        # Group 2: Branch / Merge / Stash / Tag
        g2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        for icon, label, cb in [
            ("⎇", "分支", self.on_branch),
            ("🔀", "合并", self.on_merge),
            ("💾", "贮藏", self.on_stash),
            ("🏷", "标签", self.on_tag),
        ]:
            btn = self._make_action_btn(icon, label, cb)
            g2.append(btn)
        bar.append(g2)
        bar.append(self._vsep())

        # Group 3: right-aligned filters
        g3 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        g3.set_margin_end(8)
        g3.set_hexpand(True)
        g3.set_halign(Gtk.Align.END)

        for name in ["Git工作流", "远端", "命令行模式", "资源管理器"]:
            btn = Gtk.Button(label=name)
            btn.add_css_class("filter-btn")
            g3.append(btn)

        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Author Name")
        self.search_entry.set_size_request(150, -1)
        self.search_entry.connect("search-changed", self.on_search)
        g3.append(self.search_entry)

        jump_btn = Gtk.Button(label="跳转到:")
        jump_btn.add_css_class("filter-btn")
        g3.append(jump_btn)

        bar.append(g3)
        self.append(bar)

    def _make_action_btn(self, icon_text, label, callback):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        icon_lbl = Gtk.Label(label=icon_text)
        icon_lbl.add_css_class("action-icon")
        text_lbl = Gtk.Label(label=label)
        text_lbl.set_css_classes(["action-label"])
        vbox.append(icon_lbl)
        vbox.append(text_lbl)

        btn = Gtk.Button()
        btn.set_child(vbox)
        btn.add_css_class("action-btn")
        btn.connect("clicked", callback)
        return btn

    def _vsep(self):
        sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        sep.set_margin_top(4)
        sep.set_margin_bottom(4)
        sep.add_css_class("separator-v")
        return sep

    # ── Main Area ───────────────────────────────────────────
    def _build_main_area(self):
        self.v_paned = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
        self.v_paned.set_position(460)

        self.h_paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.h_paned.set_position(220)

        self.sidebar = Sidebar(self)
        sidebar_scroll = Gtk.ScrolledWindow()
        sidebar_scroll.set_child(self.sidebar)
        sidebar_scroll.set_size_request(220, -1)
        sidebar_scroll.add_css_class("sidebar")
        self.h_paned.set_start_child(sidebar_scroll)

        self.commit_view = CommitHistoryView(self)
        self.h_paned.set_end_child(self.commit_view)

        self.v_paned.set_start_child(self.h_paned)

        self.bottom_panel = BottomPanel(self)
        self.v_paned.set_end_child(self.bottom_panel)

        self.append(self.v_paned)

    def get_repo_name(self):
        return os.path.basename(self.repo_path)

    def refresh_ui(self):
        self.sidebar.refresh()
        self.commit_view.refresh()
        self.bottom_panel.clear()

    # ── Actions ─────────────────────────────────────────────
    def on_commit(self, btn):
        from app.window import CommitDialog
        dialog = CommitDialog(self.parent_window)
        dialog.connect("response", self._on_commit_response)
        dialog.present()

    def _on_commit_response(self, dialog, response_id):
        if response_id == Gtk.ResponseType.OK:
            message = dialog.get_message()
            if message.strip():
                try:
                    self.repo.commit(message)
                    self.refresh_ui()
                except Exception as e:
                    self.show_error(f"提交失败: {str(e)}")
            else:
                self.show_error("提交消息不能为空")
        dialog.destroy()

    def on_pull(self, btn):
        try:
            self.repo.pull()
            self.refresh_ui()
        except Exception as e:
            self.show_error(f"拉取失败: {str(e)}")

    def on_push(self, btn):
        try:
            self.repo.push()
            self.refresh_ui()
        except Exception as e:
            self.show_error(f"推送失败: {str(e)}")

    def on_fetch(self, btn):
        try:
            self.repo.fetch()
            self.refresh_ui()
        except Exception as e:
            self.show_error(f"获取失败: {str(e)}")

    def on_branch(self, btn):
        dialog = Gtk.Dialog(title="创建分支", transient_for=self.parent_window)
        dialog.add_buttons("取消", Gtk.ResponseType.CANCEL, "创建", Gtk.ResponseType.OK)
        box = dialog.get_content_area()
        box.set_spacing(10)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.append(Gtk.Label(label="分支名称:"))
        entry = Gtk.Entry()
        entry.set_placeholder_text("分支名称")
        box.append(entry)
        dialog.connect("response", lambda dlg, resp: self._on_create_branch(resp, dlg, entry))
        dialog.present()

    def _on_create_branch(self, response_id, dialog, entry):
        if response_id == Gtk.ResponseType.OK and entry.get_text().strip():
            try:
                self.repo.create_branch(entry.get_text().strip())
                self.refresh_ui()
            except Exception as e:
                self.show_error(f"创建分支失败: {str(e)}")
        dialog.destroy()

    def on_merge(self, btn):
        from app.window import MergeDialog
        dialog = MergeDialog(self.parent_window)
        dialog.connect("response", self._on_merge_response)
        dialog.present()

    def _on_merge_response(self, dialog, response_id):
        if response_id == Gtk.ResponseType.OK:
            branch_name = dialog.get_branch_name()
            if branch_name.strip():
                try:
                    self.repo.merge(branch_name)
                    self.refresh_ui()
                except Exception as e:
                    self.show_error(f"合并失败: {str(e)}")
        dialog.destroy()

    def on_stash(self, btn):
        try:
            self.repo.stash()
            self.refresh_ui()
        except Exception as e:
            self.show_error(f"贮藏失败: {str(e)}")

    def on_tag(self, btn):
        dialog = Gtk.Dialog(title="创建标签", transient_for=self.parent_window)
        dialog.add_buttons("取消", Gtk.ResponseType.CANCEL, "创建", Gtk.ResponseType.OK)
        box = dialog.get_content_area()
        box.set_spacing(10)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.append(Gtk.Label(label="标签名称:"))
        name_entry = Gtk.Entry()
        box.append(name_entry)
        box.append(Gtk.Label(label="消息:"))
        text_view = Gtk.TextView()
        text_view.set_size_request(300, 80)
        box.append(text_view)
        dialog.connect("response", lambda dlg, resp: self._on_create_tag(resp, dlg, name_entry, text_view))
        dialog.present()

    def _on_create_tag(self, response_id, dialog, name_entry, text_view):
        if response_id == Gtk.ResponseType.OK and name_entry.get_text().strip():
            buf = text_view.get_buffer()
            msg = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True)
            try:
                self.repo.create_tag(name_entry.get_text().strip(), msg)
                self.refresh_ui()
            except Exception as e:
                self.show_error(f"创建标签失败: {str(e)}")
        dialog.destroy()

    def on_search(self, entry):
        self.commit_view.set_search(entry.get_text())

    def show_error(self, message):
        dialog = Gtk.MessageDialog(
            transient_for=self.parent_window,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="错误",
        )
        dialog.format_secondary_text(message)
        dialog.present()
        dialog.connect("response", lambda dlg, resp: dlg.destroy())


# ═══════════════════════════════════════════════════════════════
#  SIDEBAR
# ═══════════════════════════════════════════════════════════════

class Sidebar(Gtk.Box):
    def __init__(self, parent):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.parent = parent
        self._build()

    def _build(self):
        # Workspace section
        ws_header = Gtk.Label(label="WORKSPACE")
        ws_header.set_halign(Gtk.Align.START)
        ws_header.set_margin_start(8)
        ws_header.set_margin_top(8)
        ws_header.set_margin_bottom(4)
        ws_header.add_css_class("sidebar-header")
        self.append(ws_header)

        self.history_btn = Gtk.Button(label="History")
        self.history_btn.set_halign(Gtk.Align.FILL)
        self.history_btn.set_margin_start(8)
        self.history_btn.set_margin_end(8)
        self.history_btn.add_css_class("sidebar-item")
        self.history_btn.add_css_class("active")
        self.append(self.history_btn)

        search_btn = Gtk.Button(label="Search")
        search_btn.set_halign(Gtk.Align.FILL)
        search_btn.set_margin_start(8)
        search_btn.set_margin_end(8)
        search_btn.add_css_class("sidebar-item")
        self.append(search_btn)

        # Search box
        search_hdr = Gtk.Label(label="🔍 搜索")
        search_hdr.set_halign(Gtk.Align.START)
        search_hdr.set_margin_start(8)
        search_hdr.set_margin_top(12)
        search_hdr.set_margin_bottom(4)
        search_hdr.add_css_class("sidebar-header")
        self.append(search_hdr)

        self.sidebar_search = Gtk.SearchEntry()
        self.sidebar_search.set_placeholder_text("搜索分支/标签...")
        self.sidebar_search.set_margin_start(8)
        self.sidebar_search.set_margin_end(8)
        self.sidebar_search.connect("search-changed", self._on_search)
        self.append(self.sidebar_search)

        # Tree view for branches / tags / remotes / stashes
        self.tree_store = Gtk.TreeStore(str, str, str)  # label, id, type
        self.tree_view = Gtk.TreeView(model=self.tree_store)
        self.tree_view.set_headers_visible(False)
        self.tree_view.set_margin_top(8)
        self.tree_view.set_margin_start(4)
        self.tree_view.set_margin_end(4)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("", renderer, text=0)
        self.tree_view.append_column(column)
        self.tree_view.get_selection().connect("changed", self._on_selection)

        tree_scroll = Gtk.ScrolledWindow()
        tree_scroll.set_child(self.tree_view)
        tree_scroll.set_vexpand(True)
        self.append(tree_scroll)

    def refresh(self):
        self.tree_store.clear()

        branches_hdr = self.tree_store.append(None, ["⎇ 分支", "", "header"])
        tags_hdr = self.tree_store.append(None, ["🏷 标签", "", "header"])
        remotes_hdr = self.tree_store.append(None, ["🌐 远程", "", "header"])
        stashes_hdr = self.tree_store.append(None, ["📦 贮藏", "", "header"])

        if not self.parent.repo or not self.parent.repo.repo:
            self.tree_view.expand_all()
            return

        try:
            branches = self.parent.repo.get_branches()
            current_branch = self.parent.repo.get_current_branch()

            for branch in branches.get("local", []):
                prefix = "● " if branch == current_branch else "  "
                self.tree_store.append(branches_hdr, [f"{prefix}{branch}", f"branch:{branch}", "branch"])

            for remote in branches.get("remote", []):
                self.tree_store.append(remotes_hdr, [f"  {remote}", f"remote:{remote}", "remote"])

            tags = self.parent.repo.get_tags()
            for tag in tags:
                self.tree_store.append(tags_hdr, [f"  {tag}", f"tag:{tag}", "tag"])
        except Exception:
            pass

        self.tree_view.expand_all()

    def _on_search(self, entry):
        pass

    def _on_selection(self, selection):
        model, paths = selection.get_selected_rows()
        if paths:
            it = model.get_iter(paths[0])
            view_id = model.get_value(it, 1)
            if view_id.startswith("branch:"):
                branch = view_id.replace("branch:", "")
                self.parent.commit_view.filter_by_branch(branch)


# ═══════════════════════════════════════════════════════════════
#  COMMIT HISTORY VIEW
# ═══════════════════════════════════════════════════════════════

class CommitHistoryView(Gtk.Box):
    def __init__(self, parent):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.parent = parent
        self.search_text = ""
        self.filter_branch = None

        self._build_header()
        self._build_list()

    def _build_header(self):
        hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        hdr.add_css_class("commit-view-header")
        hdr.set_margin_top(0)
        hdr.set_margin_bottom(0)

        for text, width in [("图谱", 200), ("描述", -1), ("日期", 150), ("作者", 250), ("提交", 80)]:
            lbl = Gtk.Label(label=text)
            lbl.set_halign(Gtk.Align.START)
            lbl.set_margin_start(8)
            lbl.set_margin_top(4)
            lbl.set_margin_bottom(4)
            if width > 0:
                lbl.set_size_request(width, -1)
            else:
                lbl.set_hexpand(True)
            lbl.add_css_class("commit-header-label")
            hdr.append(lbl)

        hdr.add_css_class("commit-header")
        self.append(hdr)

    def _build_list(self):
        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_hexpand(True)
        self.scroll.set_vexpand(True)

        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.list_box.connect("row-selected", self._on_row_selected)
        self.list_box.add_css_class("commit-list")

        self.scroll.set_child(self.list_box)
        self.append(self.scroll)

    def set_search(self, text):
        self.search_text = text
        self.refresh()

    def filter_by_branch(self, branch):
        self.filter_branch = branch
        self.refresh()

    def _on_row_selected(self, list_box, row):
        if row:
            commit = getattr(row, "commit_data", None)
            if commit:
                self.parent.bottom_panel.show_commit_detail(commit)

    def refresh(self):
        self.list_box.remove_all()

        if not self.parent.repo or not self.parent.repo.repo:
            row = Gtk.Label(label="未打开仓库")
            row.set_margin_top(20)
            self.list_box.append(row)
            return

        try:
            commits = self.parent.repo.get_commits(max_count=100)
            if not commits:
                row = Gtk.Label(label="无提交记录")
                row.set_margin_top(20)
                self.list_box.append(row)
                return

            # Build branch → commit mapping
            branch_commits = {}
            branch_color_map = {}
            branches = self.parent.repo.get_branches()
            repo = self.parent.repo.repo

            for bname in branches.get("local", []):
                ref_name = f"refs/heads/{bname}"
                if ref_name in repo.references:
                    cid = str(repo.references[ref_name].target)
                    branch_commits.setdefault(cid, []).append(bname)
                    idx = hash(bname) % len(BRANCH_COLORS)
                    branch_color_map[bname] = BRANCH_COLORS[idx]

            for bname in branches.get("remote", []):
                ref_name = f"refs/remotes/{bname}"
                if ref_name in repo.references:
                    cid = str(repo.references[ref_name].target)
                    branch_commits.setdefault(cid, []).append(bname)
                    idx = hash(bname.split("/")[-1]) % len(BRANCH_COLORS)
                    branch_color_map[bname] = BRANCH_COLORS[idx]

            # Compute graph topology
            tracker = GraphLaneTracker()
            graph_data_rows = []

            # We'll go through commits, assigning lanes for branches that appear
            active_branches = set()
            commit_branch_map = {}

            # First pass: for each commit, find which branches point to it
            # Also find which branches' tip commits are ancestors
            for c in commits:
                cid = c["id"]
                cid_branches = branch_commits.get(cid, [])
                for bname in cid_branches:
                    commit_branch_map.setdefault(cid, set()).add(bname)

            # Build a simplified lane tracking by walking commits
            for i, c in enumerate(commits):
                cid = c["id"]
                cid_branches = branch_commits.get(cid, [])

                # Assign lanes for new branches
                for bname in cid_branches:
                    if bname not in active_branches:
                        tracker.assign(bname)
                        active_branches.add(bname)

                # Build lane color map for this row
                lanes = {}
                for bname in list(active_branches):
                    lane = tracker.get_lane(bname)
                    if lane is not None:
                        lanes[lane] = branch_color_map.get(bname, BRANCH_COLORS[0])

                # Determine which branch(es) this commit belongs to
                # For the dot, use the earliest branch or current branch
                dot_lane = 0
                dot_color = BRANCH_COLORS[0]
                if cid_branches:
                    primary_branch = cid_branches[0]
                    dot_lane = tracker.get_lane(primary_branch) or 0
                    dot_color = branch_color_map.get(primary_branch, BRANCH_COLORS[0])
                elif lanes:
                    dot_lane = min(lanes.keys())
                    dot_color = lanes[dot_lane]

                # Labels for branches at this commit
                labels = []
                for bname in cid_branches:
                    labels.append({
                        "text": bname.split("/")[-1],
                        "color": branch_color_map.get(bname, BRANCH_COLORS[0]),
                    })

                # Detect merges
                merges = []
                parents = c.get("parents", [])
                if len(parents) > 1 and cid_branches:
                    main_branch = cid_branches[0]
                    main_lane = tracker.get_lane(main_branch) or 0
                    for p in parents[1:]:
                        p_branches = branch_commits.get(p, [])
                        for pb in p_branches:
                            p_lane = tracker.get_lane(pb)
                            if p_lane is not None and p_lane != main_lane:
                                merges.append({
                                    "from": p_lane,
                                    "to": main_lane,
                                    "color": branch_color_map.get(pb, BRANCH_COLORS[0]),
                                })

                graph_data_rows.append({
                    "lanes": lanes,
                    "dot_lane": dot_lane,
                    "dot_color": dot_color,
                    "labels": labels,
                    "merges": merges,
                })

            # Second pass: render rows
            for i, c in enumerate(commits):
                cid = c["id"]

                if self.filter_branch:
                    cid_branches = branch_commits.get(cid, [])
                    if self.filter_branch not in cid_branches:
                        # Check if commit is ancestor of filtered branch
                        # Simplified: check branch_commits
                        found = False
                        for br_name in cid_branches:
                            if self.filter_branch in br_name:
                                found = True
                                break
                        if not found:
                            continue

                if self.search_text:
                    search_lower = self.search_text.lower()
                    if (search_lower not in c["author"].lower() and
                            search_lower not in c["message"].lower()):
                        continue

                gdata = graph_data_rows[i] if i < len(graph_data_rows) else {}
                gdata["is_first_row"] = (i == 0)
                gdata["is_last_row"] = (i == len(commits) - 1)

                row = self._make_commit_row(c, gdata, branch_commits.get(cid, []), branch_color_map)
                self.list_box.append(row)

        except Exception as e:
            row = Gtk.Label(label=f"错误: {str(e)}")
            row.set_margin_top(20)
            self.list_box.append(row)

    def _make_commit_row(self, commit, gdata, cid_branches, branch_color_map):
        row = Gtk.ListBoxRow()
        row.commit_data = commit
        row.add_css_class("commit-row")

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)

        # Graph column
        graph_widget = CommitGraphWidget(gdata)
        graph_widget.set_size_request(200, 26)
        hbox.append(graph_widget)

        # Description: branch tags + message
        desc_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)

        # Branch tag badges
        for bname in cid_branches:
            color = branch_color_map.get(bname, BRANCH_COLORS[0])
            hex_color = _color_hex(*color)
            tag_lbl = Gtk.Label(label=bname)
            tag_lbl.set_css_classes(["branch-tag"])
            tag_lbl.set_name(f"tag-{bname}")
            # Use inline CSS via markup
            short_name = bname.split("/")[-1]
            tag_lbl.set_markup(
                f'<span background="{hex_color}" foreground="white" size="x-small"> {bname} </span>'
            )
            tag_lbl.set_margin_end(2)
            desc_box.append(tag_lbl)

        msg = commit["message"].strip().split("\n")[0]
        msg_lbl = Gtk.Label(label=msg)
        msg_lbl.set_halign(Gtk.Align.START)
        msg_lbl.set_ellipsize(Pango.EllipsizeMode.END)
        msg_lbl.set_max_width_chars(80)
        msg_lbl.add_css_class("commit-message")
        desc_box.append(msg_lbl)

        desc_box.set_hexpand(True)
        hbox.append(desc_box)

        # Date
        dt = datetime.datetime.fromtimestamp(commit["time"])
        date_lbl = Gtk.Label(label=dt.strftime("%Y-%m-%d %H:%M"))
        date_lbl.set_size_request(150, -1)
        date_lbl.set_margin_start(8)
        date_lbl.add_css_class("commit-date")
        hbox.append(date_lbl)

        # Author
        author_text = f'{commit["author"]} <{commit["email"]}>'
        author_lbl = Gtk.Label(label=author_text)
        author_lbl.set_size_request(250, -1)
        author_lbl.set_margin_start(8)
        author_lbl.set_ellipsize(Pango.EllipsizeMode.END)
        author_lbl.add_css_class("commit-author")
        hbox.append(author_lbl)

        # Hash
        hash_lbl = Gtk.Label(label=commit["id"][:10])
        hash_lbl.set_size_request(80, -1)
        hash_lbl.set_margin_start(8)
        hash_lbl.add_css_class("commit-hash")
        hbox.append(hash_lbl)

        row.set_child(hbox)
        return row

    def _format_date(self, timestamp):
        dt = datetime.datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M")


# ═══════════════════════════════════════════════════════════════
#  BOTTOM PANEL  (commit detail + diff viewer)
# ═══════════════════════════════════════════════════════════════

class BottomPanel(Gtk.Box):
    def __init__(self, parent):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.parent = parent
        self.set_size_request(-1, 280)
        self._build()

    def _build(self):
        # Tab bar
        tab_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        tab_bar.add_css_class("bottom-tabs")

        self.status_tab = Gtk.Button(label="已按照文件状态排序")
        self.status_tab.add_css_class("bottom-tab")
        tab_bar.append(self.status_tab)

        self.files_tab = Gtk.Button(label="1 文件")
        self.files_tab.add_css_class("bottom-tab")
        self.files_tab.add_css_class("active")
        tab_bar.append(self.files_tab)

        self.append(tab_bar)

        # Content area: detail + code
        hpaned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)

        self.detail_panel = self._build_detail()
        hpaned.set_start_child(self.detail_panel)

        self.code_panel = self._build_code_panel()
        hpaned.set_end_child(self.code_panel)

        hpaned.set_position(380)
        self.append(hpaned)

    def _build_detail(self):
        scroll = Gtk.ScrolledWindow()
        scroll.set_size_request(380, -1)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        box.add_css_class("detail-panel")

        self.lbl_commit = Gtk.Label()
        self.lbl_commit.set_halign(Gtk.Align.START)
        self.lbl_commit.set_selectable(True)
        self.lbl_commit.add_css_class("detail-value")
        box.append(self._detail_row("提交：", self.lbl_commit))

        self.lbl_parent = Gtk.Label()
        self.lbl_parent.set_halign(Gtk.Align.START)
        self.lbl_parent.set_selectable(True)
        self.lbl_parent.add_css_class("detail-value")
        box.append(self._detail_row("父级：", self.lbl_parent))

        self.lbl_author = Gtk.Label()
        self.lbl_author.set_halign(Gtk.Align.START)
        self.lbl_author.set_selectable(True)
        self.lbl_author.add_css_class("detail-value")
        box.append(self._detail_row("作者：", self.lbl_author))

        self.lbl_date = Gtk.Label()
        self.lbl_date.set_halign(Gtk.Align.START)
        self.lbl_date.set_selectable(True)
        self.lbl_date.add_css_class("detail-value")
        box.append(self._detail_row("日期：", self.lbl_date))

        self.lbl_committer = Gtk.Label()
        self.lbl_committer.set_halign(Gtk.Align.START)
        self.lbl_committer.set_selectable(True)
        self.lbl_committer.add_css_class("detail-value")
        box.append(self._detail_row("提交者：", self.lbl_committer))

        self.lbl_message = Gtk.Label()
        self.lbl_message.set_halign(Gtk.Align.START)
        self.lbl_message.set_selectable(True)
        self.lbl_message.set_margin_top(12)
        self.lbl_message.add_css_class("detail-value")
        box.append(self.lbl_message)

        scroll.set_child(box)
        return scroll

    def _detail_row(self, label_text, value_widget):
        row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        lbl = Gtk.Label(label=label_text)
        lbl.set_halign(Gtk.Align.START)
        lbl.add_css_class("detail-label")
        row.append(lbl)
        row.append(value_widget)
        return row

    def _build_code_panel(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # Code header
        hdr_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        hdr_box.add_css_class("code-header")
        hdr_box.set_margin_top(0)
        hdr_box.set_margin_bottom(0)

        self.code_header_lbl = Gtk.Label(label="📄 选择提交查看差异")
        self.code_header_lbl.set_halign(Gtk.Align.START)
        self.code_header_lbl.set_hexpand(True)
        hdr_box.append(self.code_header_lbl)

        for btn_label in ["⚙", "...", "回退区块"]:
            b = Gtk.Button(label=btn_label)
            b.add_css_class("filter-btn")
            hdr_box.append(b)

        box.append(hdr_box)

        # Code content
        scroll = Gtk.ScrolledWindow()
        self.code_text = Gtk.TextView()
        self.code_text.set_editable(False)
        self.code_text.set_monospace(True)
        self.code_text.set_wrap_mode(Gtk.WrapMode.NONE)
        self.code_buffer = self.code_text.get_buffer()

        self._tag_add = self.code_buffer.create_tag("add", background="#e6ffec")
        self._tag_remove = self.code_buffer.create_tag("remove", background="#ffe6e6")
        self._tag_add_fg = self.code_buffer.create_tag("add_fg", foreground="#28a745")
        self._tag_remove_fg = self.code_buffer.create_tag("remove_fg", foreground="#dc3545")

        scroll.set_child(self.code_text)
        box.append(scroll)

        return box

    # ── Public API ──────────────────────────────────────────
    def show_commit_detail(self, commit):
        short_id = commit["id"][:7]
        full_id = commit["id"]
        self.lbl_commit.set_label(f"{full_id} [{short_id}]")

        parents = commit.get("parents", [])
        if parents:
            self.lbl_parent.set_label(", ".join(p[:7] for p in parents))
        else:
            self.lbl_parent.set_label("(初始提交)")

        self.lbl_author.set_label(f'{commit["author"]} <{commit["email"]}>')

        dt = datetime.datetime.fromtimestamp(commit["time"])
        self.lbl_date.set_label(dt.strftime("%Y年%m月%d日 %H:%M:%S"))

        self.lbl_committer.set_label(commit["author"])
        self.lbl_message.set_label(commit["message"].strip())

        self._show_diff(commit)

    def _show_diff(self, commit):
        self.code_buffer.set_text("")
        self.code_header_lbl.set_label(f"📄 提交 {commit['id'][:7]} 的文件变更")

        try:
            commit_obj = self.parent.repo.repo.get(commit["id"])
            if not commit_obj.parents:
                self.code_buffer.set_text("(初始提交，无前一提交可比较)")
                return

            parent = commit_obj.parents[0]
            diff = self.parent.repo.repo.diff(parent, commit_obj)

            lines = []
            patch_count = 0
            for patch in diff:
                patch_count += 1
                fname = patch.new_file_path or patch.old_file_path or "unknown"
                lines.append(f"块 {patch_count} : {fname}\n")

                for hunk in patch.hunks:
                    header = f"@@ -{hunk.old_start},{hunk.old_lines} +{hunk.new_start},{hunk.new_lines} @@\n"
                    lines.append(("hunk", header))
                    for line in hunk.lines:
                        if line.origin == '+':
                            lines.append(("add", f"+{line.content}"))
                        elif line.origin == '-':
                            lines.append(("remove", f"-{line.content}"))
                        else:
                            lines.append(("context", f" {line.content}"))
                lines.append(("", "\n"))

            if patch_count == 0:
                self.code_buffer.set_text("(无文件变更)")
                return

            it = self.code_buffer.get_start_iter()
            for item in lines:
                if isinstance(item, tuple):
                    tag_type, text = item
                    if tag_type == "add":
                        self.code_buffer.insert_with_tags(it, text, self._tag_add)
                    elif tag_type == "remove":
                        self.code_buffer.insert_with_tags(it, text, self._tag_remove)
                    else:
                        self.code_buffer.insert(it, text)
                else:
                    self.code_buffer.insert(it, item)

        except Exception as e:
            self.code_buffer.set_text(f"无法显示差异: {str(e)}")

    def clear(self):
        for lbl in [self.lbl_commit, self.lbl_parent, self.lbl_author,
                     self.lbl_date, self.lbl_committer, self.lbl_message]:
            lbl.set_label("")
        self.code_buffer.set_text("")
        self.code_header_lbl.set_label("📄 选择提交查看差异")
