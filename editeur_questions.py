#!/usr/bin/env python3
"""Éditeur de questions · Examen SeeD (Final Fantasy VIII)

Lance :  python editeur_questions.py [fichier.json]
Aucune installation : utilise uniquement la bibliothèque standard (tkinter).

Format du fichier (un fichier par niveau) :
[
  {"q": "Question ?", "a": "Bonne réponse", "w": ["Faux 1", "Faux 2", "Faux 3"]}
]
Dans le formulaire, le PREMIER choix est toujours la bonne réponse.
"""
import json
import os
import shutil
import sys

MIN_QUESTIONS = 10  # minimum exigé par le site pour lancer un examen


# --------------------------------------------------------------------------
# Logique fichier (sans interface)
# --------------------------------------------------------------------------
def norm(text):
    return " ".join(str(text).split()).lower()


def clean(item):
    """Accepte {q,a,w} ou {question,bonne,faux} ; renvoie un dict propre ou None."""
    if not isinstance(item, dict):
        return None
    q = item.get("q") or item.get("question")
    a = item.get("a") or item.get("bonne") or item.get("reponse")
    w = item.get("w") or item.get("faux") or item.get("mauvaises")
    if not (isinstance(q, str) and isinstance(a, str) and isinstance(w, list) and len(w) == 3):
        return None
    out = {"q": q.strip(), "a": a.strip(), "w": [str(x).strip() for x in w]}
    choices = [out["a"], *out["w"]]
    if not out["q"] or any(not c for c in choices) or len({norm(c) for c in choices}) != 4:
        return None
    return out


def load_questions(path):
    """Renvoie (liste de questions valides, nombre d'entrées invalides)."""
    with open(path, encoding="utf-8-sig") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(
            "Le fichier doit contenir une liste de questions (un fichier par niveau).\n"
            'Exemple : [{"q":"…","a":"…","w":["…","…","…"]}]'
        )
    cleaned = [clean(x) for x in data]
    return [x for x in cleaned if x], cleaned.count(None)


def save_questions(path, items, make_backup=False):
    """Écriture atomique en UTF-8 (une question par ligne, comme le site l'attend)."""
    if make_backup and os.path.exists(path):
        shutil.copy2(path, path + ".bak")
    body = ",\n".join("  " + json.dumps(x, ensure_ascii=False) for x in items)
    text = "[\n" + body + "\n]\n" if items else "[]\n"
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    os.replace(tmp, path)


