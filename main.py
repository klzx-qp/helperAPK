"""
ИИ Ассистент — Android версия (Kivy + KivyMD)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Сборка APK на ПК:
  pip install buildozer
  buildozer android debug

Или через Google Colab — см. инструкцию в README.md
"""

import json
import os
import re
import threading
import requests
from datetime import datetime
from pathlib import Path

os.environ["KIVY_NO_ENV_CONFIG"] = "1"
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.core.window import Window
from kivy.utils import get_color_from_hex
from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.graphics import Color, RoundedRectangle, Rectangle

# ═══════════════════════════════════════════════════════════
#  НАСТРОЙКИ
# ═══════════════════════════════════════════════════════════
GOOGLE_API_KEY = "AQ.Ab8RN6I29IOjhHeuTNSr3vXN41-DS-rCtZnrPaQAmgTfJ8dX5w"

MODEL_CANDIDATES = [
    "gemini-2.5-flash", "gemini-2.0-flash",
    "gemini-2.0-flash-lite", "gemini-1.5-flash",
]
MODEL_NAME = ""

try:
    from android.storage import app_storage_path
    DATA_DIR = Path(app_storage_path())
except ImportError:
    DATA_DIR = Path("data")

DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = str(DATA_DIR / "agent_data.json")
MEMORY_FILES = {
    "max":   str(DATA_DIR / "memory_max.json"),
    "lena":  str(DATA_DIR / "memory_lena.json"),
    "anton": str(DATA_DIR / "memory_anton.json"),
}

BG      = get_color_from_hex("#1a1a2e")
SIDEBAR = get_color_from_hex("#16213e")
CARD    = get_color_from_hex("#1e2a45")
TEXT    = get_color_from_hex("#e8eaf6")
MUTED   = get_color_from_hex("#7986cb")
ACCENT  = get_color_from_hex("#5c6bc0")
RED     = get_color_from_hex("#ef5350")

AGENT_META = {
    "lena":  {"label": "Лена",  "color": get_color_from_hex("#00bfa5"),
               "bg": get_color_from_hex("#0d2e2a"), "letter": "Л"},
    "max":   {"label": "Макс",  "color": get_color_from_hex("#42a5f5"),
               "bg": get_color_from_hex("#0d1f3c"), "letter": "М"},
    "anton": {"label": "Антон", "color": get_color_from_hex("#ffca28"),
               "bg": get_color_from_hex("#2e2500"), "letter": "А"},
}

# ═══════════════════════════════════════════════════════════
#  БД
# ═══════════════════════════════════════════════════════════
EMPTY_DB: dict = {"calendar": [], "wallet": [], "notes": []}

def load_db():
    if os.path.exists(DB_PATH):
        try:
            with open(DB_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k in EMPTY_DB:
                data.setdefault(k, [])
            return data
        except Exception:
            pass
    return {k: list(v) for k, v in EMPTY_DB.items()}

def save_db(db):
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

def next_id(col):
    return max((x["id"] for x in col), default=0) + 1

def add_transaction(type_, amount, category="", description=""):
    if amount <= 0: return "❌ Сумма должна быть положительной."
    db = load_db()
    db["wallet"].append({"id": next_id(db["wallet"]), "type": type_,
                          "amount": amount, "category": category or "прочее",
                          "description": description,
                          "date": datetime.now().strftime("%Y-%m-%d")})
    save_db(db)
    return f"✅ {'Доход' if type_=='income' else 'Расход'} {amount} руб. ({category or 'прочее'})"

def get_balance():
    db = load_db()
    inc = sum(t["amount"] for t in db["wallet"] if t["type"] == "income")
    exp = sum(t["amount"] for t in db["wallet"] if t["type"] == "expense")
    return f"💰 Баланс: {inc-exp:.0f} руб. | Доходы: {inc:.0f} | Расходы: {exp:.0f}"

def add_calendar_event(title, date_, time_=""):
    db = load_db()
    db["calendar"].append({"id": next_id(db["calendar"]), "title": title,
                            "date": date_, "time": time_})
    save_db(db)
    return f"✅ Событие «{title}» на {date_}"

def get_calendar_events(date_filter=""):
    db = load_db()
    ev = [e for e in db["calendar"] if not date_filter or e.get("date") == date_filter]
    return "📅 " + " | ".join(f"[{e['id']}] {e['date']} {e['title']}" for e in ev) if ev else "📅 Событий нет."

def create_note(title, content, tag=""):
    db = load_db()
    db["notes"].append({"id": next_id(db["notes"]), "title": title,
                         "content": content, "tag": tag or "общее",
                         "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")})
    save_db(db)
    return f"✅ Заметка «{title}» сохранена."

