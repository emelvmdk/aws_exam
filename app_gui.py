#!/usr/bin/env python3
"""
AWS 문제풀이 - 데스크톱 앱 (Tkinter GUI)

PDF를 변환해서 "최근 시험 목록"에 등록해두고, 다음부터는 목록에서 골라
바로 "시작하기"만 누르면 되도록 만든 실행기. PyInstaller로 --onefile
--windowed 빌드하면 파이썬 설치 없이 더블클릭으로 쓸 수 있는 .exe가 된다.

폴더 구조(개발 모드/빌드된 exe 모두 exe가 있는 위치를 기준으로 동작):
    app_gui.py (또는 AWS문제풀이.exe)
    parser/parse_pdf.py
    web/
    data/
      library/        각 시험을 변환한 JSON + 라이브러리 메타데이터 (git 미포함)
      questions.json   "시작하기"를 누른 시험이 복사되는 위치 (웹앱이 읽는 파일)
"""
import functools
import http.server
import io
import json
import re
import sys
import threading
import tkinter as tk
import webbrowser
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

# PyInstaller --windowed(콘솔 없음) 빌드에서는 sys.stdout/sys.stderr가 None이
# 된다. http.server는 요청마다 sys.stderr.write(...)로 로그를 남기려 하는데,
# None에 write()를 호출하면 예외가 발생해 응답이 끊겨 브라우저에
# ERR_EMPTY_RESPONSE가 뜬다. 콘솔이 없을 때는 안전한 더미 스트림으로 막는다.
if sys.stdout is None:
    sys.stdout = io.StringIO()
if sys.stderr is None:
    sys.stderr = io.StringIO()

PORT = 8765


def base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


BASE_DIR = base_dir()
DATA_DIR = BASE_DIR / "data"
LIBRARY_DIR = DATA_DIR / "library"
LIBRARY_FILE = LIBRARY_DIR / "library.json"
ACTIVE_JSON = DATA_DIR / "questions.json"
SAMPLE_JSON = DATA_DIR / "questions.sample.json"

sys.path.insert(0, str(BASE_DIR / "parser"))


def load_library() -> dict:
    if not LIBRARY_FILE.exists():
        return {"exams": [], "last_selected": None}
    try:
        return json.loads(LIBRARY_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"exams": [], "last_selected": None}


