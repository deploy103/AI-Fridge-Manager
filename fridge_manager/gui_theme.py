import tkinter.font as tkfont
from tkinter import ttk


COLORS = {
    "bg": "#eef3f1",
    "card": "#ffffff",
    "card_alt": "#f5f8f7",
    "border": "#d7e0dc",
    "text": "#1f2a27",
    "muted": "#63706b",
    "accent": "#2e7d69",
    "accent_hover": "#246754",
    "accent_soft": "#dcefe9",
    "hero": "#173f45",
    "hero_text": "#f7fffb",
    "success_bg": "#dff3e4",
    "success_fg": "#1d633c",
    "warning_bg": "#fff0cf",
    "warning_fg": "#8f5a12",
    "info_bg": "#e3ecff",
    "info_fg": "#29528e",
    "error_bg": "#f8d9dc",
    "error_fg": "#953840",
    "danger": "#bd4b4b",
    "danger_hover": "#9e3d3d",
    "button_text": "#ffffff",
}

FONT_CANDIDATES = (
    "留묒? 怨좊뵓",
    "Malgun Gothic",
    "Noto Sans KR",
    "Apple SD Gothic Neo",
    "AppleGothic",
    "NanumGothic",
    "?뗭?",
    "援대┝",
    "Arial Unicode MS",
)


def _select_font_family(root):
    available_fonts = set(tkfont.families(root))

    for font_name in FONT_CANDIDATES:
        if font_name in available_fonts:
            return font_name

    return tkfont.nametofont("TkDefaultFont").cget("family")


def _build_fonts(root):
    family = _select_font_family(root)
    fonts = {
        "title": (family, 26, "bold"),
        "hero_subtitle": (family, 11),
        "section": (family, 14, "bold"),
        "body": (family, 10),
        "body_bold": (family, 10, "bold"),
        "result": (family, 16, "bold"),
        "button": (family, 10, "bold"),
        "badge": (family, 9, "bold"),
        "small": (family, 9),
        "tiny_bold": (family, 8, "bold"),
    }

    for font_name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
        named_font = tkfont.nametofont(font_name)
        named_font.configure(family=family)

    root.option_add("*Font", fonts["body"])
    return fonts


def apply_theme(root):
    root.configure(bg=COLORS["bg"])
    fonts = _build_fonts(root)

    style = ttk.Style(root)
    if "clam" in style.theme_names():
        style.theme_use("clam")

    style.configure("Shell.TFrame", background=COLORS["bg"])
    style.configure("Card.TFrame", background=COLORS["card"], relief="flat")
    style.configure("Status.TFrame", background=COLORS["card_alt"], relief="flat")

    style.configure(
        "CardTitle.TLabel",
        background=COLORS["card"],
        foreground=COLORS["text"],
        font=fonts["section"],
    )
    style.configure(
        "CardBody.TLabel",
        background=COLORS["card"],
        foreground=COLORS["text"],
        font=fonts["body"],
    )
    style.configure(
        "Muted.TLabel",
        background=COLORS["card"],
        foreground=COLORS["muted"],
        font=fonts["small"],
    )
    style.configure(
        "Insight.TLabel",
        background=COLORS["accent_soft"],
        foreground=COLORS["text"],
        font=fonts["small"],
        padding=(10, 7),
    )
    style.configure(
        "Result.TLabel",
        background=COLORS["card"],
        foreground=COLORS["text"],
        font=fonts["result"],
    )
    style.configure(
        "StatusBar.TLabel",
        background=COLORS["card_alt"],
        foreground=COLORS["text"],
        font=fonts["body"],
    )

    style.configure(
        "Primary.TButton",
        background=COLORS["accent"],
        foreground=COLORS["button_text"],
        font=fonts["button"],
        borderwidth=0,
        focusthickness=0,
        padding=(14, 10),
    )
    style.map(
        "Primary.TButton",
        background=[("active", COLORS["accent_hover"]), ("disabled", COLORS["border"])],
        foreground=[("disabled", COLORS["muted"])],
    )

    style.configure(
        "Secondary.TButton",
        background=COLORS["card_alt"],
        foreground=COLORS["text"],
        font=fonts["button"],
        borderwidth=0,
        focusthickness=0,
        padding=(14, 10),
    )
    style.map(
        "Secondary.TButton",
        background=[("active", COLORS["accent_soft"]), ("disabled", COLORS["border"])],
        foreground=[("disabled", COLORS["muted"])],
    )

    style.configure(
        "Compact.TButton",
        background=COLORS["card_alt"],
        foreground=COLORS["text"],
        font=fonts["tiny_bold"],
        borderwidth=0,
        focusthickness=0,
        padding=(10, 9),
    )
    style.map(
        "Compact.TButton",
        background=[("active", COLORS["accent_soft"]), ("disabled", COLORS["border"])],
        foreground=[("disabled", COLORS["muted"])],
    )

    style.configure(
        "Danger.TButton",
        background=COLORS["danger"],
        foreground=COLORS["button_text"],
        font=fonts["button"],
        borderwidth=0,
        focusthickness=0,
        padding=(14, 10),
    )
    style.map(
        "Danger.TButton",
        background=[("active", COLORS["danger_hover"]), ("disabled", COLORS["border"])],
        foreground=[("disabled", COLORS["muted"])],
    )

    style.configure(
        "App.TEntry",
        fieldbackground=COLORS["card_alt"],
        foreground=COLORS["text"],
        bordercolor=COLORS["border"],
        insertcolor=COLORS["text"],
        padding=10,
        relief="flat",
    )
    style.map(
        "App.TEntry",
        bordercolor=[("focus", COLORS["accent"])],
        lightcolor=[("focus", COLORS["accent"])],
        darkcolor=[("focus", COLORS["accent"])],
    )

    style.configure(
        "App.Treeview",
        background=COLORS["card_alt"],
        fieldbackground=COLORS["card_alt"],
        foreground=COLORS["text"],
        bordercolor=COLORS["border"],
        font=fonts["body"],
        rowheight=34,
    )
    style.configure(
        "App.Treeview.Heading",
        background=COLORS["card"],
        foreground=COLORS["text"],
        font=fonts["body_bold"],
        relief="flat",
    )
    style.map(
        "App.Treeview",
        background=[("selected", COLORS["accent_soft"])],
        foreground=[("selected", COLORS["text"])],
    )

    return fonts
