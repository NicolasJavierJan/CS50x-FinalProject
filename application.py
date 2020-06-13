import os
import random

from flask import Flask
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from cs50 import SQL
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps

# Login Function
def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///project.db")


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return render_template("index.html")
    else:
        article = request.form.get("article")
        return redirect("/article/"+article)


@app.route("/articles", methods=["GET", "POST"])
def articles():
    if request.method == "GET":
        return render_template("articles.html")
    else:
        article = request.form.get("article")
        return redirect("/article/"+article)


@app.route("/article/<n>", methods=["GET", "POST"])
def articlenumber(n):
    if request.method == "GET":
        return render_template("article.html", n=n)
    else:
        return render_template("article.html")


@app.route("/games", methods=["GET", "POST"])
def games():
    if request.method == "GET":
        console = db.execute("SELECT DISTINCT console FROM games ORDER BY console")
        year = db.execute("SELECT DISTINCT year FROM games ORDER BY year")
        return render_template("games.html", console=console, year=year)

    else:
        console = db.execute("SELECT DISTINCT console FROM games ORDER BY console")
        year = db.execute("SELECT DISTINCT year FROM games ORDER BY year")
        search1 = request.form.get("console")
        search2 = request.form.get("year")
        if search1 == None:
            if search2 == None:
                rows = db.execute("SELECT * FROM games ORDER BY year")
                return render_template("games.html", rows=rows, year=year, console=console)
            else:
                rows = db.execute("SELECT * FROM games WHERE year = :year", year=search2)
                return render_template("games.html", rows=rows, year=year, console=console)
        else:
            if search2 == None:
                rows = db.execute("SELECT * FROM games WHERE console = :console", console=search1)
                return render_template("games.html", rows=rows, year=year, console=console)
            else:
                rows = db.execute("SELECT * FROM games WHERE console = :console AND year = :year", console=search1, year=search2)
                return render_template("games.html", rows=rows, year=year, console=console)


@app.route("/game/<number>")
def game(number):
    game = db.execute("SELECT * FROM games")
    votes = db.execute("SELECT game, id FROM games JOIN compare ON id = secondid WHERE firstid = :number AND votes > 0 ORDER BY votes DESC LIMIT 3", number=number)
    name = None
    entries = 0
    for row in game:
        entries += 1
        if int(number) == int(row['id']):
            name = row['game']
            gameinfo = db.execute("SELECT * FROM review WHERE id = :number", number=number)
            return render_template("game.html", name=name, subtitle=gameinfo[0]['subtitle'], review=gameinfo[0]['review'],
                                    number=gameinfo[0]['id'], votes=votes)
    if int(number) > entries:
        error = "Game Not Found"
        return render_template("error.html", error=error)


@app.route("/compare", methods=['GET'])
@login_required
def compare():
    if request.method == 'GET':
        number = db.execute("SELECT id FROM games")
        entries = 0
        for row in number:
            entries += 1
        ran1 = random.randint(1, entries)
        ran2 = random.randint(1, entries)
        game1 = db.execute("SELECT * FROM games WHERE id = :random", random=ran1)
        game2 = db.execute("SELECT * FROM games WHERE id = :random", random=ran2)
        if game1[0]['game'] == game2[0]['game']:
            ran2 = random.randint(1, entries)
            game2 = db.execute("SELECT * FROM games WHERE id = :random", random=ran2)
        return redirect("/compare/"+str(ran1)+"/with/"+str(ran2))


@app.route("/compare/<a>/with/<b>", methods=['GET', 'POST'])
@login_required
def comparewith(a,b):
    if request.method == 'GET':
        game1 = db.execute("SELECT * FROM games WHERE id = :random", random=a)
        game2 = db.execute("SELECT * FROM games WHERE id = :random", random=b)
        return render_template("compare.html", number1=a, number2=b, title=game1[0]['game'], year=game1[0]['year'], console=game1[0]['console'],
                                title2=game2[0]['game'], year2=game2[0]['year'], console2=game2[0]['console'], a=a, b=b)
    else:
        choice = request.form.get("choice")
        if int(choice) == 1:
            vote1 = db.execute("SELECT votes FROM compare WHERE firstid = :gameid AND secondid = :game2id", gameid=a, game2id=b)
            if not vote1:
                db.execute("INSERT INTO compare (firstid, secondid, votes) VALUES (:gameid, :game2id, 1)", gameid=a, game2id=b)
                db.execute("INSERT INTO compare (firstid, secondid, votes) values (:game2id, :gameid, 1)", game2id=b, gameid=a)
                return redirect("/compare")
            else:
                db.execute("UPDATE compare SET votes = votes + 1 WHERE firstid = :gameid AND secondid = :game2id", gameid=a, game2id=b)
                db.execute("UPDATE compare SET votes = votes + 1 WHERE firstid = :game2id AND secondid = :gameid", game2id=b, gameid=a)
                return redirect("/compare")
        else:
            vote2 = db.execute("SELECT * FROM compare WHERE firstid = :gameid AND secondid = :game2id", gameid=a, game2id=b)
            if not vote2:
                db.execute("INSERT INTO compare (firstid, secondid, votes) VALUES (:gameid, :game2id, -1)", gameid=a, game2id=b)
                db.execute("INSERT INTO compare (firstid, secondid, votes) values (:game2id, :gameid, -1)", game2id=b, gameid=a)
                return redirect("/compare")
            else:
                db.execute("UPDATE compare SET votes = votes - 1 WHERE firstid = :gameid AND secondid = :game2id", gameid=a, game2id=b)
                db.execute("UPDATE compare SET votes = votes - 1 WHERE firstid = :game2id AND secondid = :gameid", game2id=b, gameid=a)
                return redirect("/compare")


@app.route("/profile", methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'GET':
        userid = session['user_id']
        info = db.execute("SELECT * FROM profile WHERE id = :userid", userid=userid)
        game = db.execute("SELECT DISTINCT game FROM games")
        favourite = 0
        if info[0]['favourite'] != "Not yet defined":
            new = db.execute("SELECT id FROM games WHERE game = :game", game=info[0]['favourite'])
            favourite = int(new[0]['id'])
        return render_template("profile.html", username=info[0]['username'], favourite=info[0]['favourite'], game=game, number=favourite)
    else:
        game = db.execute("SELECT DISTINCT game FROM games")
        name = request.form.get("game")
        userid = session['user_id']
        db.execute("UPDATE profile SET favourite = :favourite WHERE id = :userid", favourite=name, userid=userid)
        info = db.execute("SELECT * FROM profile WHERE id = :userid", userid=userid)
        favourite = db.execute("SELECT id FROM games WHERE game = :game", game=name)
        return render_template("profile.html", username=info[0]['username'], favourite=info[0]['favourite'], game=game, number=favourite[0]['id'])


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    else:
        username = request.form.get("username")
        user = db.execute("SELECT * FROM users WHERE username = :username", username=username)
        if len(user) > 0:
            error = "Username taken"
            return render_template("error.html", error=error)
        else:
            password = request.form.get("password")
            confirmation = request.form.get("confirmation")
            if confirmation != password:
                error = "Password and confirmation must be the same!"
                return render_template("error.html", error=error)
            else:
                encryptedpass = generate_password_hash(password)
                db.execute("INSERT INTO users (username, hash) VALUES (:username, :password)", username=username, password=encryptedpass)
                db.execute("INSERT INTO profile (username, since, favourite) VALUES (:username, datetime('now'), 'Not yet defined')", username=username)
                return redirect("/")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            error = "Invalid User or Password"
            return render_template("error.html", error=error)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

