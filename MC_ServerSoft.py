import os
import sys
import time
import threading
import subprocess
import requests
import webbrowser
import socket
import json
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from datetime import datetime

try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None

try:
    import pyperclip
except Exception:
    pyperclip = None

try:
    import miniupnpc
except Exception:
    miniupnpc = None

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

__version__ = "2.0.0"
ROOT_GEOMETRY = "700x360"
DEFAULT_ICON_NAME = "icon.ico"
DISCORD_ICON_NAME = "Discord.png"
DISCORD_URL = "https://disboard.org/ja/server/1383423417348395078"

PAPER_API_ROOT = "https://api.papermc.io/v2"
MOJANG_MANIFEST = "https://launchermeta.mojang.com/mc/game/version_manifest.json"
PURPUR_API_ROOT = "https://api.purpurmc.org/v2"
FABRIC_API_ROOT = "https://meta.fabricmc.net/v2/versions/server"
FORGE_INDEX_URL = "https://files.minecraftforge.net/net/minecraftforge/forge/"

CONFIG_FILENAME = "mc_server_config.json"

PROPERTY_DEFINITIONS = [
    ("motd", "サーバー名 (MOTD)", "A Minecraft Server", False),
    ("server-port", "サーバーポート", "25565", False),
    ("server-ip", "サーバーIP（空欄で自動）", "", False),
    ("max-players", "最大プレイヤー数", "20", False),
    ("online-mode", "オンラインモード（true=認証あり）", "true", True),
    ("level-name", "ワールド名", "world", False),
    ("level-seed", "ワールドシード", "", False),
    ("gamemode", "ゲームモード", "survival", False),
    ("difficulty", "難易度 (0=peaceful,1=easy,2=normal,3=hard)", "1", False),
    ("pvp", "PvP を有効にする", "true", True),
    ("view-distance", "ビュー距離 (チャンク)", "10", False),
    ("spawn-monsters", "モンスター生成", "true", True),
    ("spawn-npcs", "NPC 生成", "true", True),
    ("spawn-animals", "動物生成", "true", True),
    ("spawn-protection", "スポーン保護範囲", "16", False),
    ("enforce-whitelist", "ホワイトリストを強制", "false", True),
    ("enable-command-block", "コマンドブロックを許可", "false", True),
    ("allow-flight", "飛行を許可", "false", True),
    ("generate-structures", "構造物を生成", "true", True),
    ("level-type", "ワールドタイプ", "default", False),
    ("snooper-enabled", "Snooper 送信を有効", "true", True),
    ("resource-pack", "リソースパック URL", "", False),
    ("enable-rcon", "RCON を有効にする", "false", True),
    ("rcon.password", "RCON パスワード", "", False),
    ("rcon.port", "RCON ポート", "25575", False),
    ("max-tick-time", "最大ティック時間 (ms)", "60000", False),
    ("function-permission-level", "関数の権限レベル", "2", False),
    ("op-permission-level", "OP 権限レベル", "4", False),
    ("query.enabled", "Query を有効にする", "false", True),
    ("query.port", "Query ポート", "25565", False),
    ("debug", "デバッグモード", "false", True),
    ("allow-nether", "ネザーを許可", "true", True),
    ("announce-player-achievements", "実績通知 (古い)", "true", True),
]


def resource_path(relative_path: str) -> str:
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parent
    return str((base / relative_path).resolve())

