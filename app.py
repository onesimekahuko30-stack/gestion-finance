from flask import Flask, render_template, request, redirect, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib 
matplotlib.use('agg')
import os
TAUX_USD_CDF = 2400
app = Flask(__name__)
app.secret_key = "ULTRA_FINANCE_SECRET"
DB = "finance.db"

os.makedirs("static", exist_ok=True)

# =========================
# INIT DATABASE ULTRA
# =========================
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # 1. USERS (DOIT ÊTRE EN PREMIER)
    c.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT
    )
    """)

    # 2. RECETTES
    c.execute("""
    CREATE TABLE IF NOT EXISTS recettes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titre TEXT,
        montant REAL,
        devise TEXT,
        date TEXT
    )
    """)

    # 3. DEPENSES
    c.execute("""
    CREATE TABLE IF NOT EXISTS depenses(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titre TEXT,
        montant REAL,
        devise TEXT, 
        date TEXT
    )
    """)

    # 4. DETTES
    c.execute("""
    CREATE TABLE IF NOT EXISTS dettes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titre TEXT,
        montant REAL,
        devise TEXT, 
        date TEXT,
        statut TEXT
    )
    """)

    # 5. PROJETS
    c.execute("""
    CREATE TABLE IF NOT EXISTS projets(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT,
        budget REAL,
        devise TEXT, 
        avance REAL,
        statut TEXT
    )
    """)

    # ADMIN DEFAULT
    c.execute("SELECT * FROM users WHERE username='admin'")
    if not c.fetchone():
        c.execute(
            "INSERT INTO users(username,password,role) VALUES(?,?,?)",
            ("admin", generate_password_hash("1234"), "admin")
        )

    conn.commit()
    conn.close()

def convertir(montant, devise):
    if devise == "USD":
        return float(montant) * TAUX_USD_CDF
    return float(montant)
init_db()


def prediction_recettes():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT montant FROM recettes ORDER BY id DESC LIMIT 5")
    data = [x[0] for x in c.fetchall()]
    conn.close()

    if len(data) < 2:
        return 0

    return sum(data) / len(data)

def prediction_depenses():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT montant FROM depenses ORDER BY id DESC LIMIT 5")
    data = [x[0] for x in c.fetchall()]
    conn.close()

    if len(data) < 2:
        return 0

    return sum(data) / len(data)

def prediction_dettes():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT montant FROM dettes ORDER BY id DESC LIMIT 5")
    data = [x[0] for x in c.fetchall()]
    conn.close()

    if len(data) < 2:
        return 0

    return sum(data) / len(data)

def prediction_projets():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT budget FROM projets ORDER BY id DESC LIMIT 5")
    data = [x[0] for x in c.fetchall()]
    conn.close()

    if len(data) < 2:
        return 0

    return sum(data) / len(data)

# =========================
# LOGIN SECURISÉ
# =========================
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=?", (u,))
        user = c.fetchone()
        conn.close()

        if user and check_password_hash(user[2], p):
            session["user"] = user[1]
            session["role"] = user[3]
            return redirect("/dashboard")

        return """
<h2>❌ Identifiants incorrects</h2>