# --------------------------------------------------------------------------
# Interface
# --------------------------------------------------------------------------
def run_gui(start_path=None):
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    class App(tk.Tk):
        def __init__(self):
            super().__init__()
            self.title("Éditeur de questions · Examen SeeD")
            self.geometry("1150x720")
            self.minsize(900, 560)
            self.path = None
            self.items = []
            self.backed_up = False
            self.filter_var = tk.StringVar()
            self.filter_var.trace_add("write", lambda *_: self.refresh())
            self.build()
            self.refresh()
            if start_path:
                self.load(start_path)

        # ---- construction ------------------------------------------------
        def build(self):
            top = ttk.Frame(self, padding=(10, 8))
            top.pack(fill="x")
            ttk.Button(top, text="Ouvrir un JSON…", command=self.open_file).pack(side="left")
            ttk.Button(top, text="Nouveau fichier…", command=self.new_file).pack(side="left", padx=6)
            self.file_label = ttk.Label(top, text="Aucun fichier chargé", font=("", 10, "bold"))
            self.file_label.pack(side="left", padx=12)
            ttk.Entry(top, textvariable=self.filter_var, width=28).pack(side="right")
            ttk.Label(top, text="Filtrer :").pack(side="right", padx=(0, 6))

            mid = ttk.Frame(self, padding=(10, 0))
            mid.pack(fill="both", expand=True)
            cols = ("n", "q", "a", "w1", "w2", "w3")
            self.tree = ttk.Treeview(mid, columns=cols, show="headings", selectmode="extended")
            heads = ("#", "Question", "✔ Bonne réponse", "Faux 1", "Faux 2", "Faux 3")
            widths = (45, 430, 170, 150, 150, 150)
            for c, h, w in zip(cols, heads, widths):
                self.tree.heading(c, text=h)
                self.tree.column(c, width=w, anchor="w", stretch=(c == "q"))
            vs = ttk.Scrollbar(mid, orient="vertical", command=self.tree.yview)
            hs = ttk.Scrollbar(mid, orient="horizontal", command=self.tree.xview)
            self.tree.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)
            self.tree.grid(row=0, column=0, sticky="nsew")
            vs.grid(row=0, column=1, sticky="ns")
            hs.grid(row=1, column=0, sticky="ew")
            mid.rowconfigure(0, weight=1)
            mid.columnconfigure(0, weight=1)
            self.tree.bind("<<TreeviewSelect>>", self.on_select)
            self.tree.bind("<Delete>", lambda e: self.delete())

            form = ttk.LabelFrame(self, text=" Créer / modifier une question ", padding=10)
            form.pack(fill="x", padx=10, pady=8)
            form.columnconfigure(1, weight=1)
            labels = ("Question", "✔ Bonne réponse (1er choix)", "Faux choix 1", "Faux choix 2", "Faux choix 3")
            self.entries = []
            for r, text in enumerate(labels):
                ttk.Label(form, text=text).grid(row=r, column=0, sticky="w", pady=2, padx=(0, 10))
                e = ttk.Entry(form)
                e.grid(row=r, column=1, sticky="ew", pady=2)
                e.bind("<Control-Return>", lambda ev: self.add())
                self.entries.append(e)
            btns = ttk.Frame(form)
            btns.grid(row=5, column=0, columnspan=2, sticky="w", pady=(8, 0))
            ttk.Button(btns, text="Ajouter (Ctrl+Entrée)", command=self.add).pack(side="left")
            ttk.Button(btns, text="Modifier la sélection", command=self.update_sel).pack(side="left", padx=6)
            ttk.Button(btns, text="Supprimer la sélection", command=self.delete).pack(side="left")
            ttk.Button(btns, text="Vider le formulaire", command=self.clear_form).pack(side="left", padx=6)

            self.status = ttk.Label(self, anchor="w", padding=(10, 4))
            self.status.pack(fill="x")

        # ---- fichiers ----------------------------------------------------
        def open_file(self):
            p = filedialog.askopenfilename(
                title="Ouvrir un fichier de questions",
                filetypes=[("Fichiers JSON", "*.json"), ("Tous les fichiers", "*.*")],
            )
            if p:
                self.load(p)

        def load(self, p):
            try:
                items, bad = load_questions(p)
            except Exception as e:  # noqa: BLE001
                messagebox.showerror("Lecture impossible", f"{p}\n\n{e}")
                return
            self.path, self.items, self.backed_up = p, items, False
            if bad:
                messagebox.showwarning(
                    "Entrées ignorées",
                    f"{bad} entrée(s) invalide(s) ignorée(s) (champ vide, choix en double, mauvais format).\n"
                    "Elles disparaîtront du fichier au prochain enregistrement.",
                )
            self.clear_form()
            self.refresh()

        def new_file(self):
            p = filedialog.asksaveasfilename(
                title="Créer un fichier de questions",
                defaultextension=".json",
                filetypes=[("Fichiers JSON", "*.json")],
                initialfile="questions-cadet.json",
            )
            if not p:
                return
            self.path, self.items, self.backed_up = p, [], True
            self.save()
            self.refresh()

        def save(self):
            if not self.path:
                return False
            try:
                save_questions(self.path, self.items, make_backup=not self.backed_up)
                self.backed_up = True
                return True
            except OSError as e:
                messagebox.showerror("Enregistrement impossible", str(e))
                return False

        # ---- formulaire --------------------------------------------------
        def need_file(self):
            if self.path:
                return True
            messagebox.showinfo("Aucun fichier", "Ouvre un fichier JSON (ou crée-en un) avant d’ajouter des questions.")
            return False

        def read_form(self, ignore=None):
            vals = [e.get().strip() for e in self.entries]
            q, choices = vals[0], vals[1:]
            if not q or any(not c for c in choices):
                messagebox.showwarning("Champs manquants", "Remplis la question et les 4 choix.")
                return None
            if len({norm(c) for c in choices}) != 4:
                messagebox.showwarning("Choix en double", "Les 4 choix doivent être différents.")
                return None
            dup = [str(i + 1) for i, it in enumerate(self.items) if norm(it["q"]) == norm(q) and i != ignore]
            if dup and not messagebox.askyesno(
                "Doublon", f"Cette question existe déjà (n° {', '.join(dup)}).\nL’ajouter quand même ?"
            ):
                return None
            return {"q": q, "a": choices[0], "w": choices[1:]}

        def fill_form(self, it):
            for e, v in zip(self.entries, (it["q"], it["a"], *it["w"])):
                e.delete(0, "end")
                e.insert(0, v)

        def clear_form(self):
            for e in self.entries:
                e.delete(0, "end")

        # ---- actions -----------------------------------------------------
        def add(self):
            if not self.need_file():
                return
            it = self.read_form()
            if not it:
                return
            self.items.append(it)
            if self.save():
                self.clear_form()
                self.refresh(select=len(self.items) - 1)
                self.entries[0].focus_set()

        def selected(self):
            return sorted(int(i) for i in self.tree.selection())

        def update_sel(self):
            sel = self.selected()
            if len(sel) != 1:
                messagebox.showinfo("Modifier", "Sélectionne une seule ligne du tableau.")
                return
            it = self.read_form(ignore=sel[0])
            if it:
                self.items[sel[0]] = it
                if self.save():
                    self.refresh(select=sel[0])

        def delete(self):
            sel = self.selected()
            if not sel:
                return
            if not messagebox.askyesno("Supprimer", f"Supprimer {len(sel)} question(s) ?"):
                return
            for i in reversed(sel):
                del self.items[i]
            if self.save():
                self.clear_form()
                self.refresh()

        def on_select(self, _event=None):
            sel = self.selected()
            if len(sel) == 1:
                self.fill_form(self.items[sel[0]])

        # ---- affichage ---------------------------------------------------
        def refresh(self, select=None):
            flt = norm(self.filter_var.get())
            self.tree.delete(*self.tree.get_children())
            for i, it in enumerate(self.items):
                row = (i + 1, it["q"], it["a"], *it["w"])
                if flt and flt not in norm(" ".join(map(str, row[1:]))):
                    continue
                self.tree.insert("", "end", iid=str(i), values=row)
            if select is not None and self.tree.exists(str(select)):
                self.tree.selection_set(str(select))
                self.tree.see(str(select))
            n = len(self.items)
            if self.path:
                self.file_label.config(text=os.path.basename(self.path))
                note = "" if n >= MIN_QUESTIONS else f"  ⚠ le site exige au moins {MIN_QUESTIONS} questions"
                self.status.config(text=f"{n} question(s) · enregistrement automatique dans {self.path}{note}")
            else:
                self.file_label.config(text="Aucun fichier chargé")
                self.status.config(text="Ouvre un fichier JSON pour commencer.")

    App().mainloop()


if __name__ == "__main__":
    run_gui(sys.argv[1] if len(sys.argv) > 1 else None)