def get_notes(tag_filter=""):
    db = load_db()
    notes = [n for n in db["notes"] if not tag_filter or n.get("tag") == tag_filter]
    return "📝 " + " | ".join(f"[{n['id']}] {n['title']}" for n in notes[:5]) if notes else "📝 Заметок нет."

def web_search(query):
    q = query.lower()
    if any(w in q for w in ["кафе","ресторан","поесть","обед"]):
        return "🔍 Кафе: 1. Уют ⭐4.7 | 2. Coffee Point ⭐4.5 | 3. Восток ⭐4.8"
    if any(w in q for w in ["вакансия","работа","фриланс","подработка"]):
        return "🔍 Вакансии: Python Junior 60-90т.р. | Фриланс 3000/заказ | QA 70-100т.р."
    return f"🔍 По «{query}» ничего не найдено."

# ═══════════════════════════════════════════════════════════
#  ПАМЯТЬ
# ═══════════════════════════════════════════════════════════
def load_memory(key):
    path = MEMORY_FILES.get(key, "")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                d = json.load(f)
            if isinstance(d, list): return d
        except Exception: pass
    return []

def save_memory(key, facts):
    with open(MEMORY_FILES[key], "w", encoding="utf-8") as f:
        json.dump(facts, f, ensure_ascii=False, indent=2)

def add_memory_fact(key, fact):
    facts = load_memory(key)
    if fact not in [f["fact"] for f in facts]:
        facts.append({"fact": fact, "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M")})
        save_memory(key, facts)
    return f"🧠 Запомнила: {fact}"

def forget_memory_fact(key, index):
    facts = load_memory(key)
    idx = index - 1
    if 0 <= idx < len(facts):
        removed = facts.pop(idx)
        save_memory(key, facts)
        return f"🗑 Забыла: {removed['fact']}"
    return f"❌ Факт #{index} не найден."

def format_memory_block(key):
    facts = load_memory(key)
    if not facts: return ""
    lines = ["=== ЧТО Я УЖЕ ЗНАЮ О ПОЛЬЗОВАТЕЛЕ ==="]
    for i, f in enumerate(facts, 1):
        lines.append(f"  {i}. {f['fact']}")
    lines.append("=== КОНЕЦ ПАМЯТИ ===")
    return "\n".join(lines)

# ═══════════════════════════════════════════════════════════
#  ПАРСЕР КОМАНД
# ═══════════════════════════════════════════════════════════
COMMAND_RE = re.compile(r"\[\[([A-Z_]+):([^\]]*)\]\]")

