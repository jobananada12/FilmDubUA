import os
import shutil
import subprocess
import tempfile
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import pyttsx3

APP_TITLE = "FilmDubUA — українська озвучка"


def ffmpeg_path():
    return shutil.which("ffmpeg")


def get_voices():
    engine = pyttsx3.init()
    voices = engine.getProperty("voices")
    engine.stop()
    return voices


def make_tts(text, output, voice_id, rate):
    engine = pyttsx3.init()
    if voice_id:
        engine.setProperty("voice", voice_id)
    engine.setProperty("rate", int(rate))
    engine.setProperty("volume", 1.0)
    engine.save_to_file(text, output)
    engine.runAndWait()
    engine.stop()


def mux_video(video, audio, output, volume):
    cmd = [
        ffmpeg_path(), "-y", "-i", video, "-i", audio,
        "-filter:a", f"volume={volume}",
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-shortest", output,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-2500:])


class App:
    def __init__(self, root):
        self.root = root
        root.title(APP_TITLE)
        root.geometry("900x650")
        root.minsize(760, 560)

        self.video = tk.StringVar()
        self.output = tk.StringVar()
        self.status = tk.StringVar(value="Готово")
        self.rate = tk.IntVar(value=165)
        self.volume = tk.DoubleVar(value=1.0)
        self.voices = []

        top = ttk.Frame(root, padding=18)
        top.pack(fill="both", expand=True)

        ttk.Label(top, text="FilmDubUA", font=("Segoe UI", 24, "bold")).pack(anchor="w")
        ttk.Label(top, text="Безкоштовна українська озвучка відео", font=("Segoe UI", 11)).pack(anchor="w", pady=(0, 16))

        file_frame = ttk.LabelFrame(top, text="1. Відео", padding=12)
        file_frame.pack(fill="x", pady=6)
        ttk.Entry(file_frame, textvariable=self.video).pack(side="left", fill="x", expand=True)
        ttk.Button(file_frame, text="Вибрати…", command=self.choose_video).pack(side="left", padx=(8, 0))

        script_frame = ttk.LabelFrame(top, text="2. Текст озвучки", padding=12)
        script_frame.pack(fill="both", expand=True, pady=6)
        self.script = tk.Text(script_frame, height=12, wrap="word", font=("Segoe UI", 12))
        self.script.pack(fill="both", expand=True)
        self.script.insert("1.0", "Встав сюди текст української озвучки…")

        settings = ttk.LabelFrame(top, text="3. Голос і налаштування", padding=12)
        settings.pack(fill="x", pady=6)
        row = ttk.Frame(settings)
        row.pack(fill="x")
        ttk.Label(row, text="Голос:").pack(side="left")
        self.voice_combo = ttk.Combobox(row, state="readonly", width=48)
        self.voice_combo.pack(side="left", padx=8)
        ttk.Button(row, text="Оновити", command=self.load_voices).pack(side="left")

        row2 = ttk.Frame(settings)
        row2.pack(fill="x", pady=(10, 0))
        ttk.Label(row2, text="Швидкість:").pack(side="left")
        ttk.Scale(row2, from_=80, to=240, variable=self.rate, orient="horizontal", length=220).pack(side="left", padx=8)
        ttk.Label(row2, textvariable=self.rate).pack(side="left")
        ttk.Label(row2, text="   Гучність:").pack(side="left")
        ttk.Scale(row2, from_=0.2, to=2.0, variable=self.volume, orient="horizontal", length=180).pack(side="left", padx=8)
        ttk.Label(row2, text="1.0×").pack(side="left")

        out = ttk.Frame(top)
        out.pack(fill="x", pady=6)
        ttk.Label(out, text="Файл результату:").pack(side="left")
        ttk.Entry(out, textvariable=self.output).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(out, text="Зберегти як…", command=self.choose_output).pack(side="left")

        bottom = ttk.Frame(top)
        bottom.pack(fill="x", pady=(10, 0))
        self.progress = ttk.Progressbar(bottom, mode="indeterminate")
        self.progress.pack(fill="x", side="top")
        ttk.Label(bottom, textvariable=self.status).pack(anchor="w", pady=5)
        self.export_btn = ttk.Button(bottom, text="🎬 СТВОРИТИ ОЗВУЧЕНЕ ВІДЕО", command=self.export)
        self.export_btn.pack(fill="x", ipady=8)

        self.load_voices()

    def choose_video(self):
        path = filedialog.askopenfilename(filetypes=[("Відео", "*.mp4 *.mkv *.mov *.avi"), ("Усі файли", "*.*")])
        if path:
            self.video.set(path)
            base = os.path.splitext(path)[0]
            self.output.set(base + "_dubbed.mp4")

    def choose_output(self):
        path = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4", "*.mp4")])
        if path:
            self.output.set(path)

    def load_voices(self):
        try:
            self.voices = get_voices()
            names = []
            for v in self.voices:
                name = getattr(v, "name", None) or getattr(v, "id", "Unknown")
                names.append(str(name))
            self.voice_combo["values"] = names
            if names:
                self.voice_combo.current(0)
            self.status.set(f"Знайдено голосів Windows: {len(names)}")
        except Exception as e:
            self.status.set("Не вдалося отримати голоси")
            messagebox.showerror("Помилка TTS", str(e))

    def export(self):
        if not self.video.get() or not os.path.isfile(self.video.get()):
            messagebox.showwarning("Відео", "Спочатку вибери відео.")
            return
        text = self.script.get("1.0", "end").strip()
        if not text or text.startswith("Встав сюди"):
            messagebox.showwarning("Текст", "Введи текст для озвучки.")
            return
        if not ffmpeg_path():
            messagebox.showerror("FFmpeg не знайдено", "Встанови FFmpeg та додай його до PATH, потім перезапусти програму.")
            return
        if not self.output.get():
            self.choose_output()
        if not self.output.get():
            return

        self.export_btn.config(state="disabled")
        self.progress.start(12)
        self.status.set("Створюю голос…")
        threading.Thread(target=self._worker, args=(text,), daemon=True).start()

    def _worker(self, text):
        try:
            with tempfile.TemporaryDirectory() as td:
                audio = os.path.join(td, "voice.wav")
                idx = self.voice_combo.current()
                voice_id = self.voices[idx].id if 0 <= idx < len(self.voices) else None
                make_tts(text, audio, voice_id, self.rate.get())
                self.root.after(0, lambda: self.status.set("Збираю відео…"))
                mux_video(self.video.get(), audio, self.output.get(), self.volume.get())
            self.root.after(0, self.done)
        except Exception as e:
            self.root.after(0, lambda: self.failed(str(e)))

    def done(self):
        self.progress.stop()
        self.export_btn.config(state="normal")
        self.status.set("✅ Готово: " + self.output.get())
        messagebox.showinfo("Готово", "Озвучене відео створено!")

    def failed(self, error):
        self.progress.stop()
        self.export_btn.config(state="normal")
        self.status.set("❌ Помилка")
        messagebox.showerror("Помилка", error)


if __name__ == "__main__":
    root = tk.Tk()
    try:
        root.iconname("FilmDubUA")
    except Exception:
        pass
    App(root)
    root.mainloop()
