from flask import Flask, render_template_string, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
import random
import requests  # Для поиска по Википедии

# --- LLM (DeepInfra) integration ---
import os
import requests as _requests

DEEPINFRA_API_KEY = os.getenv("DEEPINFRA_API_KEY")

def ask_llm(message, system_prompt="Ты умный помощник. Отвечай кратко и по-русски."):
    """Call DeepInfra OpenAI-compatible endpoint if API key is set.
    Returns string answer or None on error / not configured.
    """
    if not DEEPINFRA_API_KEY:
        return None
    try:
        url = "https://api.deepinfra.com/v1/openai/chat/completions"
        headers = {
            "Authorization": f"Bearer {DEEPINFRA_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "meta-llama/Meta-Llama-3-8B-Instruct",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
            "temperature": 0.3,
        }
        resp = _requests.post(url, headers=headers, json=payload, timeout=60)
        data = resp.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content")
    except Exception as e:
        # Fail soft: don't break the app if LLM call fails
        print("LLM error:", e)
        return None
import re

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
app.secret_key = 'secretkey'
db = SQLAlchemy(app)

# --- Модели ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(32), unique=True, nullable=False)
    password = db.Column(db.String(32), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    tariff = db.Column(db.String(16), default='demo')  # demo, standart, premium

class Support(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    text = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text)
    is_tariff = db.Column(db.Boolean, default=False)

class Knowledge(db.Model):  # Самообучающаяся база "вопрос-ответ"
    id = db.Column(db.Integer, primary_key=True)
    phrase = db.Column(db.String(256), nullable=False, unique=True)
    answer = db.Column(db.Text, nullable=False)

# --- Хелперы ---
def get_current_user():
    uid = session.get('user_id')
    if uid:
        return User.query.get(uid)
    return None

def init_db():
    with app.app_context():
        db.create_all()
        # Создаем админа если нет
        if not User.query.filter_by(login="Artem2013").first():
            db.session.add(User(login="Artem2013", password="Art2013Ar", is_admin=True, tariff="premium"))
            db.session.commit()

# --- Стиль и navbar ---
STYLE = """
<style>
body { min-height:100vh; background:linear-gradient(135deg,#b0e0ff,#e6d8ff,#f7c6f7,#d8f5e7); font-family:'Segoe UI',sans-serif; margin:0;}
.navbar {background:#fff7;box-shadow:0 2px 16px #b0e0ff66;}
.container-main {display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:75vh;}
h1 { font-size:2.7rem;font-weight:700;margin-top:38px;text-align:center;letter-spacing:1px;text-shadow:0 2px 12px #e2e6fa77;}
.sub {font-size:1.18rem;color:#49447a;text-align:center;margin-bottom:28px;}
@media (max-width:800px){h1{font-size:1.7rem}.container-main{padding:14px 2px;}}
.chat-container {background:#fff9;border-radius:16px;box-shadow:0 0 14px #c6c6e044;padding:16px;max-width:420px;width:100%;margin:0 auto;}
.chat-messages {max-height:350px;overflow-y:auto;margin-bottom:10px;}
.chat-bubble {margin:10px 0;padding:12px 16px;border-radius:16px;background:#f0f6ff;font-size:1rem;}
.chat-bubble.user {background:#d8f7e8;text-align:right;}
.chat-bubble.ai {background:#e7e6fd;text-align:left;}
@media (max-width:600px){.chat-container{max-width:97vw;}}
</style>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"/>
"""

def navbar(active="/"):
    user = get_current_user()
    return render_template_string("""
<nav class="navbar navbar-expand-lg mb-3">
  <div class="container">
    <a class="navbar-brand fw-bold" href="/">NeiroGPT</a>
    <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
      <span class="navbar-toggler-icon"></span>
    </button>
    <div class="collapse navbar-collapse" id="navbarNav">
      <ul class="navbar-nav me-auto mb-2 mb-lg-0">
        <li class="nav-item"><a class="nav-link {% if active=='/' %}active{% endif %}" href="/">Главная</a></li>
        {% if user %}
          <li class="nav-item"><a class="nav-link {% if active=='/chat' %}active{% endif %}" href="/chat">Чат</a></li>
          <li class="nav-item"><a class="nav-link {% if active=='/profile' %}active{% endif %}" href="/profile">Профиль</a></li>
          <li class="nav-item"><a class="nav-link {% if active=='/tariffs' %}active{% endif %}" href="/tariffs">Тарифы</a></li>
          <li class="nav-item"><a class="nav-link {% if active=='/support' %}active{% endif %}" href="/support">Техподдержка</a></li>
          {% if user.is_admin %}
            <li class="nav-item"><a class="nav-link {% if active=='/admin' %}active{% endif %}" href="/admin">Админка</a></li>
          {% endif %}
        {% endif %}
      </ul>
      <div class="d-flex">
        {% if user %}
          <span class="me-2">👤 {{ user.login }}</span>
          <a class="btn btn-outline-danger btn-sm" href="/logout">Выйти</a>
        {% else %}
          <a class="btn btn-primary btn-sm me-2" href="/login">Вход</a>
          <a class="btn btn-success btn-sm" href="/register">Регистрация</a>
        {% endif %}
      </div>
    </div>
  </div>
</nav>
""", user=user, active=active)

# --- Главная
@app.route("/")
def index():
    user = get_current_user()
    return render_template_string("""
    {{style|safe}}
    {{navbar|safe}}
    <div class="container-main">
      <h1>NeiroGPT — будущее уже здесь</h1>
      <div class="sub">Зарегистрируйтесь и пользуйтесь искусственным интеллектом прямо сейчас!</div>
      {% if not user %}
      <a href="/login" class="btn btn-primary btn-lg">Войти в чат</a>
      {% else %}
      <a href="/chat" class="btn btn-success btn-lg">Открыть чат</a>
      {% endif %}
    </div>
    """, style=STYLE, navbar=navbar("/"), user=user)

# --- Регистрация
@app.route("/register", methods=["GET", "POST"])
def register():
    if get_current_user(): return redirect("/chat")
    msg = ""
    if request.method == "POST":
        login = request.form["login"]
        password = request.form["password"]
        if User.query.filter_by(login=login).first():
            msg = "Пользователь уже существует!"
        else:
            u = User(login=login, password=password, is_admin=False, tariff="demo")
            db.session.add(u)
            db.session.commit()
            session['user_id'] = u.id
            session['chat'] = []
            return redirect("/chat")
    return render_template_string("""
    {{style|safe}}{{navbar|safe}}
    <div class="container d-flex flex-column align-items-center">
      <h2>Регистрация</h2>
      <form method="post" style="max-width:350px;width:100%;">
        <input class="form-control mb-2" name="login" placeholder="Логин" required>
        <input class="form-control mb-2" name="password" type="password" placeholder="Пароль" required>
        <button class="btn btn-success w-100">Создать аккаунт</button>
      </form>
      {% if msg %}<div class="alert alert-danger mt-2">{{msg}}</div>{% endif %}
    </div>
    """, style=STYLE, navbar=navbar("/register"), msg=msg)

# --- Вход
@app.route("/login", methods=["GET", "POST"])
def login():
    if get_current_user(): return redirect("/chat")
    msg = ""
    if request.method == "POST":
        login = request.form["login"]
        password = request.form["password"]
        u = User.query.filter_by(login=login, password=password).first()
        if u:
            session['user_id'] = u.id
            session['chat'] = []
            return redirect("/chat")
        else:
            msg = "Неверный логин или пароль!"
    return render_template_string("""
    {{style|safe}}{{navbar|safe}}
    <div class="container d-flex flex-column align-items-center">
      <h2>Вход</h2>
      <form method="post" style="max-width:350px;width:100%;">
        <input class="form-control mb-2" name="login" placeholder="Логин" required>
        <input class="form-control mb-2" name="password" type="password" placeholder="Пароль" required>
        <button class="btn btn-primary w-100">Войти</button>
      </form>
      {% if msg %}<div class="alert alert-danger mt-2">{{msg}}</div>{% endif %}
    </div>
    """, style=STYLE, navbar=navbar("/login"), msg=msg)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# --- Профиль пользователя
@app.route("/profile")
def profile():
    user = get_current_user()
    if not user:
        return redirect("/login")
    return render_template_string("""
    {{style|safe}}{{navbar|safe}}
    <div class="container mt-4" style="max-width:400px;">
      <h3>Профиль</h3>
      <b>Логин:</b> {{user.login}}<br>
      <b>Тариф:</b> {{user.tariff}}<br>
      <b>Роль:</b> {% if user.is_admin %}Админ{% else %}Пользователь{% endif %}<br>
    </div>
    """, style=STYLE, navbar=navbar("/profile"), user=user)

# --- Чат с ИИ (обучение)
@app.route("/chat", methods=["GET", "POST"])
def chat():
    user = get_current_user()
    if not user: return redirect("/login")
    if "chat" not in session or not isinstance(session["chat"], list):
        session["chat"] = []
    if request.method == "POST":
        text = request.form["text"].strip()
        if text:
            session["chat"].append({"from": "user", "text": text})
            ai_ans = smart_answer_learn(text)
            session["chat"].append({"from": "ai", "text": ai_ans})
    chat_history = session.get("chat", [])
    return render_template_string("""
    {{style|safe}}{{navbar|safe}}
    <div class="container chat-container mt-4">
      <div class="chat-messages" id="msglist">
        {% for m in chat %}
          <div class="chat-bubble {{m.from}}">{{m.text}}</div>
        {% endfor %}
      </div>
      <form method="post" class="d-flex gap-2" onsubmit="setTimeout(()=>{this.text.value=''},200)">
        <input autofocus autocomplete="off" name="text" class="form-control" placeholder="Ваш вопрос..." required onkeydown="if(event.key==='Enter'&&!event.shiftKey){this.form.submit();return false;}">
        <button class="btn btn-primary">Отправить</button>
      </form>
    </div>
    <script>
      setTimeout(()=>{let d=document.getElementById('msglist');d.scrollTop=d.scrollHeight;},100);
    </script>
    """, style=STYLE, navbar=navbar("/chat"), chat=chat_history)

# --- Тарифы (оставим твой шаблон)
@app.route("/tariffs")
def tariffs():
    return render_template_string("""
    {{style|safe}}{{navbar|safe}}
    <div class="container mt-4" style="max-width:740px;">
      <h3>Тарифы</h3>
      <div class="row row-cols-1 row-cols-md-3 g-3">
        <div class="col">
          <div class="card h-100 border-success">
            <div class="card-header text-success fw-bold">Демо</div>
            <div class="card-body"><b>Бесплатно</b><br>Обычный чат.</div>
            <div class="card-footer text-center">Подключено</div>
          </div>
        </div>
        <div class="col">
          <div class="card h-100 border-info">
            <div class="card-header text-info fw-bold">Стандарт</div>
            <div class="card-body"><b>199₽/мес</b><br>600 вопросов/мес.<br>Приоритетная поддержка.</div>
            <div class="card-footer text-center">
              <form method="post" action="/buy">
                <input type="hidden" name="tariff" value="standart">
                <button class="btn btn-outline-info btn-sm mt-2">Купить</button>
              </form>
            </div>
          </div>
        </div>
        <div class="col">
          <div class="card h-100 border-warning">
            <div class="card-header text-warning fw-bold">Премиум</div>
            <div class="card-body"><b>399₽/мес</b><br>2000 вопросов/мес.<br>VIP поддержка.</div>
            <div class="card-footer text-center">
              <form method="post" action="/buy">
                <input type="hidden" name="tariff" value="premium">
                <button class="btn btn-outline-warning btn-sm mt-2">Купить</button>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
    """, style=STYLE, navbar=navbar("/tariffs"))

# --- Страница после "Купить" тариф (инструкция + заявка)
@app.route("/buy", methods=["POST"])
def buy():
    user = get_current_user()
    if not user: return redirect("/login")
    tariff = request.form.get("tariff")
    return render_template_string("""
    {{style|safe}}{{navbar|safe}}
    <div class="container mt-4" style="max-width:450px;">
      <h4>Покупка тарифа: <b>{{tariff.title()}}</b></h4>
      <div class="alert alert-info">
        <b>Инструкция:</b><br>
        1. Оплатите <b>{% if tariff=='standart' %}199₽{% elif tariff=='premium' %}399₽{% endif %}</b> на Сбербанк по номеру: <b>+7 (929) 842-53-70</b> или <b>+8 (929) 842-53-70</b><br>
        2. В сообщении к переводу напишите свой логин и выбранный тариф.<br>
        3. После оплаты — отправьте заявку ниже (или напишите в поддержку).
      </div>
      <form method="post" action="/tariff-request">
        <input type="hidden" name="tariff" value="{{tariff}}">
        <textarea name="msg" class="form-control mb-2" placeholder="Сообщение для заявки: например, оплата, ваш логин, детали..." required></textarea>
        <button class="btn btn-success w-100">Подать заявку</button>
      </form>
      <a href="/tariffs" class="btn btn-link mt-2">Назад к тарифам</a>
    </div>
    """, style=STYLE, navbar=navbar("/tariffs"), tariff=tariff)

# --- Сохранить заявку на тариф
@app.route("/tariff-request", methods=["POST"])
def tariff_request():
    user = get_current_user()
    if not user: return redirect("/login")
    text = request.form.get("msg")
    tariff = request.form.get("tariff")
    support = Support(user_id=user.id, text=f"Заявка на тариф {tariff}: {text}", is_tariff=True)
    db.session.add(support)
    db.session.commit()
    return render_template_string("""
    {{style|safe}}{{navbar|safe}}
    <div class="container mt-4" style="max-width:440px;">
      <div class="alert alert-success">
        Заявка отправлена! Мы рассмотрим её и свяжемся с вами.
      </div>
      <a href="/tariffs" class="btn btn-primary">Назад к тарифам</a>
    </div>
    """, style=STYLE, navbar=navbar("/tariffs"))

# --- Техподдержка (чат с ботом + общение с реальным админом)
@app.route("/support", methods=["GET", "POST"])
def support():
    user = get_current_user()
    if not user: return redirect("/login")
    chat = session.get("support_chat", [])
    msg = ""
    if request.method == "POST":
        text = request.form["text"]
        # Сохраняем как "вопрос"
        chat.append({"from": "user", "text": text})
        # Ответ от ИИ (обучается так же, как и обычный чат)
        ai_ans = smart_answer_learn(text, context="support")
        chat.append({"from": "ai", "text": ai_ans})
        session["support_chat"] = chat
        msg = "Ответ от поддержки получен!"
    return render_template_string("""
    {{style|safe}}{{navbar|safe}}
    <div class="container mt-4" style="max-width:480px;">
      <h3>Техподдержка</h3>
      <div class="chat-messages mb-2" style="height:240px;overflow:auto;background:#fff5;padding:12px;border-radius:12px;">
        {% for m in chat %}
          <div class="chat-bubble {{m.from}}">{{m.text}}</div>
        {% endfor %}
      </div>
      <form method="post">
        <textarea name="text" class="form-control mb-2" placeholder="Ваш вопрос..." required></textarea>
        <button class="btn btn-primary w-100">Отправить</button>
      </form>
      <a href="/support-admin" class="btn btn-link mt-2">Связаться с реальным человеком</a>
      {% if msg %}<div class="alert alert-success mt-2">{{msg}}</div>{% endif %}
    </div>
    """, style=STYLE, navbar=navbar("/support"), chat=chat, msg=msg)

# --- Поддержка: форма для реального админа (сохраняет вопрос в базу)
@app.route("/support-admin", methods=["GET", "POST"])
def support_admin():
    user = get_current_user()
    if not user: return redirect("/login")
    msg = ""
    if request.method == "POST":
        text = request.form["text"]
        sup = Support(user_id=user.id, text=text, is_tariff=False)
        db.session.add(sup)
        db.session.commit()
        msg = "Ваш вопрос отправлен реальному оператору!"
    return render_template_string("""
    {{style|safe}}{{navbar|safe}}
    <div class="container mt-4" style="max-width:440px;">
      <h4>Связь с реальным человеком</h4>
      <form method="post">
        <textarea name="text" class="form-control mb-2" placeholder="Ваш вопрос..." required></textarea>
        <button class="btn btn-warning w-100">Отправить</button>
      </form>
      {% if msg %}<div class="alert alert-info mt-2">{{msg}}</div>{% endif %}
      <a href="/support" class="btn btn-link mt-2">Назад</a>
    </div>
    """, style=STYLE, navbar=navbar("/support"), msg=msg)

# --- Админка
@app.route("/admin", methods=["GET", "POST"])
def admin():
    user = get_current_user()
    if not user or not user.is_admin:
        return redirect("/")
    # Обработка ответа на поддержку
    if request.method == "POST":
        if "support_id" in request.form:
            sup = Support.query.get(int(request.form["support_id"]))
            sup.answer = request.form["answer"]
            db.session.commit()
        elif "user_id" in request.form and "tariff" in request.form:
            u = User.query.get(int(request.form["user_id"]))
            u.tariff = request.form["tariff"]
            db.session.commit()
    users = User.query.all()
    support = Support.query.order_by(Support.id.desc()).all()
    return render_template_string("""
    {{style|safe}}{{navbar|safe}}
    <div class="container mt-4">
      <h3>Админ-панель</h3>
      <h5>Пользователи</h5>
      <table class="table table-bordered">
        <tr><th>ID</th><th>Логин</th><th>Тариф</th><th>Роль</th><th>Сменить тариф</th></tr>
        {% for u in users %}
        <tr>
          <td>{{u.id}}</td>
          <td>{{u.login}}</td>
          <td>{{u.tariff}}</td>
          <td>{% if u.is_admin %}Админ{% else %}Пользователь{% endif %}</td>
          <td>
            <form method="post" class="d-flex gap-2">
              <input type="hidden" name="user_id" value="{{u.id}}">
              <select name="tariff" class="form-select form-select-sm" style="max-width:120px;">
                <option value="demo" {% if u.tariff=='demo' %}selected{% endif %}>demo</option>
                <option value="standart" {% if u.tariff=='standart' %}selected{% endif %}>standart</option>
                <option value="premium" {% if u.tariff=='premium' %}selected{% endif %}>premium</option>
              </select>
              <button class="btn btn-sm btn-outline-success">OK</button>
            </form>
          </td>
        </tr>
        {% endfor %}
      </table>
      <h5 class="mt-4">Заявки и поддержка</h5>
      <table class="table table-sm table-bordered">
        <tr><th>ID</th><th>Пользователь</th><th>Тип</th><th>Сообщение</th><th>Ответ</th><th>Действие</th></tr>
        {% for s in support %}
        <tr>
          <td>{{s.id}}</td>
          <td>
            {% for u in users %}
              {% if u.id == s.user_id %}
                {{u.login}}
              {% endif %}
            {% endfor %}
          </td>
          <td>{% if s.is_tariff %}<b>Заявка на тариф</b>{% else %}Вопрос{% endif %}</td>
          <td>{{s.text}}</td>
          <td>{{s.answer or "-"}}</td>
          <td>
            <form method="post" style="min-width:160px;">
              <input type="hidden" name="support_id" value="{{s.id}}">
              <input type="text" name="answer" placeholder="Ответ..." class="form-control form-control-sm mb-1" value="{{s.answer or ''}}">
              <button class="btn btn-sm btn-primary">Ответить</button>
            </form>
          </td>
        </tr>
        {% endfor %}
      </table>
    </div>
    """, style=STYLE, navbar=navbar("/admin"), users=users, support=support)

# --- Реализация "самообучения" и поиска
def smart_answer_learn(text, context=None):
    text_l = text.lower()
    # 1. Поиск по базе знаний (фразы пользователей)
    for know in Knowledge.query.all():
        if know.phrase in text_l:
            return know.answer
    # 2. Ключевые слова из SMART_WORDS
    for i, key in enumerate(SMART_WORDS):
        if key in text_l:
            return SMART_ANSWERS[i % len(SMART_ANSWERS)]
    # 3. Если нет — ищем в Википедии
    wiki_answer = search_wikipedia(text)
    if wiki_answer:
        # Имитируем "уникальный" ответ (замена некоторых слов)
        uniq = wiki_answer.replace(" — ", " это ").replace(" Википедия", " энциклопедия")
        # Сохраняем новый опыт в базу знаний для будущих ответов
        db.session.add(Knowledge(phrase=text_l[:120], answer=uniq[:350]))
        db.session.commit()
        return uniq
    # 4. Если вообще ничего не найдено — генерируем уникальный ответ
    answer = f"Интересный вопрос! Я обязательно изучу это глубже и скоро смогу ответить."
    db.session.add(Knowledge(phrase=text_l[:120], answer=answer))
    db.session.commit()
    return answer

def search_wikipedia(query):
    """Ищет краткий ответ в Википедии (ru)"""
    try:
        url = f"https://ru.wikipedia.org/api/rest_v1/page/summary/{query.replace(' ','_')}"
        r = requests.get(url, timeout=2)
        if r.status_code == 200 and "extract" in r.json():
            text = r.json()["extract"]
            # Обрезаем до предложения (до точки)
            s = re.split(r'[.!?]', text)
            if s and len(s[0]) > 12:
                return s[0]
            return text[:180]
    except Exception:
        pass
    
    # 4. Попытка спросить у LLM (DeepInfra), если настроен ключ
    llm = ask_llm(text)
    if llm:
        try:
            # сохраняем новый опыт
            if not Knowledge.query.filter_by(phrase=text.lower()).first():
                db.session.add(Knowledge(phrase=text.lower(), answer=llm))
                db.session.commit()
        except Exception as _e:
            print("save LLM answer failed:", _e)
        return llm
    return None

# --- Ключевые слова и ответы для ИИ
SMART_WORDS = [
    "привет", "как дела", "погода", "новости", "курс доллара", "биткоин", "путин", "что такое", "кто такой", "когда",
    "почему", "как работает", "откуда", "сколько стоит", "анекдот", "расскажи шутку", "посоветуй фильм", "цитата", "мотивируй",
    "совет", "рецепт", "игра", "любовь", "работа", "python", "java", "бот", "кот", "погода завтра", "учёба", "мем", "юмор",
    "правда", "интересный факт", "деньги", "счастье", "здоровье", "рейтинг", "top", "гороскоп", "будущее", "дружба", "страна",
    "власть", "психология", "нейросеть", "инструкция", "sql", "flask", "react", "vue", "сайт"
]
SMART_ANSWERS = [
    "Привет! Я всегда рад общаться.",
    "Всё отлично, работаю для вас 24/7!",
    "Погода сегодня отличная — самое время сделать что-то новое.",
    "Вот свежие новости России: ...",
    "Курс доллара уточните на сайте банка, но могу примерно рассказать.",
    "Биткоин сейчас очень популярен среди инвесторов.",
    "Владимир Владимирович Путин — Президент РФ.",
    "Это очень интересный вопрос! Сейчас расскажу подробно.",
    "Этот термин часто используется, например...",
    "Расскажу коротко: ...",
    "Вот как это работает: ...",
    "Обычно так бывает потому что ...",
    "Рецепт дня — борщ по-домашнему.",
    "Вам стоит попробовать фильм 'Гарри Поттер' — отличный выбор!",
    "Держите цитату: 'Будущее принадлежит тем, кто верит в красоту своей мечты.'",
    "Шутка дня: Заходит нейросеть в бар, а бармен ей: 'Тебя не обслуживаем!'",
    "Мой совет — не бойтесь пробовать новое!",
    "В игре важна стратегия и удача!",
    "Любовь — великая сила, вдохновляющая людей.",
    "Работа — это путь к росту и успеху.",
    "Python — популярный язык программирования. Могу привести пример кода, если нужно!",
    "Java — строго типизированный язык. Отлично подходит для крупных проектов.",
    "Боты делают жизнь проще. Могу подсказать как их создать.",
    "Коты — лучшие антидепрессанты!",
    "Погода завтра: возможно, солнечно, как ваше настроение.",
    "Учёба — ключ к знаниям и будущему.",
    "Вот свежий мем: когда чат-бот становится твоим лучшим другом...",
    "Юмор — отличное средство от стресса.",
    "Правда — это основа доверия.",
    "Факт: мозг человека весит в среднем 1.4 кг!",
    "Деньги — инструмент, а не цель.",
    "Счастье в мелочах. Наслаждайтесь каждым моментом!",
    "Здоровье — главное богатство.",
    "Вот топ-3 интересных книги...",
    "Топ фильмов — посоветую индивидуально!",
    "Гороскоп: у вас всё получится!",
    "Будущее — за искусственным интеллектом.",
    "Дружба — опора в жизни.",
    "Каждая страна уникальна и интересна.",
    "Власть — большая ответственность.",
    "Психология — наука о душе.",
    "Нейросеть — это структура, вдохновлённая мозгом человека.",
    "Вот простая инструкция...",
    "SQL — язык для работы с базой данных.",
    "Flask — микро-фреймворк на Python.",
    "React — библиотека для фронтенда.",
    "Vue — ещё одна библиотека для UI.",
    "Сайт — твой виртуальный офис :)"
]

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)