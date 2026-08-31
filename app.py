import os
import subprocess
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

class FilmDubUA:
    def __init__(self, root):
        self.root=root; self.root.title('FilmDubUA — Mini Dubbing Studio'); self.root.geometry('1050x720'); self.video=''; self.build()
    def build(self):
        top=ttk.Frame(self.root,padding=12); top.pack(fill='x')
        ttk.Label(top,text='🎬 FilmDubUA',font=('Segoe UI',22,'bold')).pack(side='left'); ttk.Button(top,text='Відкрити відео',command=self.open_video).pack(side='right')
        self.video_label=ttk.Label(self.root,text='Відео не вибрано',padding=(12,0)); self.video_label.pack(fill='x')
        main=ttk.Panedwindow(self.root,orient='horizontal'); main.pack(fill='both',expand=True,padx=12,pady=8)
        left=ttk.Frame(main,padding=10); right=ttk.Frame(main,padding=10); main.add(left,weight=3); main.add(right,weight=2)
        ttk.Label(left,text='Таймлайн реплік',font=('Segoe UI',14,'bold')).pack(anchor='w')
        self.tree=ttk.Treeview(left,columns=('start','end','text'),show='headings',height=20)
        for c,t,w in [('start','Початок',90),('end','Кінець',90),('text','Текст',520)]: self.tree.heading(c,text=t); self.tree.column(c,width=w)
        self.tree.pack(fill='both',expand=True); self.tree.bind('<<TreeviewSelect>>',self.select_row)
        b=ttk.Frame(left); b.pack(fill='x',pady=8)
        ttk.Button(b,text='+ Додати',command=self.add_row).pack(side='left'); ttk.Button(b,text='Видалити',command=self.delete_row).pack(side='left',padx=5); ttk.Button(b,text='Очистити',command=self.clear_rows).pack(side='left')
        ttk.Label(right,text='Редактор',font=('Segoe UI',14,'bold')).pack(anchor='w')
        f=ttk.Frame(right); f.pack(fill='x',pady=8)
        ttk.Label(f,text='Початок (сек.)').grid(row=0,column=0,sticky='w'); ttk.Label(f,text='Кінець (сек.)').grid(row=1,column=0,sticky='w')
        self.start=tk.StringVar(value='0'); self.end=tk.StringVar(value='3'); ttk.Entry(f,textvariable=self.start,width=12).grid(row=0,column=1,padx=8,pady=3); ttk.Entry(f,textvariable=self.end,width=12).grid(row=1,column=1,padx=8,pady=3)
        ttk.Label(right,text='Текст репліки').pack(anchor='w'); self.text=tk.Text(right,height=8,wrap='word'); self.text.pack(fill='x',pady=5); ttk.Button(right,text='Застосувати',command=self.apply).pack(anchor='e')
        ttk.Separator(right).pack(fill='x',pady=14); ttk.Label(right,text='Голос',font=('Segoe UI',14,'bold')).pack(anchor='w')
        self.voice=ttk.Combobox(right,state='readonly'); self.voice.pack(fill='x',pady=6); self.load_voices()
        ttk.Label(right,text='Швидкість').pack(anchor='w'); self.rate=tk.IntVar(value=165); ttk.Scale(right,from_=80,to=240,variable=self.rate,orient='horizontal').pack(fill='x')
        ttk.Button(right,text='▶ Прослухати',command=self.preview).pack(fill='x',pady=5); ttk.Button(right,text='🎙 Експорт MP4',command=self.export).pack(fill='x',pady=5)
        self.status=ttk.Label(right,text='Готово'); self.status.pack(anchor='w',pady=8); self.add_row()
    def load_voices(self):
        if not pyttsx3: self.voice['values']=['pyttsx3 не встановлено']; self.voice.current(0); return
        try:
            e=pyttsx3.init(); vs=e.getProperty('voices'); self.voice['values']=[getattr(v,'name',str(v)) for v in vs];
            if vs:self.voice.current(0)
            e.stop()
        except Exception:self.voice['values']=['Системний голос Windows']; self.voice.current(0)
    def open_video(self):
        p=filedialog.askopenfilename(filetypes=[('Відео','*.mp4 *.mkv *.mov *.avi'),('Усі файли','*.*')]);
        if p:self.video=p; self.video_label.config(text=os.path.basename(p)); self.status.config(text='Відео завантажено')
    def add_row(self):
        i=self.tree.insert('','end',values=('0.0','3.0','Нова репліка')); self.tree.selection_set(i); self.select_row()
    def delete_row(self):
        for i in self.tree.selection():self.tree.delete(i)
    def clear_rows(self):
        for i in self.tree.get_children():self.tree.delete(i)
        self.add_row()
    def select_row(self,_=None):
        s=self.tree.selection()
        if s:
            v=self.tree.item(s[0],'values'); self.start.set(v[0]); self.end.set(v[1]); self.text.delete('1.0','end'); self.text.insert('1.0',v[2])
    def apply(self):
        s=self.tree.selection()
        if not s:return
        try: float(self.start.get()); float(self.end.get())
        except ValueError: messagebox.showerror('Помилка','Час має бути числом.'); return
        self.tree.item(s[0],values=(self.start.get(),self.end.get(),self.text.get('1.0','end').strip()))
    def engine(self):
        if not pyttsx3:raise RuntimeError('Встанови pyttsx3: pip install pyttsx3')
        e=pyttsx3.init(); e.setProperty('rate',int(self.rate.get())); vs=e.getProperty('voices'); idx=self.voice.current()
        if 0<=idx<len(vs):e.setProperty('voice',vs[idx].id)
        return e
    def preview(self):
        t=self.text.get('1.0','end').strip()
        if not t:return
        try:e=self.engine(); e.say(t); e.runAndWait(); e.stop()
        except Exception as x:messagebox.showerror('Озвучка',str(x))
    def export(self):
        if not self.video:messagebox.showwarning('FilmDubUA','Спочатку вибери відео.');return
        rows=[]
        for i in self.tree.get_children():
            a,b,t=self.tree.item(i,'values')
            if t.strip():rows.append((float(a),float(b),t.strip()))
        if not rows:messagebox.showwarning('FilmDubUA','Додай репліку.');return
        out=filedialog.asksaveasfilename(defaultextension='.mp4',filetypes=[('MP4','*.mp4')],initialfile='filmdubua_output.mp4')
        if not out:return
        self.status.config(text='Створюю озвучку...'); self.root.update()
        try:
            with tempfile.TemporaryDirectory() as td:
                tracks=[]
                for n,(_,_,t) in enumerate(rows):
                    wav=os.path.join(td,f'voice_{n}.wav'); e=self.engine(); e.save_to_file(t,wav); e.runAndWait(); e.stop(); tracks.append(wav)
                ins=[]; fs=[]
                for n,(row,wav) in enumerate(zip(rows,tracks)):
                    ins += ['-i',wav]; d=max(0,int(row[0]*1000)); fs.append(f'[{n+1}:a]adelay={d}|{d}[a{n}]')
                labels=''.join(f'[a{n}]' for n in range(len(rows))); fs.append(f'{labels}amix=inputs={len(rows)}:duration=longest[voice]')
                cmd=['ffmpeg','-y','-i',self.video]+ins+['-filter_complex',';'.join(fs),'-map','0:v:0','-map','[voice]','-c:v','copy','-c:a','aac','-shortest',out]
                subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
            self.status.config(text='Готово!'); messagebox.showinfo('FilmDubUA','Відео створено:\n'+out)
        except FileNotFoundError:messagebox.showerror('FFmpeg','FFmpeg не знайдений у PATH.')
        except Exception as x:messagebox.showerror('Експорт',str(x)); self.status.config(text='Помилка')

if __name__=='__main__':
    root=tk.Tk(); FilmDubUA(root); root.mainloop()