def save_library(lib: dict) -> None:
    LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
    # 임시 파일에 쓴 뒤 원자적으로 교체한다. 쓰는 도중 앱이 죽거나 강제
    # 종료돼도 library.json은 항상 이전 상태 또는 완전한 새 상태 중 하나이며,
    # 깨진(truncated) JSON으로 남아 다음 실행 때 목록이 통째로 사라지는
    # 일이 없다.
    tmp_path = LIBRARY_FILE.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(lib, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(LIBRARY_FILE)


def upsert_exam(entry: dict, select: bool = True) -> dict:
    """디스크의 최신 library.json을 다시 읽어서 entry를 병합 저장한다.

    앱을 시작할 때 메모리에 읽어둔 목록을 그대로 덮어쓰면, 창을 완전히 닫지
    않은 채 다른 인스턴스가 남아있다가 나중에 저장할 때 방금 추가/변경한
    내용이 사라질 수 있다. 저장 직전에 항상 디스크 최신 상태를 다시 읽어
    병합하면 이런 유실을 막을 수 있다.
    """
    lib = load_library()
    exams = [e for e in lib.get("exams", []) if e["name"] != entry["name"]]
    exams.append(entry)
    lib["exams"] = exams
    if select:
        lib["last_selected"] = entry["name"]
    save_library(lib)
    return lib


def remove_exam(name: str) -> dict:
    lib = load_library()
    lib["exams"] = [e for e in lib.get("exams", []) if e["name"] != name]
    if lib.get("last_selected") == name:
        lib["last_selected"] = None
    save_library(lib)
    return lib


def safe_filename(name: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|]+', "_", name).strip()
    return cleaned or "exam"


class QuietRequestHandler(http.server.SimpleHTTPRequestHandler):
    """콘솔이 없는(--windowed) 빌드에서는 요청 로그를 남길 곳이 없으므로 끈다.

    브라우저가 web/index.html, style.css, app.js를 캐시하면 앱을 새로 만들어도
    화면이 안 바뀐 것처럼 보일 수 있으므로 캐시를 끈다(로컬 전용 도구라 매
    요청 디스크에서 새로 읽어도 성능에 문제없다).
    """

    def log_message(self, format, *args):  # noqa: A002 - matches base signature
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        super().end_headers()


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("AWS 자격증 문제풀이")
        self.root.geometry("560x420")
        self.root.minsize(480, 360)

        self.httpd: http.server.ThreadingHTTPServer | None = None
        self.lib = load_library()

        self._build_ui()
        self._refresh_list(select_name=self.lib.get("last_selected"))
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------- UI ----------

    def _build_ui(self):
        pad = {"padx": 12, "pady": 6}

        title = ttk.Label(self.root, text="AWS 자격증 문제풀이", font=("Segoe UI", 16, "bold"))
        title.pack(anchor="w", **pad)

        subtitle = ttk.Label(
            self.root,
            text="변환해 둔 시험 중 하나를 골라 시작하거나, 새 PDF를 추가하세요.",
            foreground="#555",
        )
        subtitle.pack(anchor="w", padx=12)

        list_frame = ttk.Frame(self.root)
        list_frame.pack(fill="both", expand=True, padx=12, pady=(10, 6))

        self.listbox = tk.Listbox(list_frame, activestyle="dotbox", font=("Segoe UI", 11))
        self.listbox.pack(side="left", fill="both", expand=True)
        self.listbox.bind("<Double-Button-1>", lambda e: self.start_selected())

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.listbox.config(yscrollcommand=scrollbar.set)

        btn_row1 = ttk.Frame(self.root)
        btn_row1.pack(fill="x", padx=12, pady=(0, 4))
        ttk.Button(btn_row1, text="▶ 시작하기", command=self.start_selected).pack(side="left")
        ttk.Button(btn_row1, text="PDF 추가", command=self.add_pdf).pack(side="left", padx=6)
        ttk.Button(btn_row1, text="다시 변환", command=self.reconvert_selected).pack(side="left")
        ttk.Button(btn_row1, text="영문 PDF 연결", command=self.link_english_pdf).pack(side="left", padx=6)

        btn_row2 = ttk.Frame(self.root)
        btn_row2.pack(fill="x", padx=12, pady=(0, 4))
        ttk.Button(btn_row2, text="이름 변경", command=self.rename_selected).pack(side="left")
        ttk.Button(btn_row2, text="삭제", command=self.delete_selected).pack(side="left", padx=6)

        self.status_var = tk.StringVar(value="준비됨")
        status = ttk.Label(self.root, textvariable=self.status_var, foreground="#0a7d32")
        status.pack(anchor="w", padx=12, pady=(4, 10))

    # ---------- library <-> UI ----------

    def _entries(self):
        """라이브러리 항목 + 항상 존재하는 샘플 항목을 최근 사용 순으로 반환."""
        exams = sorted(self.lib.get("exams", []), key=lambda e: e.get("last_used", ""), reverse=True)
        sample = {
            "name": "샘플 문제 (동작 확인용)",
            "json_path": str(SAMPLE_JSON),
            "is_sample": True,
        }
        return exams + [sample]

    def _refresh_list(self, select_name=None):
        self.listbox.delete(0, "end")
        self._current_entries = self._entries()
        for entry in self._current_entries:
            label = entry["name"]
            if entry.get("last_used") and not entry.get("is_sample"):
                label += f"  (마지막 사용: {entry['last_used'][:16].replace('T', ' ')})"
            self.listbox.insert("end", label)

        target_idx = 0
        if select_name:
            for idx, entry in enumerate(self._current_entries):
                if entry["name"] == select_name:
                    target_idx = idx
                    break
        if self._current_entries:
            self.listbox.selection_set(target_idx)
            self.listbox.activate(target_idx)

    def _selected_entry(self):
        sel = self.listbox.curselection()
        if not sel:
            return None
        return self._current_entries[sel[0]]

    # ---------- actions ----------

    def add_pdf(self):
        pdf_path = filedialog.askopenfilename(
            title="시험 덤프 PDF 선택 (한글판)",
            filetypes=[("PDF 파일", "*.pdf")],
        )
        if not pdf_path:
            return

        default_name = Path(pdf_path).stem
        name = simpledialog.askstring(
            "시험 이름", "목록에 표시할 이름을 입력하세요:", initialvalue=default_name
        )
        if not name:
            return

        en_pdf_path = None
        if messagebox.askyesno(
            "영문 원문 PDF",
            "같은 시험의 영문 원본 PDF도 가지고 있나요?\n"
            "함께 등록하면 실전 모드에서 'View in English' 팝업에 실제 영문 원문이 표시됩니다.",
        ):
            en_pdf_path = filedialog.askopenfilename(
                title="영문 원본 PDF 선택",
                filetypes=[("PDF 파일", "*.pdf")],
            )

        self._convert_and_register(pdf_path, name, en_pdf_path or None)

    def reconvert_selected(self):
        entry = self._selected_entry()
        if not entry or entry.get("is_sample"):
            messagebox.showinfo("안내", "다시 변환할 시험을 목록에서 선택하세요.")
            return
        pdf_path = entry.get("pdf_path")
        if not pdf_path or not Path(pdf_path).exists():
            messagebox.showwarning(
                "원본 PDF 없음",
                "원본 PDF 파일을 찾을 수 없습니다. 'PDF 추가'로 다시 등록해주세요.",
            )
            return
        self._convert_and_register(pdf_path, entry["name"], entry.get("en_pdf_path"))

    def link_english_pdf(self):
        entry = self._selected_entry()
        if not entry or entry.get("is_sample"):
            messagebox.showinfo("안내", "영문 PDF를 연결할 시험을 목록에서 선택하세요.")
            return
        pdf_path = entry.get("pdf_path")
        if not pdf_path or not Path(pdf_path).exists():
            messagebox.showwarning(
                "원본 PDF 없음",
                "한글 원본 PDF를 찾을 수 없습니다. 'PDF 추가'로 다시 등록해주세요.",
            )
            return
        en_pdf_path = filedialog.askopenfilename(
            title="영문 원본 PDF 선택",
            filetypes=[("PDF 파일", "*.pdf")],
        )
        if not en_pdf_path:
            return
        self._convert_and_register(pdf_path, entry["name"], en_pdf_path)

    def _convert_and_register(self, pdf_path: str, name: str, en_pdf_path: str = None):
        self.status_var.set("PDF를 변환하는 중...")
        self.root.update_idletasks()
        try:
            import parse_pdf

            questions, skipped = parse_pdf.parse_pdf(pdf_path)
            matched_en = None
            if en_pdf_path:
                questions_en, _ = parse_pdf.parse_pdf(en_pdf_path)
                matched_en = parse_pdf.merge_english(questions, questions_en)
        except Exception as exc:  # noqa: BLE001 - 사용자에게 원인을 그대로 보여줌
            self.status_var.set("변환 실패")
            messagebox.showerror("변환 실패", f"PDF 변환 중 오류가 발생했습니다:\n{exc}")
            return

        if not questions:
            self.status_var.set("변환 실패")
            messagebox.showerror(
                "변환 실패", "문제를 하나도 인식하지 못했습니다. PDF 포맷을 확인해주세요."
            )
            return

        LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
        json_path = LIBRARY_DIR / f"{safe_filename(name)}.json"
        json_path.write_text(json.dumps(questions, ensure_ascii=False, indent=2), encoding="utf-8")

        self.lib = upsert_exam(
            {
                "name": name,
                "pdf_path": str(Path(pdf_path).resolve()),
                "en_pdf_path": str(Path(en_pdf_path).resolve()) if en_pdf_path else None,
                "json_path": str(json_path),
                "added": datetime.now().isoformat(timespec="seconds"),
                "last_used": datetime.now().isoformat(timespec="seconds"),
            }
        )

        msg = f"문제 {len(questions)}개를 변환했습니다."
        if skipped:
            msg += f" ({len(skipped)}개는 인식하지 못해 건너뜀)"
        if matched_en is not None:
            msg += f" / 영문 원문 {matched_en}개 매칭됨"
        self.status_var.set(msg)
        self._refresh_list(select_name=name)

    def rename_selected(self):
        entry = self._selected_entry()
        if not entry or entry.get("is_sample"):
            messagebox.showinfo("안내", "이름을 변경할 시험을 목록에서 선택하세요.")
            return
        new_name = simpledialog.askstring("이름 변경", "새 이름을 입력하세요:", initialvalue=entry["name"])
        if not new_name or new_name == entry["name"]:
            return

        # 저장 직전에 디스크 최신 상태를 다시 읽어서 이름만 바꾼다 (다른
        # 인스턴스가 그 사이에 추가한 항목을 덮어쓰지 않도록).
        lib = load_library()
        if any(e["name"] == new_name for e in lib.get("exams", [])):
            messagebox.showerror("오류", "이미 같은 이름의 시험이 있습니다.")
            return
        found = False
        for e in lib.get("exams", []):
            if e["name"] == entry["name"]:
                e["name"] = new_name
                found = True
                break
        if not found:
            messagebox.showwarning("안내", "이 시험은 이미 목록에서 삭제된 것 같습니다.")
            self.lib = lib
            self._refresh_list()
            return
        if lib.get("last_selected") == entry["name"]:
            lib["last_selected"] = new_name
        save_library(lib)
        self.lib = lib
        self._refresh_list(select_name=new_name)

    def delete_selected(self):
        entry = self._selected_entry()
        if not entry or entry.get("is_sample"):
            messagebox.showinfo("안내", "삭제할 시험을 목록에서 선택하세요.")
            return
        if not messagebox.askyesno("삭제 확인", f"'{entry['name']}'을(를) 목록에서 삭제할까요?\n(원본 PDF는 삭제되지 않습니다)"):
            return
        self.lib = remove_exam(entry["name"])
        try:
            Path(entry["json_path"]).unlink(missing_ok=True)
        except OSError:
            pass
        self._refresh_list()

    def start_selected(self):
        entry = self._selected_entry()
        if not entry:
            messagebox.showinfo("안내", "시작할 시험을 목록에서 선택하거나 'PDF 추가'로 등록하세요.")
            return

        json_path = Path(entry["json_path"])
        if not json_path.exists():
            messagebox.showerror("오류", f"문제 파일을 찾을 수 없습니다:\n{json_path}")
            return

        DATA_DIR.mkdir(parents=True, exist_ok=True)
        ACTIVE_JSON.write_bytes(json_path.read_bytes())

        if not entry.get("is_sample"):
            lib = load_library()
            for e in lib.get("exams", []):
                if e["name"] == entry["name"]:
                    e["last_used"] = datetime.now().isoformat(timespec="seconds")
            lib["last_selected"] = entry["name"]
            save_library(lib)
            self.lib = lib
            self._refresh_list(select_name=entry["name"])

        self._ensure_server()
        webbrowser.open(f"http://127.0.0.1:{PORT}/web/index.html")
        self.status_var.set(f"'{entry['name']}' 시작됨 - 브라우저를 확인하세요.")

    def _ensure_server(self):
        if self.httpd is not None:
            return
        handler = functools.partial(QuietRequestHandler, directory=str(BASE_DIR))
        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), handler)
        thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        thread.start()

    def _on_close(self):
        if self.httpd is not None:
            self.httpd.shutdown()
            self.httpd.server_close()
        self.root.destroy()


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