def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def download_file_stream(url: str, dest_path: Path, callback=None) -> None:
    with requests.get(url, stream=True, timeout=30) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0) or 0)
        downloaded = 0
        with open(dest_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if callback:
                        callback(downloaded, total)

def get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"

def get_global_ip() -> str | None:
    try:
        r = requests.get("https://api.ipify.org", timeout=5)
        r.raise_for_status()
        return r.text.strip()
    except Exception:
        return None

def copy_to_clipboard(text: str) -> tuple[bool, str | None]:
    if pyperclip:
        try:
            pyperclip.copy(text)
            return True, None
        except Exception as e:
            return False, str(e)
    else:
        try:
            tmp = tk.Tk()
            tmp.withdraw()
            tmp.clipboard_clear()
            tmp.clipboard_append(text)
            tmp.update()
            tmp.destroy()
            return True, None
        except Exception as e:
            return False, str(e)

def timestamp() -> str:
    return datetime.now().strftime("[%Y-%m-%d %H:%M:%S] ")


def fetch_paper_versions():
    r = requests.get(PAPER_API_ROOT + "/projects/paper", timeout=10)
    r.raise_for_status()
    versions = r.json().get("versions", [])
    versions = sorted(versions, reverse=True)
    return versions

def fetch_purpur_versions():

    r = requests.get(PURPUR_API_ROOT + "/purpur", timeout=10)
    r.raise_for_status()

    j = r.json()
    if isinstance(j, dict) and "versions" in j:
        versions = sorted(j.get("versions", []), reverse=True)
    elif isinstance(j, list):
        versions = sorted(j, reverse=True)
    else:
        versions = []
    return versions

def fetch_fabric_versions():
    r = requests.get(FABRIC_API_ROOT, timeout=10)
    r.raise_for_status()

    j = r.json()
    if isinstance(j, list):
        vals = []
        for e in j:
            if isinstance(e, dict) and "version" in e:
                vals.append(e["version"])
            elif isinstance(e, str):
                vals.append(e)
        return sorted(vals, reverse=True)
    return []

def fetch_forge_versions():


    if BeautifulSoup is None:
        raise RuntimeError("BeautifulSoup が必要です。`pip install beautifulsoup4` を実行してください。")
    r = requests.get(FORGE_INDEX_URL, timeout=10)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    versions = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        parts = href.split("/net/minecraftforge/forge/")
        if len(parts) > 1:
            tail = parts[1]
            ver = tail.split("/")[0]
            if ver:
                versions.add(ver)
    versions = sorted(versions, reverse=True)
    return versions


def download_plugin_from_spigot_page(url: str, plugins_dir: Path, status_callback=None) -> Path:
    if status_callback:
        status_callback("プラグインページ解析中...")
    headers = {"User-Agent": "Mozilla/5.0"}

    if url.lower().endswith(".jar"):
        dest_name = Path(url.split("?")[0]).name
        dest = plugins_dir / dest_name
        download_file_stream(url, dest)
        return dest

    if BeautifulSoup is None:
        raise RuntimeError("BeautifulSoup (bs4) が必要です。pip install beautifulsoup4 を実行してください。")

    resp = requests.get(url, headers=headers, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    a = soup.find("a", class_="downloadButton")
    if not a:
        a = soup.find("a", href=lambda href: href and "download" in href.lower())
    if not a or not a.get("href"):
        raise RuntimeError("ダウンロードリンクをページ内から検出できませんでした。")

    dl_url = a.get("href")
    if dl_url.startswith("/"):
        dl_url = "https://www.spigotmc.org" + dl_url

    if status_callback:
        status_callback("中間ページ取得中...")
    inter_resp = requests.get(dl_url, headers=headers, timeout=20, allow_redirects=True)
    inter_resp.raise_for_status()

    if inter_resp.url.lower().endswith(".jar"):
        final_url = inter_resp.url
    else:
        soup2 = BeautifulSoup(inter_resp.text, "html.parser")
        jar_a = soup2.find("a", href=lambda href: href and href.lower().endswith(".jar"))
        if not jar_a:
            raise RuntimeError("最終的な.jarリンクを検出できませんでした。")
        final_url = jar_a.get("href")
        if final_url.startswith("/"):
            final_url = "https://www.spigotmc.org" + final_url

    if status_callback:
        status_callback("ダウンロード中...")
    r2 = requests.get(final_url, headers=headers, allow_redirects=True, stream=True, timeout=30)
    r2.raise_for_status()

    filename = None
    cd = r2.headers.get("Content-Disposition")
    if cd and "filename=" in cd:
        try:
            filename = cd.split("filename=")[1].strip().strip('"').split(";")[0]
        except Exception:
            pass
    if not filename:
        filename = Path(final_url.split("?")[0]).name
    if not filename.lower().endswith(".jar"):
        filename = f"plugin_{int(time.time())}.jar"

    ensure_dir(plugins_dir)
    dest = plugins_dir / filename
    with open(dest, "wb") as fw:
        for chunk in r2.iter_content(chunk_size=8192):
            if chunk:
                fw.write(chunk)

    return dest


def config_path() -> Path:
    base = Path(__file__).resolve().parent
    return base / CONFIG_FILENAME

DEFAULT_CONFIG = {
    "java_path": "",
    "args": "",
    "install_dir": str(Path.cwd()),
    "ram": "2048",
    "server_type": "paper",
    "version": "",
}

def load_config() -> dict:
    p = config_path()
    if p.exists():
        try:
            with open(p, "r", encoding="utf-8") as f:
                j = json.load(f)
            
            for k, v in DEFAULT_CONFIG.items():
                if k not in j:
                    j[k] = v
            return j
        except Exception:
            return DEFAULT_CONFIG.copy()
    else:
        return DEFAULT_CONFIG.copy()

def save_config(cfg: dict):
    try:
        with open(config_path(), "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


class MCServerGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("Minecraft サーバーセットアップ＆管理")
        root.geometry(ROOT_GEOMETRY)
        root.resizable(False, False)

        try:
            ico = resource_path(DEFAULT_ICON_NAME)
            if Path(ico).exists():
                root.iconbitmap(ico)
        except Exception:
            pass

        self.config = load_config()

        self.server_type = tk.StringVar(value=self.config.get("server_type", "paper"))
        self.version = tk.StringVar(value=self.config.get("version", ""))
        self.install_dir = tk.StringVar(value=self.config.get("install_dir", str(Path.cwd())))
        self.ram = tk.StringVar(value=self.config.get("ram", "2048"))
        self.status_text = tk.StringVar(value="Ready")
        self.plugin_url_var = tk.StringVar()
        self.update_check_url_var = tk.StringVar(value="")
        self.java_path_var = tk.StringVar(value=self.config.get("java_path", ""))
        self.args_var = tk.StringVar(value=self.config.get("args", ""))
        self.reset_args_var = tk.BooleanVar(value=False)

        self.server_proc: subprocess.Popen | None = None
        self.read_thread: threading.Thread | None = None
        self.proc_lock = threading.Lock()
        self.console_window: tk.Toplevel | None = None
        self.console_text: scrolledtext.ScrolledText | None = None
        self.console_input: ttk.Entry | None = None

        self.build_ui()
        self.show_splash_then_main()

    def show_splash_then_main(self):
        splash = tk.Toplevel(self.root)
        splash.overrideredirect(True)
        w = 520; h = 220
        ws = self.root.winfo_screenwidth(); hs = self.root.winfo_screenheight()
        x = (ws - w) // 2; y = (hs - h) // 2
        splash.geometry(f"{w}x{h}+{x}+{y}")
        frm = ttk.Frame(splash, padding=12)
        frm.pack(fill="both", expand=True)
        try:
            img_path = resource_path("back.png")
            if Path(img_path).exists() and PIL_AVAILABLE:
                img = Image.open(img_path)
                img = img.resize((w, h), Image.LANCZOS)
                self.splash_img = ImageTk.PhotoImage(img)
                lbl = tk.Label(frm, image=self.splash_img)
                lbl.pack(fill="both", expand=True)
            else:
                ttk.Label(frm, text="Minecraft Server Manager", font=("Segoe UI", 18)).pack(pady=20)
                ttk.Label(frm, text=f"バージョン {__version__}").pack()
        except Exception:
            ttk.Label(frm, text="Minecraft Server Manager", font=("Segoe UI", 18)).pack(pady=20)
            ttk.Label(frm, text=f"バージョン {__version__}").pack()

        self.root.withdraw()
        def close_splash():
            time.sleep(1.0)
            try:
                splash.destroy()
            except Exception:
                pass
            try:
                self.root.deiconify()
            except Exception:
                pass
        threading.Thread(target=close_splash, daemon=True).start()

    def build_ui(self):
        frm = ttk.Frame(self.root, padding=8)
        frm.pack(fill="both", expand=True)

       
        ttk.Label(frm, text="サーバータイプ").grid(row=0, column=0, sticky="w", padx=4, pady=2)
        types = [("PaperMC", "paper"), ("Purpur", "purpur"), ("Vanilla", "vanilla"), ("Forge", "forge"), ("Fabric", "fabric")]
        col = 1
        for txt, val in types:
            ttk.Radiobutton(frm, text=txt, variable=self.server_type, value=val).grid(row=0, column=col, sticky="w")
            col += 1

        
        ttk.Label(frm, text="バージョン").grid(row=1, column=0, sticky="w", padx=4, pady=2)
        self.version_cb = ttk.Combobox(frm, textvariable=self.version, width=30)
        self.version_cb.grid(row=1, column=1, columnspan=3, sticky="w")
        ttk.Button(frm, text="バージョン一覧取得", width=16, command=self.fetch_versions).grid(row=1, column=4, sticky="w", padx=4)

        
        ttk.Label(frm, text="インストール先").grid(row=2, column=0, sticky="w", padx=4, pady=2)
        ttk.Entry(frm, textvariable=self.install_dir, width=46).grid(row=2, column=1, columnspan=3, sticky="w")
        ttk.Button(frm, text="参照", width=8, command=self.browse_dir).grid(row=2, column=4, sticky="w", padx=4)

        
        ttk.Label(frm, text="割当メモリ (MB)").grid(row=3, column=0, sticky="w", padx=4, pady=2)
        ttk.Entry(frm, textvariable=self.ram, width=12).grid(row=3, column=1, sticky="w")

        
        ttk.Label(frm, text="Java パス").grid(row=4, column=0, sticky="w", padx=4, pady=2)
        ttk.Entry(frm, textvariable=self.java_path_var, width=46).grid(row=4, column=1, columnspan=3, sticky="w")
        ttk.Button(frm, text="参照", width=8, command=self.browse_java).grid(row=4, column=4, sticky="w", padx=4)


        self.use_gui_mode = tk.BooleanVar(value=False)
        ttk.Checkbutton(frm, text="GUIあり起動（noguiを外す）", variable=self.use_gui_mode).grid(row=6, column=0, columnspan=2, sticky="w", padx=6, pady=2)

        ttk.Label(frm, text="引数").grid(row=5, column=0, sticky="w", padx=4, pady=2)
        ttk.Entry(frm, textvariable=self.args_var, width=46).grid(row=5, column=1, columnspan=3, sticky="w")
        ttk.Checkbutton(frm, text="リセット（デフォルト引数に戻す）", variable=self.reset_args_var, command=self.on_reset_args).grid(row=5, column=4, sticky="w", padx=4)

        self.use_gui_mode = tk.BooleanVar(value=False)
        ttk.Checkbutton(frm, text="GUIあり起動（noguiを外す）", variable=self.use_gui_mode).grid(row=6, column=0, columnspan=2, sticky="w", padx=6, pady=2)

        btn_frame = ttk.Frame(frm)
        btn_frame.grid(row=7, column=0, columnspan=5, pady=8)
        ttk.Button(btn_frame, text="ダウンロード＆セットアップ", width=20, command=self.start_setup).grid(row=0, column=0, padx=4)
        ttk.Button(btn_frame, text="サーバー開始", width=12, command=self.start_server).grid(row=0, column=1, padx=4)
        ttk.Button(btn_frame, text="サーバー停止", width=12, command=self.stop_server).grid(row=0, column=2, padx=4)
        ttk.Button(btn_frame, text="強制終了", width=12, command=self.force_kill_server).grid(row=0, column=3, padx=4)
        ttk.Button(btn_frame, text="サーバー設定", width=12, command=self.open_settings_window).grid(row=0, column=4, padx=4)

        ttk.Label(frm, textvariable=self.status_text, foreground="blue").grid(row=8, column=0, columnspan=5, sticky="w", pady=(4,2))


        bottom = ttk.Frame(self.root, padding=6)
        bottom.pack(side="bottom", fill="x")
        ttk.Button(bottom, text="ポート開放", width=12, command=self.port_open).pack(side="left", padx=6)
        ttk.Button(bottom, text="ポート閉鎖", width=12, command=self.port_close).pack(side="left", padx=6)
        ttk.Button(bottom, text="ローカルIPコピー", width=14, command=self.copy_local_ip).pack(side="left", padx=6)
        ttk.Button(bottom, text="グローバルIPコピー", width=14, command=self.copy_global_ip).pack(side="left", padx=6)

        ttk.Label(bottom, text="プラグインURL:").pack(side="left", padx=(10,4))
        self.plugin_entry = ttk.Entry(bottom, textvariable=self.plugin_url_var, width=36)
        self.plugin_entry.pack(side="left", padx=4)
        ttk.Button(bottom, text="プラグインDL", command=self.on_plugin_download).pack(side="left", padx=6)

        try:
            dpath = resource_path(DISCORD_ICON_NAME)
            if Path(dpath).exists() and PIL_AVAILABLE:
                img = Image.open(dpath).resize((20,20), Image.LANCZOS)
                self.discord_photo = ImageTk.PhotoImage(img)
                tk.Button(bottom, image=self.discord_photo, command=lambda: webbrowser.open(DISCORD_URL), borderwidth=0).pack(side="right", padx=8)
            else:
                ttk.Button(bottom, text="Discord", command=lambda: webbrowser.open(DISCORD_URL)).pack(side="right", padx=8)
        except Exception:
            ttk.Button(bottom, text="Discord", command=lambda: webbrowser.open(DISCORD_URL)).pack(side="right", padx=8)

        ttk.Label(bottom, text="Update URL:").pack(side="right", padx=(8,2))
        ttk.Entry(bottom, textvariable=self.update_check_url_var, width=18).pack(side="right", padx=(0,6))

    def set_status(self, text: str):
        try:
            self.status_text.set(text)
            self.root.update_idletasks()
        except Exception:
            pass

    def browse_dir(self):
        d = filedialog.askdirectory(initialdir=self.install_dir.get())
        if d:
            self.install_dir.set(d)
            self.config["install_dir"] = d
            save_config(self.config)

    def browse_java(self):
        p = filedialog.askopenfilename(title="java.exe を選択", filetypes=[("Java Executable", "java.exe")], initialdir="C:\\Program Files\\Java")
        if p:
            self.java_path_var.set(p)
            self.config["java_path"] = p
            save_config(self.config)

    def on_reset_args(self):
        if self.reset_args_var.get():

            ram_mb = self.ram.get() if self.ram.get().isdigit() else "2048"
            default = f"-Xmx{ram_mb}M -Xms{ram_mb}M nogui"
            self.args_var.set(default)
            self.config["args"] = default
            save_config(self.config)


    def fetch_versions(self):
        self.set_status("バージョン一覧取得中...")
        def job():
            try:
                stype = self.server_type.get()
                versions = []
                if stype == "paper":
                    versions = fetch_paper_versions()
                elif stype == "purpur":
                    try:
                        versions = fetch_purpur_versions()
                    except Exception as e:
                        raise RuntimeError(f"Purpur バージョン取得に失敗しました: {e}")
                elif stype == "fabric":
                    try:
                        versions = fetch_fabric_versions()
                    except Exception as e:
                        raise RuntimeError(f"Fabric バージョン取得に失敗しました: {e}")
                elif stype == "forge":
                    try:
                        versions = fetch_forge_versions()
                    except Exception as e:
                        raise RuntimeError(f"Forge バージョン取得に失敗しました: {e}")
                else:

                    r = requests.get(MOJANG_MANIFEST, timeout=10)
                    r.raise_for_status()
                    versions = [v["id"] for v in r.json().get("versions", [])]
                if not versions:
                    raise RuntimeError("バージョン一覧が空です。")

                self.version_cb["values"] = versions
                if versions:
                    self.version.set(versions[0])
                self.set_status("バージョン取得完了")

                self.config["server_type"] = self.server_type.get()
                self.config["version"] = self.version.get()
                save_config(self.config)
            except Exception as e:
                self.set_status("取得失敗")
                messagebox.showerror("エラー", f"バージョンの取得に失敗しました:\n{e}")
        threading.Thread(target=job, daemon=True).start()

 
    def start_setup(self):
        version = self.version.get().strip()
        if not version:
            messagebox.showwarning("未選択", "バージョンを選択してください。")
            return
        threading.Thread(target=self._setup_job, daemon=True).start()

    def _setup_job(self):
        try:
            self.set_status("セットアップ開始...")
            server_dir = Path(self.install_dir.get())
            ensure_dir(server_dir)

            stype = self.server_type.get()
            version = self.version.get().strip()
            jar_url = None
            jar_name = None

            if stype == "paper":
                r = requests.get(f"{PAPER_API_ROOT}/projects/paper/versions/{version}", timeout=10)
                r.raise_for_status()
                builds = r.json().get("builds", [])
                if not builds:
                    raise Exception("PaperMC のビルドが見つかりません")
                build = max(builds)
                jar_url = f"{PAPER_API_ROOT}/projects/paper/versions/{version}/builds/{build}/downloads/paper-{version}-{build}.jar"
                jar_name = f"paper-{version}-{build}.jar"
            elif stype == "purpur":

                try:
                    r = requests.get(f"{PURPUR_API_ROOT}/purpur/versions/{version}", timeout=10)
                    r.raise_for_status()

                    j = r.json()
                    if isinstance(j, dict) and "builds" in j and j["builds"]:
                        build = max(j["builds"])
                        jar_url = f"{PURPUR_API_ROOT}/purpur/versions/{version}/builds/{build}/downloads/purpur-{version}-{build}.jar"
                        jar_name = f"purpur-{version}-{build}.jar"
                    else:

                        jar_url = f"{PURPUR_API_ROOT}/purpur/{version}/latest/download"
                        jar_name = f"purpur-{version}.jar"
                except Exception:

                    jar_url = f"{PURPUR_API_ROOT}/purpur/{version}/latest/download"
                    jar_name = f"purpur-{version}.jar"
            elif stype == "fabric":

                try:
                    r = requests.get(FABRIC_API_ROOT, timeout=10)
                    r.raise_for_status()
                    candidates = r.json()

                    found = None
                    for e in candidates:
                        if (isinstance(e, dict) and e.get("version") == version) or (isinstance(e, str) and e == version):
                            found = e
                            break

                    jar_url = None
                    jar_name = f"fabric-server-{version}.jar"

                except Exception:
                    jar_url = None
            elif stype == "forge":

                try:
                    if BeautifulSoup is None:
                        raise RuntimeError("Forge の自動取得には BeautifulSoup が必要です。pip install beautifulsoup4 を実行してください。")
                   
                    idx = requests.get(FORGE_INDEX_URL, timeout=10)
                    idx.raise_for_status()
                    soup = BeautifulSoup(idx.text, "html.parser")
                 
                    found_link = None
                    for a in soup.find_all("a", href=True):
                        if f"/{version}/" in a["href"]:
                            found_link = a["href"]
                            break
                    if found_link:
                      
                        if found_link.startswith("/"):
                            base = "https://files.minecraftforge.net"
                            found_link = base + found_link
                      
                        pg = requests.get(found_link, timeout=10)
                        pg.raise_for_status()
                        soup2 = BeautifulSoup(pg.text, "html.parser")
                        jar_link = None
                        for a in soup2.find_all("a", href=True):
                            href = a["href"]
                            if href.lower().endswith(".jar") and "server" in href.lower():
                                jar_link = href
                                break
                        if jar_link:
                            if jar_link.startswith("/"):
                                jar_link = "https://files.minecraftforge.net" + jar_link
                            jar_url = jar_link
                            jar_name = Path(jar_url.split("?")[0]).name
                        else:
                            jar_url = None
                    else:
                        jar_url = None
                except Exception:
                    jar_url = None
            else:
             
                r = requests.get(MOJANG_MANIFEST, timeout=10)
                r.raise_for_status()
                manifest = r.json()
                vinfo = next((v for v in manifest["versions"] if v["id"] == version), None)
                if not vinfo:
                    raise Exception("指定バージョンが見つかりません")
                r2 = requests.get(vinfo["url"], timeout=10)
                r2.raise_for_status()
                server_info = r2.json().get("downloads", {}).get("server", {})
                jar_url = server_info.get("url")
                jar_name = f"vanilla-{version}.jar"

          
            if jar_url:
                jar_path = server_dir / jar_name
                self.set_status("ダウンロード中...")
                download_file_stream(jar_url, jar_path)
            else:
                jar_path = None

          
            (server_dir / "eula.txt").write_text("eula=true\n", encoding="utf-8")

     
            args = self.args_var.get().strip()
            if not args:
          
                ram_mb = self.ram.get() if self.ram.get().isdigit() else "2048"
                args = f"-Xmx{ram_mb}M -Xms{ram_mb}M nogui"
            java_exec = self.java_path_var.get().strip() or "java"
          
            if java_exec and Path(java_exec).is_dir():
                guessed = Path(java_exec) / "bin" / "java.exe"
                if guessed.exists():
                    java_exec = str(guessed)
          
            start_bat = server_dir / "start.bat"
            if jar_path:
                jar_name_local = jar_path.name
                start_bat.write_text(f'@echo off\n"{java_exec}" {args} -jar "{jar_name_local}" nogui\npause\n', encoding="utf-8")
            else:
            
                start_bat.write_text(f'@echo off\nREM サーバーJARが存在するフォルダで、以下のコマンドを実行してください\nREM 例: "{java_exec}" {args} -jar server.jar nogui\npause\n', encoding="utf-8")

            prop_path = server_dir / "server.properties"
            if not prop_path.exists():
                default_props = {
                    "motd": "A Minecraft Server",
                    "server-port": "25565",
                    "max-players": "20",
                    "online-mode": "true",
                    "level-name": "world",
                    "gamemode": "survival",
                    "difficulty": "1",
                    "pvp": "true",
                }
                with open(prop_path, "w", encoding="utf-8") as f:
                    for k, v in default_props.items():
                        f.write(f"{k}={v}\n")

            
            self.config["install_dir"] = str(server_dir)
            self.config["ram"] = self.ram.get()
            self.config["args"] = args
            self.config["java_path"] = self.java_path_var.get().strip()
            self.config["server_type"] = self.server_type.get()
            self.config["version"] = self.version.get().strip()
            save_config(self.config)

            self.set_status("セットアップ完了")
            messagebox.showinfo("完了", "セットアップが完了しました。")
        except Exception as e:
            self.set_status("セットアップ失敗")
            messagebox.showerror("エラー", f"セットアップに失敗しました:\n{e}")

    
    def start_server(self):
        with self.proc_lock:
            if self.server_proc:
                messagebox.showwarning("既に起動中", "サーバーはすでに起動しています。")
                return
        server_dir = Path(self.install_dir.get())
        jars = list(server_dir.glob("*.jar"))
        if not jars:
            messagebox.showerror("エラー", "サーバーJARが見つかりません。先にセットアップするか、サーバーJARを設置してください。")
            return
        jar = jars[0]
        try:
            
            java_exec = self.java_path_var.get().strip() or "java"
            if java_exec and Path(java_exec).is_dir():
                guessed = Path(java_exec) / "bin" / "java.exe"
                if guessed.exists():
                    java_exec = str(guessed)
           
            args_text = self.args_var.get().strip()
            if not args_text:
                ram_mb = self.ram.get() if self.ram.get().isdigit() else "2048"
                args_text = f"-Xmx{ram_mb}M -Xms{ram_mb}M nogui"
           
            args_parts = [a for a in args_text.split() if a.lower() != "nogui"]
            cmd = [java_exec] + args_parts + ["-jar", jar.name, "nogui"]

        except Exception as e:
            messagebox.showerror("起動エラー", f"コマンド構築に失敗しました:\n{e}")
            return

        try:
            proc = subprocess.Popen(cmd, cwd=str(server_dir),
                                    stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, text=True, bufsize=1)
        except Exception as e:
            messagebox.showerror("起動エラー", f"プロセスの起動に失敗しました:\n{e}")
            return

        with self.proc_lock:
            self.server_proc = proc

        self.open_console_window()
        self.read_thread = threading.Thread(target=self._read_server_output_loop, daemon=True)
        self.read_thread.start()
        self.set_status("サーバー起動中...")

       
        self.config["java_path"] = self.java_path_var.get().strip()
        self.config["args"] = self.args_var.get().strip()
        self.config["ram"] = self.ram.get()
        self.config["install_dir"] = self.install_dir.get()
        self.config["server_type"] = self.server_type.get()
        self.config["version"] = self.version.get()
        save_config(self.config)

    def _read_server_output_loop(self):
        proc = None
        with self.proc_lock:
            proc = self.server_proc

        if not proc:
            return

        try:
            for line in proc.stdout:
                if line is None:
                    break
               
                self._append_console(timestamp() + line)
        except Exception:
            pass
        finally:
            try:
                with self.proc_lock:
                    if proc is not None and proc.poll() is not None:
                        try:
                            if proc.stdin:
                                proc.stdin.close()
                        except Exception:
                            pass
                        try:
                            if proc.stdout:
                                proc.stdout.close()
                        except Exception:
                            pass
                        self.server_proc = None
                        self.set_status("サーバー停止（プロセス終了）")
            except Exception:
                pass

    def stop_server(self):
        with self.proc_lock:
            proc = self.server_proc
        if not proc:
            messagebox.showwarning("未起動", "サーバーは起動していません。")
            return

        try:
            try:
                if proc.stdin and proc.poll() is None:
                    proc.stdin.write("stop\n")
                    proc.stdin.flush()
                    self.set_status("停止コマンド送信、終了待ち...")
                else:
                    self.set_status("停止コマンド送信失敗（stdin closed）")
            except Exception:
                pass

            def waiter(wait_timeout=30):
                try:
                    proc.wait(timeout=wait_timeout)
                    try:
                        if proc.stdin:
                            proc.stdin.close()
                    except Exception:
                        pass
                    try:
                        if proc.stdout:
                            proc.stdout.close()
                    except Exception:
                        pass
                    with self.proc_lock:
                        if self.server_proc is proc:
                            self.server_proc = None
                    self.set_status("サーバー停止しました")
                except subprocess.TimeoutExpired:
                    self.set_status("停止コマンドで終了しませんでした")
                    def ask_kill():
                        if messagebox.askyesno("強制終了", "停止コマンドで終了しませんでした。\n強制終了しますか？"):
                            self.force_kill_server()
                    try:
                        self.root.after(0, ask_kill)
                    except Exception:
                        pass
                except Exception as e:
                    self.set_status("停止中にエラー")
                    try:
                        self.root.after(0, lambda: messagebox.showerror("停止エラー", f"{e}"))
                    except Exception:
                        pass

            threading.Thread(target=waiter, daemon=True).start()

        except Exception as e:
            messagebox.showerror("停止失敗", f"{e}")

    def force_kill_server(self):
        with self.proc_lock:
            proc = self.server_proc

        if proc:
            try:
                try:
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        try:
                            proc.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            pass
                except Exception:
                    try:
                        proc.kill()
                        try:
                            proc.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            pass
                    except Exception:
                        pass
            finally:
                try:
                    if proc.stdin:
                        proc.stdin.close()
                except Exception:
                    pass
                try:
                    if proc.stdout:
                        proc.stdout.close()
                except Exception:
                    pass

        try:
            if os.name == "nt":
                os.system('taskkill /F /IM java.exe > NUL 2>&1')
        except Exception:
            pass

        with self.proc_lock:
            self.server_proc = None

        self.set_status("Javaプロセスを強制終了しました")

 
    def open_console_window(self):
        if self.console_window and tk.Toplevel.winfo_exists(self.console_window):
            self.console_window.lift()
            return
        self.console_window = tk.Toplevel(self.root)
        self.console_window.title("サーバーコンソール")
        self.console_window.geometry("760x460")
        try:
            ico = resource_path(DEFAULT_ICON_NAME)
            if Path(ico).exists():
                self.console_window.iconbitmap(ico)
        except Exception:
            pass

        self.console_text = scrolledtext.ScrolledText(self.console_window, width=120, height=28, state="disabled")
        self.console_text.pack(padx=6, pady=6, fill="both", expand=True)
        bottom = ttk.Frame(self.console_window)
        bottom.pack(fill="x", padx=6, pady=6)
        self.console_input = ttk.Entry(bottom)
        self.console_input.pack(side="left", fill="x", expand=True, padx=(0,6))
        ttk.Button(bottom, text="送信", width=10, command=self.send_command).pack(side="left")
       
        self.console_input.bind("<Return>", lambda e: self.send_command())

    def _append_console(self, text: str):
        if not self.console_text:
            return
        def _do():
            try:
                self.console_text.configure(state="normal")
                self.console_text.insert("end", text)
                if not text.endswith("\n"):
                    self.console_text.insert("end", "\n")
                self.console_text.see("end")
                self.console_text.configure(state="disabled")
            except Exception:
                pass
        try:
            self.console_text.after(0, _do)
        except Exception:
            pass

    def send_command(self):
        cmd = self.console_input.get().strip()
        if not cmd:
            return
        with self.proc_lock:
            proc = self.server_proc
        if not proc or proc.poll() is not None:
            messagebox.showwarning("未起動", "サーバーは起動していません。")
            return
        try:
            if proc.stdin:
                proc.stdin.write(cmd + "\n")
                proc.stdin.flush()
                self.console_input.delete(0, "end")
                self._append_console(timestamp() + "> " + cmd)
            else:
                messagebox.showerror("送信失敗", "プロセスの stdin にアクセスできません。")
        except Exception as e:
            messagebox.showerror("送信失敗", f"{e}")

    
    def _get_server_port(self) -> int:
        server_dir = Path(self.install_dir.get())
        prop_path = server_dir / "server.properties"
        if prop_path.exists():
            try:
                with open(prop_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if "=" in line and line.strip().startswith("server-port"):
                            return int(line.split("=",1)[1].strip())
            except Exception:
                pass
        return 25565

    def port_open(self):
        if miniupnpc is None:
            messagebox.showerror("miniupnpc が無い", "ポート開放には miniupnpc が必要です。\n`pip install miniupnpc` を実行してください。")
            return
        port = self._get_server_port()
        threading.Thread(target=self._port_open_job, args=(port,), daemon=True).start()

    def _port_open_job(self, port: int):
        self.set_status(f"ポート {port} を開放しています...")
        try:
            u = miniupnpc.UPnP()
            u.discoverdelay = 200
            u.discover()
            u.selectigd()
            local_ip = get_local_ip()
            u.addportmapping(port, "TCP", local_ip, port, "Minecraft server", "")
            self.set_status(f"ポート {port} を開放しました（TCP）。")
            messagebox.showinfo("完了", f"ポート {port} を開放しました（TCP）。")
        except Exception as e:
            messagebox.showerror("UPnP エラー", f"UPnP によるポート開放に失敗しました:\n{e}")
            self.set_status("ポート開放失敗")

    def port_close(self):
        if miniupnpc is None:
            messagebox.showerror("miniupnpc が無い", "ポート閉鎖には miniupnpc が必要です。\n`pip install miniupnpc` を実行してください。")
            return
        port = self._get_server_port()
        threading.Thread(target=self._port_close_job, args=(port,), daemon=True).start()

    def _port_close_job(self, port: int):
        self.set_status(f"ポート {port} を閉鎖しています...")
        try:
            u = miniupnpc.UPnP()
            u.discoverdelay = 200
            u.discover()
            u.selectigd()
            u.deleteportmapping(port, "TCP")
            self.set_status(f"ポート {port} を閉鎖しました（TCP）。")
            messagebox.showinfo("完了", f"ポート {port} を閉鎖しました（TCP）。")
        except Exception as e:
            messagebox.showerror("UPnP エラー", f"UPnP によるポート閉鎖に失敗しました:\n{e}")
            self.set_status("ポート閉鎖失敗")


    def copy_local_ip(self):
        ip = get_local_ip()
        ok, err = copy_to_clipboard(ip)
        if ok:
            messagebox.showinfo("コピー完了", f"ローカルIPをコピーしました: {ip}")
        else:
            messagebox.showerror("コピー失敗", f"クリップボードへのコピーに失敗しました:\n{err}")

    def copy_global_ip(self):
        self.set_status("グローバルIP取得中...")
        def job():
            ip = get_global_ip()
            if ip:
                ok, err = copy_to_clipboard(ip)
                if ok:
                    messagebox.showinfo("コピー完了", f"グローバルIPをコピーしました: {ip}")
                    self.set_status("グローバルIP取得・コピー完了")
                else:
                    messagebox.showerror("コピー失敗", f"クリップボードへのコピーに失敗しました:\n{err}")
                    self.set_status("コピー失敗")
            else:
                messagebox.showerror("取得失敗", "グローバルIPの取得に失敗しました。")
                self.set_status("グローバルIP取得失敗")
        threading.Thread(target=job, daemon=True).start()

   
    def on_plugin_download(self):
        url = self.plugin_url_var.get().strip()
        if not url:
            messagebox.showwarning("未入力", "プラグインの URL を入力してください。")
            return
        server_dir = Path(self.install_dir.get())
        if not server_dir.exists():
            messagebox.showwarning("フォルダ未選択", "先にインストール先フォルダを正しく設定してください。")
            return
        plugins_dir = server_dir / "plugins"
        ensure_dir(plugins_dir)
        threading.Thread(target=self._plugin_download_job, args=(url, plugins_dir), daemon=True).start()

    def _plugin_download_job(self, url: str, plugins_dir: Path):
        try:
            self.set_status("プラグインダウンロード中...")
            dest = download_plugin_from_spigot_page(url, plugins_dir, status_callback=self.set_status)
            self.set_status("プラグインダウンロード完了")
            messagebox.showinfo("完了", f"プラグインを保存しました:\n{str(dest)}")
        except Exception as e:
            self.set_status("ダウンロード失敗")
            messagebox.showerror("ダウンロード失敗", f"プラグインのダウンロードに失敗しました:\n{e}")

    
    def open_settings_window(self):
        server_dir = Path(self.install_dir.get())
        prop_path = server_dir / "server.properties"
        props = {}
        if prop_path.exists():
            try:
                with open(prop_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if not line.strip() or line.strip().startswith("#") or "=" not in line:
                            continue
                        k, v = line.strip().split("=", 1)
                        props[k] = v
            except Exception:
                props = {}

        win = tk.Toplevel(self.root)
        win.title("サーバー設定")
        win.geometry("480x420")
        try:
            ico = resource_path(DEFAULT_ICON_NAME)
            if Path(ico).exists():
                win.iconbitmap(ico)
        except Exception:
            pass

        canvas = tk.Canvas(win)
        scrollbar = ttk.Scrollbar(win, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0,0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        var_map: dict[str, tuple[tk.Variable, bool]] = {}
        row = 0
        for key, jlabel, default, is_bool in PROPERTY_DEFINITIONS:
            current_val = props.get(key, default)
            ttk.Label(scrollable_frame, text=jlabel).grid(row=row, column=0, sticky="w", padx=6, pady=4)
            if is_bool:
                var = tk.BooleanVar(value=(str(current_val).lower() == "true"))
                ttk.Checkbutton(scrollable_frame, variable=var).grid(row=row, column=1, sticky="w", padx=6)
            else:
                var = tk.StringVar(value=str(current_val))
                ttk.Entry(scrollable_frame, textvariable=var, width=36).grid(row=row, column=1, sticky="w", padx=6)
            var_map[key] = (var, is_bool)
            row += 1

        def save_settings():
            if not server_dir.exists():
                messagebox.showerror("エラー", "インストール先フォルダが見つかりません。")
                return
            out: dict[str, str] = {}
            for key, _, _, _ in PROPERTY_DEFINITIONS:
                if key in var_map:
                    var, is_bool = var_map[key]
                    if is_bool:
                        out[key] = "true" if var.get() else "false"
                    else:
                        out[key] = var.get()

            try:
                if prop_path.exists():
                    with open(prop_path, "r", encoding="utf-8") as f:
                        for line in f:
                            if "=" in line and not line.strip().startswith("#"):
                                k = line.split("=",1)[0]
                                if k not in out:
                                    v = line.split("=",1)[1].rstrip("\n")
                                    out[k] = v
                with open(prop_path, "w", encoding="utf-8") as f:
                    for k, v in out.items():
                        f.write(f"{k}={v}\n")
                messagebox.showinfo("保存完了", "server.properties を保存しました。")
                win.destroy()
            except Exception as e:
                messagebox.showerror("保存失敗", f"{e}")

        ttk.Button(scrollable_frame, text="保存", command=save_settings).grid(row=row, column=0, columnspan=2, pady=10)
        


def main():
    root = tk.Tk()
    app = MCServerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