def parse_and_execute(text, agent_key):
    results = []
    found = COMMAND_RE.findall(text)
    clean = COMMAND_RE.sub("", text).strip()
    for cmd, raw in found:
        args = [a.strip() for a in raw.split("|")]
        def arg(i, d=""):
            return args[i] if i < len(args) else d
        result = ""
        try:
            if   cmd == "REMEMBER":    result = add_memory_fact(agent_key, arg(0))
            elif cmd == "FORGET":      result = forget_memory_fact(agent_key, int(arg(0)))
            elif cmd == "ADD_EVENT":   result = add_calendar_event(arg(0), arg(1), arg(2))
            elif cmd == "GET_EVENTS":  result = get_calendar_events(arg(0))
            elif cmd == "ADD_EXPENSE": result = add_transaction("expense", float(arg(0)), arg(1), arg(2))
            elif cmd == "ADD_INCOME":  result = add_transaction("income", float(arg(0)), arg(1), arg(2))
            elif cmd == "GET_BALANCE": result = get_balance()
            elif cmd == "ADD_NOTE":    result = create_note(arg(0), arg(1), arg(2))
            elif cmd == "GET_NOTES":   result = get_notes(arg(0))
            elif cmd == "SEARCH":      result = web_search(arg(0))
        except Exception as e:
            result = f"❌ Ошибка {cmd}: {e}"
        if result: results.append(result)
    return clean, results

# ═══════════════════════════════════════════════════════════
#  ПРОМПТЫ И СЕССИЯ
# ═══════════════════════════════════════════════════════════
TODAY = datetime.now().strftime("%Y-%m-%d")
MEM_INSTR = f"ПАМЯТЬ: [[REMEMBER:факт]] [[FORGET:номер]] Запоминай имя, ДР, предпочтения. Дата сегодня: {TODAY}."

def build_system(key):
    mem = format_memory_block(key)
    ms = f"\n{mem}\n" if mem else ""
    if key == "max":
        return f"Ты Max, программист-ассистент. {TODAY}.{ms} Отвечай на русском. {MEM_INSTR}"
    if key == "lena":
        return f"""Ты Лена, личный ассистент. {TODAY}.{ms} Отвечай на русском. {MEM_INSTR}
КОМАНДЫ: [[ADD_EXPENSE:сумма|кат|описание]] [[ADD_INCOME:сумма|кат|описание]]
[[GET_BALANCE:]] [[ADD_EVENT:название|YYYY-MM-DD|HH:MM]] [[GET_EVENTS:]]
[[ADD_NOTE:заголовок|текст|тег]] [[GET_NOTES:]] [[SEARCH:запрос]]"""
    return f"Ты Антон, карьерный ассистент. {TODAY}.{ms} Отвечай на русском. {MEM_INSTR} КОМАНДЫ: [[SEARCH:запрос]] [[ADD_NOTE:заголовок|текст|вакансия]] [[GET_NOTES:вакансия]]"

SESSION: dict = {"max": [], "lena": [], "anton": []}

def push(key, role, content):
    h = SESSION[key]
    h.append({"role": role, "parts": [{"text": content}]})
    if len(h) > 30: SESSION[key] = h[-30:]

# ═══════════════════════════════════════════════════════════
#  GEMINI
# ═══════════════════════════════════════════════════════════
def detect_model():
    """Проверяем модели через REST API (без SDK)."""
    for c in MODEL_CANDIDATES:
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"{c}:generateContent?key={GOOGLE_API_KEY}")
        payload = {"contents": [{"role": "user", "parts": [{"text": "Hi"}]}],
                   "generationConfig": {"maxOutputTokens": 5}}
        try:
            r = requests.post(url, json=payload, timeout=10)
            if r.status_code == 200 and "candidates" in r.json():
                return c
        except Exception:
            continue
    return ""

def call_gemini(agent_key, user_message):
    if not MODEL_NAME:
        return "❌ Модель не определена."

    # Формируем историю диалога в формате REST API Gemini
    contents = []
    for msg in SESSION[agent_key]:
        role = "user" if msg["role"] == "user" else "model"
        text = msg["parts"][0]["text"] if msg.get("parts") else ""
        contents.append({"role": role, "parts": [{"text": text}]})
    contents.append({"role": "user", "parts": [{"text": user_message}]})

    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{MODEL_NAME}:generateContent?key={GOOGLE_API_KEY}")
    payload = {
        "contents": contents,
        "systemInstruction": {"parts": [{"text": build_system(agent_key)}]},
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 2048},
    }

    try:
        r = requests.post(url, json=payload, timeout=30)
        if r.status_code == 429:
            return "❌ Лимит запросов. Подождите немного."
        if r.status_code in (401, 403):
            return "❌ Неверный API-ключ."
        data = r.json()
        if "candidates" in data:
            parts = data["candidates"][0].get("content", {}).get("parts", [])
            if parts:
                return parts[0].get("text", "⚠ Пустой ответ.")
        return f"❌ Ошибка API: {str(data)[:150]}"
    except Exception as e:
        return f"❌ Ошибка сети: {str(e)[:100]}"