<a href='/'
style='
padding:12px;
background:#2563eb;
color:white;
text-decoration:none;
border-radius:10px;
'>
⬅️ Retour à la connexion
</a>
"""

    return render_template("login.html")


# =========================
# DASHBOARD ULTRA
# =========================
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/")

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT SUM(montant) FROM recettes")
    recettes = c.fetchone()[0] or 0

    c.execute("SELECT SUM(montant) FROM depenses")
    depenses = c.fetchone()[0] or 0

    c.execute("SELECT COUNT(*) FROM dettes WHERE statut='non payé'")
    dettes = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM projets")
    projets = c.fetchone()[0]

    conn.close()

    balance = recettes - depenses
    ratio = round((depenses / recettes) * 100, 2) if recettes > 0 else 0

    # GRAPH PROPRE
    plt.figure(figsize=(5,5))
    plt.bar(["Recettes", "Dépenses"], [recettes, depenses])
    plt.title("ULTRA FINANCE")
    plt.savefig("static/graph.png")
    plt.close()

    # PRÉVISIONS (GARDER UNE SEULE VERSION)
    recettes_pred = prediction_recettes()
    depenses_pred = prediction_depenses()
    dettes_pred = prediction_dettes()
    projets_pred = prediction_projets()

    # ALERT
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM dettes WHERE statut='non payé'")
    alert = len(c.fetchall())
    conn.close()

    return render_template(
        "dashboard.html",
        recettes=recettes,
        depenses=depenses,
        dettes=dettes,
        projets=projets,
        balance=balance,
        ratio=ratio,
        alert=alert,
        recettes_pred=recettes_pred,
        depenses_pred=depenses_pred,
        dettes_pred=dettes_pred,
        projets_pred=projets_pred
    )

# =========================
# RECETTES
# =========================
@app.route("/recettes", methods=["GET","POST"])
def recettes():
    if "user" not in session:
        return redirect("/")

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    if request.method == "POST":
        c.execute(
            "INSERT INTO recettes(titre,montant,date) VALUES(?,?,?)",
            (
    request.form["titre"],
    convertir(request.form["montant"], request.form.get("devise", "CDF")),
    datetime.now().strftime("%d/%m/%Y")
)
)
        conn.commit()
    c.execute("SELECT * FROM recettes ORDER BY id DESC")
    data = c.fetchall()
    conn.close()
    return render_template("recettes.html", data=data)


# =========================
# DEPENSES
# =========================
@app.route("/depenses", methods=["GET","POST"])
def depenses():
    if "user" not in session:
        return redirect("/")

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    if request.method == "POST":
        c.execute(
            "INSERT INTO depenses(titre,montant,date) VALUES(?,?,?)",
            (
    request.form["titre"],
    convertir(request.form["montant"], request.form.get("devise", "CDF")),
    datetime.now().strftime("%d/%m/%Y")
)       
)
        conn.commit()

    c.execute("SELECT * FROM depenses ORDER BY id DESC")
    data = c.fetchall()
    conn.close()

    return render_template("depenses.html", data=data)



# =========================
# DETTES (AVEC RETARD)
# =========================
@app.route("/dettes", methods=["GET","POST"])
def dettes():
    if "user" not in session:
        return redirect("/")

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    if request.method == "POST":
        c.execute(
            "INSERT INTO dettes(titre,montant,date,statut) VALUES(?,?,?,?)",
            (
                request.form["titre"],
                convertir(request.form["montant"], request.form.get("devise", "CDF")),
                datetime.now().strftime("%d/%m/%Y"),
                "non payé"
            )
        )
        conn.commit()

    c.execute("SELECT * FROM dettes ORDER BY id DESC")
    data = c.fetchall()

    conn.close()

    return render_template("dettes.html", data=data)


# =========================
# PROJETS AVANCÉS
# =========================
@app.route("/projets", methods=["GET","POST"])
def projets():
    if "user" not in session:
        return redirect("/")

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    if request.method == "POST":
        c.execute(
            "INSERT INTO projets(nom,budget,avance,statut) VALUES(?,?,?,?)",
            (request.form["nom"], convertir( request.form["budget"], request.form.get("devise", "CDF")),  0, "en cours")
        )
        conn.commit()

    c.execute("SELECT * FROM projets ORDER BY id DESC")

    data = c.fetchall()
    conn.close()

    return render_template("projets.html", data=data)


# =========================
# LOGOUT
# =========================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/supprimer_recette/<int:id>")
def supprimer_recette(id):

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute(
        "DELETE FROM recettes WHERE id=?",
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect("/recettes")

@app.route("/supprimer_depense/<int:id>")
def supprimer_depense(id):

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute(
        "DELETE FROM depenses WHERE id=?",
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect("/depenses")

@app.route("/supprimer_dette/<int:id>")
def supprimer_dette(id):

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute(
        "DELETE FROM dettes WHERE id=?",
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect("/dettes")
@app.route("/payer_dette/<int:id>")
def payer_dette(id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("UPDATE dettes SET statut='payé' WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect("/dettes")

@app.route("/supprimer_projet/<int:id>")
def supprimer_projet(id):

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute(
        "DELETE FROM projets WHERE id=?",
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect("/projets")

@app.route("/graphique")
def graphique():
    return render_template("graph.html")

# =========================
# RUN
# =========================
if __name__ == "__main__":
    init_db()

    app.run(host="0.0.0.0", port=5000, debug=True)