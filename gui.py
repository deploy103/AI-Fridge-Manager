import threading
import tkinter as tk
from datetime import date, datetime, timedelta
from tkinter import messagebox, ttk

from openai import OpenAI

from fridge_manager.fridge_service import (
    AIResponseError,
    FridgeAI,
    FridgeManager,
    normalize_food_name,
    validate_food_name,
)
from fridge_manager.gui_theme import COLORS, apply_theme
from fridge_manager.settings import APP_ROOT, ConfigError, load_settings


class FridgeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI 냉장고 매니저")
        self.root.geometry("1220x800")
        self.root.minsize(1040, 720)
        self.fonts = apply_theme(self.root)

        try:
            self.settings = load_settings()
        except ConfigError as error:
            messagebox.showerror("설정 오류", str(error))
            self.root.destroy()
            return

        self.ai = FridgeAI(
            client=OpenAI(api_key=self.settings.api_key),
            model=self.settings.model,
        )
        self.manager = FridgeManager()
        self.inventory_path = APP_ROOT / "fridge_inventory.json"
        self._load_saved_inventory()
        self.is_busy = False

        self.food_var = tk.StringVar()
        self.expiry_var = tk.StringVar()
        self.search_var = tk.StringVar()
        self.inventory_summary_var = tk.StringVar(
            value="냉장고에 식품이 없습니다. 한글 이름으로 바로 추가할 수 있습니다."
        )
        self.freshness_summary_var = tk.StringVar(value="신선도 관리할 식품이 없습니다.")
        self.selected_item_var = tk.StringVar(value="선택한 식품이 없습니다.")
        self.decision_title_var = tk.StringVar(value="아직 판정한 식품이 없습니다.")
        self.decision_reason_var = tk.StringVar(
            value="식품을 추가하면 냉장 여부와 사유가 여기에 표시됩니다."
        )
        self.recommend_title_var = tk.StringVar(value="추천 메뉴가 아직 없습니다.")
        self.recommend_reason_var = tk.StringVar(
            value="냉장고에 재료를 추가한 뒤 버튼을 누르면 메뉴와 추천 이유를 보여줍니다."
        )
        self.status_var = tk.StringVar(
            value=f"준비 완료 | 모델: {self.settings.model} | UTF-8 한글 입력 지원"
        )

        self.add_button = None
        self.recommend_button = None
        self.remove_button = None
        self.clear_button = None
        self.food_entry = None
        self.expiry_entry = None
        self.search_entry = None
        self.inventory_tree = None
        self.decision_badge = None

        self._build_layout()
        self._refresh_inventory_view()
        self.food_entry.focus_set()

    def _load_saved_inventory(self):
        try:
            self.manager.load_from_file(self.inventory_path)
        except (OSError, ValueError) as error:
            messagebox.showwarning(
                "저장 파일 오류",
                f"저장된 냉장고 목록을 불러오지 못했습니다.\n{error}",
            )

    def _save_inventory(self):
        try:
            self.manager.save_to_file(self.inventory_path)
        except OSError as error:
            self.status_var.set(f"목록 저장에 실패했습니다: {error}")

    def _build_layout(self):
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        shell = ttk.Frame(self.root, padding=24, style="Shell.TFrame")
        shell.grid(row=0, column=0, sticky="nsew")
        shell.grid_columnconfigure(0, weight=7)
        shell.grid_columnconfigure(1, weight=10)
        shell.grid_rowconfigure(1, weight=1)

        hero = tk.Frame(shell, bg=COLORS["hero"], padx=28, pady=24)
        hero.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 18))
        hero.grid_columnconfigure(0, weight=1)

        tk.Label(
            hero,
            text="AI 냉장고 매니저",
            bg=COLORS["hero"],
            fg=COLORS["hero_text"],
            font=self.fonts["title"],
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            hero,
            text="보관 판단, 유통기한 관리, 검색, 목록 정리, 메뉴 추천까지 한 화면에서 처리합니다.",
            bg=COLORS["hero"],
            fg=COLORS["hero_text"],
            font=self.fonts["hero_subtitle"],
        ).grid(row=1, column=0, sticky="w", pady=(8, 0))

        pill_frame = tk.Frame(hero, bg=COLORS["hero"])
        pill_frame.grid(row=0, column=1, rowspan=2, sticky="e")
        self._create_hero_pill(pill_frame, f"모델 {self.settings.model}").pack(
            side="left", padx=(0, 8)
        )
        self._create_hero_pill(pill_frame, "한글 식품명 지원").pack(side="left")

        left_panel = ttk.Frame(shell, style="Shell.TFrame")
        left_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 12))
        left_panel.grid_rowconfigure(1, weight=1)
        left_panel.grid_columnconfigure(0, weight=1)

        right_panel = ttk.Frame(shell, style="Shell.TFrame")
        right_panel.grid(row=1, column=1, sticky="nsew")
        right_panel.grid_rowconfigure(0, weight=1)
        right_panel.grid_columnconfigure(0, weight=1)

        add_card = ttk.Frame(left_panel, padding=22, style="Card.TFrame")
        add_card.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        add_card.grid_columnconfigure(0, weight=1)

        ttk.Label(add_card, text="식품 추가", style="CardTitle.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            add_card,
            text="예: 김치, 우유, 두부, Greek yogurt. 한글과 영문을 모두 사용할 수 있습니다.",
            style="Muted.TLabel",
            wraplength=320,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(6, 14))

        self.food_entry = ttk.Entry(
            add_card,
            textvariable=self.food_var,
            style="App.TEntry",
            font=self.fonts["body"],
        )
        self.food_entry.grid(row=2, column=0, sticky="ew")
        self.food_entry.bind("<Return>", self._on_enter_pressed)

        expiry_row = ttk.Frame(add_card, style="Card.TFrame")
        expiry_row.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        expiry_row.grid_columnconfigure(0, weight=1)
        expiry_row.grid_columnconfigure(1, weight=0)
        expiry_row.grid_columnconfigure(2, weight=0)
        expiry_row.grid_columnconfigure(3, weight=0)

        self.expiry_entry = ttk.Entry(
            expiry_row,
            textvariable=self.expiry_var,
            style="App.TEntry",
            font=self.fonts["body"],
        )
        self.expiry_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(
            expiry_row,
            text="+3일",
            style="Compact.TButton",
            command=lambda: self._set_expiry_after_days(3),
        ).grid(row=0, column=1, padx=(0, 6))
        ttk.Button(
            expiry_row,
            text="+7일",
            style="Compact.TButton",
            command=lambda: self._set_expiry_after_days(7),
        ).grid(row=0, column=2, padx=(0, 6))
        ttk.Button(
            expiry_row,
            text="+14일",
            style="Compact.TButton",
            command=lambda: self._set_expiry_after_days(14),
        ).grid(row=0, column=3)
        ttk.Label(
            add_card,
            text="유통기한은 선택 사항입니다. YYYY-MM-DD 형식으로 입력하세요.",
            style="Muted.TLabel",
        ).grid(row=4, column=0, sticky="w", pady=(6, 0))

        button_row = ttk.Frame(add_card, style="Card.TFrame")
        button_row.grid(row=5, column=0, sticky="ew", pady=(12, 0))
        button_row.grid_columnconfigure(0, weight=1)
        button_row.grid_columnconfigure(1, weight=1)

        self.add_button = ttk.Button(
            button_row,
            text="냉장 여부 확인 후 추가",
            style="Primary.TButton",
            command=self.on_add_food,
        )
        self.add_button.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.recommend_button = ttk.Button(
            button_row,
            text="메뉴 추천 받기",
            style="Secondary.TButton",
            command=self.on_recommend_food,
        )
        self.recommend_button.grid(row=0, column=1, sticky="ew", padx=(6, 0))

        decision_card = ttk.Frame(left_panel, padding=22, style="Card.TFrame")
        decision_card.grid(row=1, column=0, sticky="nsew")
        decision_card.grid_columnconfigure(0, weight=1)
        decision_card.grid_rowconfigure(3, weight=1)

        ttk.Label(decision_card, text="최근 판정 결과", style="CardTitle.TLabel").grid(
            row=0, column=0, sticky="w"
        )

        self.decision_badge = tk.Label(
            decision_card,
            text="대기 중",
            bg=COLORS["info_bg"],
            fg=COLORS["info_fg"],
            font=self.fonts["badge"],
            padx=12,
            pady=6,
        )
        self.decision_badge.grid(row=1, column=0, sticky="w", pady=(14, 12))

        ttk.Label(
            decision_card,
            textvariable=self.decision_title_var,
            style="Result.TLabel",
            wraplength=320,
            justify="left",
        ).grid(row=2, column=0, sticky="w")

        ttk.Label(
            decision_card,
            textvariable=self.decision_reason_var,
            style="CardBody.TLabel",
            wraplength=320,
            justify="left",
        ).grid(row=3, column=0, sticky="nw", pady=(12, 0))

        inventory_card = ttk.Frame(right_panel, padding=22, style="Card.TFrame")
        inventory_card.grid(row=0, column=0, sticky="nsew", pady=(0, 12))
        inventory_card.grid_columnconfigure(0, weight=1)
        inventory_card.grid_rowconfigure(4, weight=1)

        ttk.Label(inventory_card, text="현재 냉장고 목록", style="CardTitle.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            inventory_card,
            textvariable=self.inventory_summary_var,
            style="Muted.TLabel",
            wraplength=560,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(6, 12))

        ttk.Label(
            inventory_card,
            textvariable=self.freshness_summary_var,
            style="Insight.TLabel",
            wraplength=560,
            justify="left",
        ).grid(row=2, column=0, sticky="w", pady=(0, 12))

        search_row = ttk.Frame(inventory_card, style="Card.TFrame")
        search_row.grid(row=3, column=0, sticky="ew", pady=(0, 12))
        search_row.grid_columnconfigure(0, weight=1)
        self.search_entry = ttk.Entry(
            search_row,
            textvariable=self.search_var,
            style="App.TEntry",
            font=self.fonts["body"],
        )
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.search_var.trace_add("write", lambda *_args: self._refresh_inventory_view())
        ttk.Button(
            search_row,
            text="검색 초기화",
            style="Secondary.TButton",
            command=self._clear_search,
        ).grid(row=0, column=1)

        tree_frame = ttk.Frame(inventory_card, style="Card.TFrame")
        tree_frame.grid(row=4, column=0, sticky="nsew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        self.inventory_tree = ttk.Treeview(
            tree_frame,
            columns=("food", "expiry", "freshness", "reason"),
            show="headings",
            style="App.Treeview",
            selectmode="browse",
        )
        self.inventory_tree.heading("food", text="식품")
        self.inventory_tree.heading("expiry", text="유통기한")
        self.inventory_tree.heading("freshness", text="상태")
        self.inventory_tree.heading("reason", text="냉장 보관 사유")
        self.inventory_tree.column("food", width=130, anchor="w")
        self.inventory_tree.column("expiry", width=100, anchor="center")
        self.inventory_tree.column("freshness", width=105, anchor="center")
        self.inventory_tree.column("reason", width=360, anchor="w")
        self.inventory_tree.grid(row=0, column=0, sticky="nsew")
        self.inventory_tree.bind("<<TreeviewSelect>>", self._on_inventory_selected)

        inventory_scrollbar = ttk.Scrollbar(
            tree_frame,
            orient="vertical",
            command=self.inventory_tree.yview,
        )
        inventory_scrollbar.grid(row=0, column=1, sticky="ns")
        self.inventory_tree.configure(yscrollcommand=inventory_scrollbar.set)

        action_row = ttk.Frame(inventory_card, style="Card.TFrame")
        action_row.grid(row=5, column=0, sticky="ew", pady=(12, 0))
        action_row.grid_columnconfigure(0, weight=1)
        ttk.Label(
            action_row,
            textvariable=self.selected_item_var,
            style="Muted.TLabel",
        ).grid(row=0, column=0, sticky="w")
        self.remove_button = ttk.Button(
            action_row,
            text="선택 삭제",
            style="Secondary.TButton",
            command=self.on_remove_selected,
        )
        self.remove_button.grid(row=0, column=1, padx=(8, 6))
        self.clear_button = ttk.Button(
            action_row,
            text="전체 비우기",
            style="Danger.TButton",
            command=self.on_clear_inventory,
        )
        self.clear_button.grid(row=0, column=2)

        recommendation_card = ttk.Frame(right_panel, padding=22, style="Card.TFrame")
        recommendation_card.grid(row=1, column=0, sticky="ew")
        recommendation_card.grid_columnconfigure(0, weight=1)

        ttk.Label(
            recommendation_card,
            text="추천 메뉴",
            style="CardTitle.TLabel",
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            recommendation_card,
            textvariable=self.recommend_title_var,
            style="Result.TLabel",
            wraplength=560,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(14, 10))
        ttk.Label(
            recommendation_card,
            textvariable=self.recommend_reason_var,
            style="CardBody.TLabel",
            wraplength=560,
            justify="left",
        ).grid(row=2, column=0, sticky="w")

        status_bar = ttk.Frame(shell, padding=(18, 12), style="Status.TFrame")
        status_bar.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(18, 0))
        ttk.Label(
            status_bar,
            textvariable=self.status_var,
            style="StatusBar.TLabel",
        ).grid(row=0, column=0, sticky="w")

    def _create_hero_pill(self, parent, text):
        return tk.Label(
            parent,
            text=text,
            bg=COLORS["accent_soft"],
            fg=COLORS["text"],
            font=self.fonts["small"],
            padx=10,
            pady=5,
        )

    def _on_enter_pressed(self, _event):
        self.on_add_food()

    def _set_expiry_after_days(self, days):
        self.expiry_var.set((date.today() + timedelta(days=days)).isoformat())

    def _parse_expiry_date(self):
        raw_expiry = self.expiry_var.get().strip()
        if not raw_expiry:
            return None, None

        try:
            parsed = datetime.strptime(raw_expiry, "%Y-%m-%d").date()
        except ValueError:
            return None, "유통기한은 YYYY-MM-DD 형식으로 입력해 주세요."

        if parsed < date.today() - timedelta(days=365):
            return None, "유통기한이 너무 과거입니다. 날짜를 다시 확인해 주세요."

        return parsed.isoformat(), None

    def _get_freshness_label(self, expires_on):
        if not expires_on:
            return "미설정"

        try:
            expiry_date = date.fromisoformat(expires_on)
        except ValueError:
            return "확인 필요"

        days_left = (expiry_date - date.today()).days
        if days_left < 0:
            return "기한 지남"
        if days_left == 0:
            return "오늘까지"
        if days_left <= 2:
            return f"{days_left}일 남음"
        return "여유 있음"

    def _filtered_items(self):
        keyword = normalize_food_name(self.search_var.get()).casefold()
        if not keyword:
            return self.manager.items

        return tuple(
            item
            for item in self.manager.items
            if keyword in normalize_food_name(item.name).casefold()
            or keyword in item.reason.casefold()
            or (item.expires_on and keyword in item.expires_on)
        )

    def _clear_search(self):
        self.search_var.set("")

    def _refresh_inventory_view(self):
        for item_id in self.inventory_tree.get_children():
            self.inventory_tree.delete(item_id)

        visible_items = self._filtered_items()
        for item in visible_items:
            self.inventory_tree.insert(
                "",
                "end",
                values=(
                    item.name,
                    item.expires_on or "-",
                    self._get_freshness_label(item.expires_on),
                    item.reason,
                ),
            )

        count = len(self.manager.items)
        if count == 0:
            self.inventory_summary_var.set(
                "냉장고에 식품이 없습니다. 한글 이름으로 바로 추가할 수 있습니다."
            )
        elif count == 1:
            self.inventory_summary_var.set("냉장고에 식품 1개가 있습니다.")
        else:
            self.inventory_summary_var.set(f"냉장고에 식품 {count}개가 있습니다.")

        if self.search_var.get().strip():
            self.inventory_summary_var.set(
                f"검색 결과 {len(visible_items)}개 / 전체 {count}개 식품"
            )

        self._refresh_freshness_summary()
        self._on_inventory_selected()

    def _refresh_freshness_summary(self):
        expired = 0
        urgent = 0
        unset = 0

        for item in self.manager.items:
            if not item.expires_on:
                unset += 1
                continue

            try:
                days_left = (date.fromisoformat(item.expires_on) - date.today()).days
            except ValueError:
                urgent += 1
                continue

            if days_left < 0:
                expired += 1
            elif days_left <= 2:
                urgent += 1

        if not self.manager.items:
            self.freshness_summary_var.set("신선도 관리할 식품이 없습니다.")
        else:
            self.freshness_summary_var.set(
                f"기한 지남 {expired}개 | 2일 이내 {urgent}개 | 기한 미설정 {unset}개"
            )

    def _on_inventory_selected(self, _event=None):
        if self.inventory_tree is None:
            return

        selection = self.inventory_tree.selection()
        if not selection:
            self.selected_item_var.set("선택한 식품이 없습니다.")
            return

        values = self.inventory_tree.item(selection[0], "values")
        if values:
            self.selected_item_var.set(f"선택됨: {values[0]}")

    def _set_busy(self, busy, message):
        self.is_busy = busy
        state = "disabled" if busy else "normal"
        self.add_button.configure(state=state)
        self.recommend_button.configure(state=state)
        self.remove_button.configure(state=state)
        self.clear_button.configure(state=state)
        self.food_entry.configure(state=state)
        self.expiry_entry.configure(state=state)
        self.search_entry.configure(state=state)
        self.status_var.set(message)

        if not busy:
            self.food_entry.focus_set()

    def _set_decision_view(self, label, title, reason, tone):
        tone_map = {
            "success": (COLORS["success_bg"], COLORS["success_fg"]),
            "warning": (COLORS["warning_bg"], COLORS["warning_fg"]),
            "info": (COLORS["info_bg"], COLORS["info_fg"]),
            "error": (COLORS["error_bg"], COLORS["error_fg"]),
        }
        background, foreground = tone_map[tone]
        self.decision_badge.config(text=label, bg=background, fg=foreground)
        self.decision_title_var.set(title)
        self.decision_reason_var.set(reason)

    def on_add_food(self):
        if self.is_busy:
            return

        raw_food_name = self.food_var.get()
        validation_error = validate_food_name(raw_food_name)
        if validation_error:
            self._set_decision_view(
                label="입력 확인",
                title="식품 이름을 다시 확인해 주세요.",
                reason=validation_error,
                tone="warning",
            )
            self.status_var.set("입력값을 확인해 주세요.")
            return

        expires_on, expiry_error = self._parse_expiry_date()
        if expiry_error:
            self._set_decision_view(
                label="입력 확인",
                title="유통기한을 다시 확인해 주세요.",
                reason=expiry_error,
                tone="warning",
            )
            self.status_var.set("유통기한 입력값을 확인해 주세요.")
            return

        food_name = raw_food_name.strip()
        self._set_busy(True, f"'{food_name}' 보관 여부를 AI가 확인하고 있습니다...")

        threading.Thread(
            target=self._run_add_food_task,
            args=(food_name, expires_on),
            daemon=True,
        ).start()

    def _run_add_food_task(self, food_name, expires_on):
        try:
            decision = self.ai.check_storage(food_name)
            result = self.manager.add_decision(decision)
            if result.status in {"added", "duplicate"} and expires_on:
                self.manager.update_expiry(result.item_name, expires_on)
            self.root.after(0, lambda: self._finish_add_food(result))
        except AIResponseError as error:
            self.root.after(0, lambda: self._finish_with_error(str(error)))
        except Exception:
            self.root.after(
                0,
                lambda: self._finish_with_error(
                    "AI 요청에 실패했습니다. API 키, 모델, 네트워크 상태를 확인해 주세요."
                ),
            )

    def _finish_add_food(self, result):
        self.food_var.set("")
        self.expiry_var.set("")

        if result.status == "added":
            self._set_decision_view(
                label="추가 완료",
                title=f"'{result.item_name}'을(를) 냉장고에 넣었습니다.",
                reason=result.reason,
                tone="success",
            )
            self.status_var.set(f"'{result.item_name}' 추가 완료")
        elif result.status == "rejected":
            self._set_decision_view(
                label="추가 안 함",
                title=f"'{result.item_name}'은(는) 냉장고에 넣지 않았습니다.",
                reason=result.reason,
                tone="warning",
            )
            self.status_var.set(f"'{result.item_name}'은(는) 실온 보관 권장")
        else:
            self._set_decision_view(
                label="중복 항목",
                title=f"'{result.item_name}'은(는) 이미 목록에 있습니다.",
                reason=result.reason,
                tone="info",
            )
            self.status_var.set(f"'{result.item_name}'은(는) 이미 등록되어 있습니다.")

        self._refresh_inventory_view()
        self._save_inventory()
        self._set_busy(False, self.status_var.get())

    def on_remove_selected(self):
        if self.is_busy:
            return

        selection = self.inventory_tree.selection()
        if not selection:
            self.status_var.set("삭제할 식품을 목록에서 선택해 주세요.")
            return

        values = self.inventory_tree.item(selection[0], "values")
        if not values:
            return

        food_name = values[0]
        if self.manager.remove_item(food_name):
            self._refresh_inventory_view()
            self._save_inventory()
            self.status_var.set(f"'{food_name}'을(를) 목록에서 삭제했습니다.")

    def on_clear_inventory(self):
        if self.is_busy:
            return

        if not self.manager.items:
            self.status_var.set("비울 식품이 없습니다.")
            return

        confirmed = messagebox.askyesno(
            "냉장고 비우기",
            "현재 냉장고 목록을 모두 삭제할까요?",
        )
        if not confirmed:
            return

        self.manager.clear()
        self.search_var.set("")
        self._refresh_inventory_view()
        self._save_inventory()
        self.status_var.set("냉장고 목록을 모두 비웠습니다.")

    def on_recommend_food(self):
        if self.is_busy:
            return

        if not self.manager.items:
            self.recommend_title_var.set("추천할 재료가 아직 없습니다.")
            self.recommend_reason_var.set(
                "먼저 식품을 추가하면 그 재료를 기준으로 메뉴와 추천 이유를 보여줍니다."
            )
            self.status_var.set("냉장고가 비어 있어 추천을 건너뛰었습니다.")
            return

        self._set_busy(True, "AI가 현재 재료를 바탕으로 메뉴를 추천하고 있습니다...")
        threading.Thread(target=self._run_recommend_task, daemon=True).start()

    def _run_recommend_task(self):
        try:
            recommendation = self.ai.recommend_menu(self.manager.items)
            self.root.after(0, lambda: self._finish_recommendation(recommendation))
        except AIResponseError as error:
            self.root.after(0, lambda: self._finish_with_error(str(error), recommend=True))
        except Exception:
            self.root.after(
                0,
                lambda: self._finish_with_error(
                    "AI 요청에 실패했습니다. API 키, 모델, 네트워크 상태를 확인해 주세요.",
                    recommend=True,
                ),
            )

    def _finish_recommendation(self, recommendation):
        self.recommend_title_var.set(recommendation.menu)
        self.recommend_reason_var.set(recommendation.reason)
        self.status_var.set("메뉴 추천을 완료했습니다.")
        self._set_busy(False, self.status_var.get())

    def _finish_with_error(self, message, recommend=False):
        if recommend:
            self.recommend_title_var.set("추천을 가져오지 못했습니다.")
            self.recommend_reason_var.set(message)
        else:
            self._set_decision_view(
                label="오류",
                title="식품 판정에 실패했습니다.",
                reason=message,
                tone="error",
            )

        self._set_busy(False, message)


def main():
    root = tk.Tk()
    app = FridgeApp(root)
    if root.winfo_exists() and hasattr(app, "settings"):
        root.mainloop()


if __name__ == "__main__":
    main()