# ═══════════════════════════════════════════════════════════
#  МАРШРУТИЗАТОР
# ═══════════════════════════════════════════════════════════
MAX_KW = ["код","python","javascript","алгоритм","функция","класс","баг","debug","flask","django","numpy","git","docker"]
ANT_KW = ["вакансия","работа","подработка","фриланс","резюме","карьера"]
LEN_KW = ["расход","доход","трата","купил","баланс","кошелёк","календарь","событие","встреча","заметка","кафе","деньги"]

def route(text):
    t = text.lower()
    sm = sum(1 for k in MAX_KW if k in t)
    sa = sum(1 for k in ANT_KW if k in t)
    sl = sum(1 for k in LEN_KW if k in t)
    if sm > 0 and sm >= sa and sm >= sl: return "max"
    if sa > 0 and sa >= sl: return "anton"
    return "lena"

# ═══════════════════════════════════════════════════════════
#  TTS ANDROID
# ═══════════════════════════════════════════════════════════
def speak_android(text, agent_key="lena"):
    clean = re.sub(r"\[\[.*?\]\]|[✅❌🧠📅💰📝🔍🗑⚠*_`#]", "", text).strip()
    if not clean: return
    try:
        from jnius import autoclass
        Locale = autoclass("java.util.Locale")
        TTS = autoclass("android.speech.tts.TextToSpeech")
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        activity = PythonActivity.mActivity
        holder = {}
        class Listener:
            def onInit(self, status):
                if status == TTS.SUCCESS:
                    e = holder.get("e")
                    if e:
                        e.setLanguage(Locale("ru", "RU"))
                        e.setSpeechRate(0.95)
                        e.speak(clean[:500], TTS.QUEUE_FLUSH, None, None)
        engine = TTS(activity, Listener(), 0)
        holder["e"] = engine
    except Exception:
        pass

# ═══════════════════════════════════════════════════════════
#  UI ВИДЖЕТЫ
# ═══════════════════════════════════════════════════════════
class Bubble(BoxLayout):
    def __init__(self, sender, text, **kwargs):
        super().__init__(orientation="horizontal", size_hint_y=None,
                          padding=dp(6), spacing=dp(6), **kwargs)
        is_user = sender == "user"
        bg_color = CARD if is_user else AGENT_META.get(sender, AGENT_META["lena"])["bg"]
        txt_color = TEXT if is_user else AGENT_META.get(sender, AGENT_META["lena"])["color"]

        if not is_user:
            meta = AGENT_META.get(sender, AGENT_META["lena"])
            av = Label(text=meta["letter"], color=meta["color"],
                       font_size=sp(15), bold=True,
                       size_hint=(None, None), size=(dp(32), dp(32)))
            self.add_widget(av)

        wrap = BoxLayout(orientation="vertical", size_hint_y=None, padding=dp(8))
        with wrap.canvas.before:
            Color(*bg_color)
            wrap._rect = RoundedRectangle(pos=wrap.pos, size=wrap.size, radius=[dp(10)])
        wrap.bind(pos=lambda w, v: setattr(w._rect, "pos", v),
                  size=lambda w, v: setattr(w._rect, "size", v))

        if not is_user:
            name = Label(text=meta["label"], color=meta["color"],
                         font_size=sp(10), bold=True,
                         size_hint_y=None, height=dp(16), halign="left")
            name.bind(size=lambda w, _: setattr(w, "text_size", (w.width, None)))
            wrap.add_widget(name)

        lbl = Label(text=text, color=txt_color, font_size=sp(14),
                    text_size=(Window.width * 0.72, None),
                    halign="left", valign="top", size_hint_y=None)
        lbl.bind(texture_size=lambda w, v: setattr(w, "height", v[1]))
        wrap.add_widget(lbl)
        wrap.bind(minimum_height=wrap.setter("height"))
        self.add_widget(wrap)

        if is_user:
            self.add_widget(Label(size_hint_x=0.08))

        self.bind(minimum_height=self.setter("height"))


class MainLayout(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        with self.canvas.before:
            Color(*BG)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda w, v: setattr(w._bg, "pos", v),
                  size=lambda w, v: setattr(w._bg, "size", v))

        self.selected_agent = "auto"
        self.voice_enabled = True
        self._agent_btns = {}

        # Панель агентов
        tab = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(46),
                        spacing=dp(3), padding=(dp(6), dp(4)))
        with tab.canvas.before:
            Color(*SIDEBAR)
            tab._bg = Rectangle(pos=tab.pos, size=tab.size)
        tab.bind(pos=lambda w, v: setattr(w._bg, "pos", v),
                 size=lambda w, v: setattr(w._bg, "size", v))

        for key, lbl in [("auto","🔀 Авто"),("lena","🟢 Лена"),
                          ("max","🔵 Макс"),("anton","🟡 Антон")]:
            btn = Button(text=lbl, font_size=sp(12), border=(0,0,0,0),
                         background_color=ACCENT if key=="auto" else SIDEBAR,
                         color=TEXT)
            btn.bind(on_press=lambda b, k=key: self._select(k))
            tab.add_widget(btn)
            self._agent_btns[key] = btn
        self.add_widget(tab)

        # Статус
        self.status = Label(text="⏳ Определяю модель...", color=MUTED,
                             font_size=sp(11), size_hint_y=None, height=dp(22),
                             halign="center")
        self.status.bind(size=lambda w,_: setattr(w, "text_size", (w.width, None)))
        self.add_widget(self.status)

        # Чат
        self.scroll = ScrollView(do_scroll_x=False)
        self.chat = BoxLayout(orientation="vertical", size_hint_y=None,
                               spacing=dp(4), padding=dp(6))
        self.chat.bind(minimum_height=self.chat.setter("height"))
        self.scroll.add_widget(self.chat)
        self.add_widget(self.scroll)

        # Ввод
        row = BoxLayout(orientation="horizontal", size_hint_y=None,
                        height=dp(54), padding=dp(6), spacing=dp(6))
        with row.canvas.before:
            Color(*SIDEBAR)
            row._bg = Rectangle(pos=row.pos, size=row.size)
        row.bind(pos=lambda w,v: setattr(w._bg,"pos",v),
                 size=lambda w,v: setattr(w._bg,"size",v))

        self.inp = TextInput(
            hint_text="Напишите...", multiline=False, font_size=sp(15),
            background_color=CARD, foreground_color=TEXT,
            cursor_color=ACCENT, hint_text_color=MUTED)
        self.inp.bind(on_text_validate=lambda _: self._send())
        row.add_widget(self.inp)

        self.mic_btn = Button(text="🎤", font_size=sp(20),
                               size_hint=(None,None), size=(dp(46),dp(46)),
                               background_color=get_color_from_hex("#37474f"),
                               border=(0,0,0,0))
        self.mic_btn.bind(on_press=lambda _: threading.Thread(
            target=self._listen, daemon=True).start())
        row.add_widget(self.mic_btn)

        send = Button(text="➤", font_size=sp(20),
                      size_hint=(None,None), size=(dp(46),dp(46)),
                      background_color=ACCENT, border=(0,0,0,0))
        send.bind(on_press=lambda _: self._send())
        row.add_widget(send)
        self.add_widget(row)

        self._sys_msg("👋 Добро пожаловать! Запускаю систему...")
        threading.Thread(target=self._init_model, daemon=True).start()

    def _select(self, key):
        self.selected_agent = key
        for k, b in self._agent_btns.items():
            b.background_color = ACCENT if k == key else SIDEBAR

    def _init_model(self):
        global MODEL_NAME
        MODEL_NAME = detect_model()
        msg = f"✅ Модель: {MODEL_NAME}" if MODEL_NAME else "❌ Модель не найдена. Проверьте ключ."
        Clock.schedule_once(lambda dt: setattr(self.status, "text", msg))
        Clock.schedule_once(lambda dt: self._sys_msg(msg))

    def _sys_msg(self, text):
        lbl = Label(text=text, color=MUTED, font_size=sp(11),
                    size_hint_y=None, height=dp(26), halign="center")
        lbl.bind(size=lambda w,_: setattr(w,"text_size",(w.width,None)))
        self.chat.add_widget(lbl)
        Clock.schedule_once(lambda dt: setattr(self.scroll,"scroll_y",0), 0.1)

    def _add_bubble(self, sender, text):
        b = Bubble(sender, text)
        self.chat.add_widget(b)
        Clock.schedule_once(lambda dt: setattr(self.scroll,"scroll_y",0), 0.15)

    def _send(self):
        text = self.inp.text.strip()
        if not text: return
        self.inp.text = ""
        forced = None
        low = text.lower()
        if low.startswith(("@макс","@max")):
            forced="max"; text=re.sub(r"^@\S+\s*","",text).strip()
        elif low.startswith(("@лена","@lena")):
            forced="lena"; text=re.sub(r"^@\S+\s*","",text).strip()
        elif low.startswith(("@антон","@anton")):
            forced="anton"; text=re.sub(r"^@\S+\s*","",text).strip()
        if not text: return
        self._add_bubble("user", text)
        agent = forced or (self.selected_agent if self.selected_agent!="auto" else route(text))
        Clock.schedule_once(lambda dt: self._sys_msg(
            f"⏳ {AGENT_META[agent]['label']} думает..."), 0.05)
        threading.Thread(target=self._run, args=(agent, text), daemon=True).start()

    def _run(self, agent_key, user_msg):
        raw = call_gemini(agent_key, user_msg)
        clean, cmd_results = (parse_and_execute(raw, agent_key)
                               if agent_key in ("lena","anton") else (raw, []))
        push(agent_key, "user", user_msg)
        push(agent_key, "model", raw)
        display = clean + ("\n\n" + "\n".join(cmd_results) if cmd_results else "")
        def upd(dt):
            self._add_bubble(agent_key, display)
            if self.voice_enabled:
                speak_android(display, agent_key)
        Clock.schedule_once(upd)

    def _listen(self):
        try:
            import speech_recognition as sr
            r = sr.Recognizer()
            Clock.schedule_once(lambda dt: setattr(
                self.mic_btn,"background_color",RED))
            with sr.Microphone() as src:
                r.adjust_for_ambient_noise(src, duration=0.3)
                audio = r.listen(src, timeout=8, phrase_time_limit=12)
            text = r.recognize_google(audio, language="ru-RU")
            Clock.schedule_once(lambda dt: setattr(
                self.mic_btn,"background_color",get_color_from_hex("#37474f")))
            Clock.schedule_once(lambda dt: setattr(self.inp,"text",text))
        except Exception:
            Clock.schedule_once(lambda dt: setattr(
                self.mic_btn,"background_color",get_color_from_hex("#37474f")))


class AIApp(App):
    def build(self):
        Window.clearcolor = BG
        self.title = "ИИ Ассистент"
        return MainLayout()

if __name__ == "__main__":
    AIApp().run()
