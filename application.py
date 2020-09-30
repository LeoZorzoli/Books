
import os

from flask import Flask, session, render_template, request, redirect, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.security import check_password_hash, generate_password_hash

import requests

from helpers import login_required

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session 
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"), pool_size=10, max_overflow=20)
db = scoped_session(sessionmaker(bind=engine))

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if session:
        return redirect("/")
    else:
        session.clear()
        username = request.form.get("username")
        password = request.form.get("password")

        if request.method == "POST":

            rows = db.execute("SELECT * FROM users WHERE username = :username",
                            {"username":username})

            result = rows.fetchone()

            if result == None or not check_password_hash(result[2], request.form.get("password")):
                    return render_template("error.html", message="Wrong username or password")

            # Remember which user has logged in
            session["user_id"] = result[0]
            session["user_name"] = result[1]

            return redirect("/")
        else:
            return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to home
    return redirect("/")

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirm = request.form.get("confirm-password")

        userCheck = db.execute("SELECT * FROM users WHERE username = :username",
                            {"username":username}).fetchone()
        if userCheck:
                return render_template("error.html", message= "User taked")
        
        elif password != confirm:
                return render_template("error.html", message= "Password dont match")

        hashpassword = generate_password_hash(request.form.get("password"))

        db.execute("INSERT INTO users (username,hash) VALUES (:username, :password)",
                        {"username":username,
                        "password":hashpassword})

        db.commit()

        # Redirect to login page

        return redirect("/login")

    else:
        if session:
            return redirect("/")
        else:
            session.clear()
            return render_template("register.html")

@app.route("/search", methods=["GET","POST"])
@login_required
def search():
    if request.method == "GET":
        return render_template("search.html")
    else:
        data = request.form.get("book")
        if data == '':
            return render_template("error.html", message= "Insert the isbn, name, author or year of a Book")
        books = db.execute("SELECT * FROM books WHERE title ILIKE '%"+data+"%' or isbn ILIKE '%"+data+"%' or author ILIKE '%"+data+"%' or year ILIKE '%"+data+"%'").fetchall()
        if len(books) == 0:
            return render_template("error.html", message="No coincidence")
        return render_template("search.html", books = books, data = data)
        
@app.route("/search/<isbn>", methods=['GET', 'POST'])
@login_required
def book(isbn):

    if request.method == 'POST':
        currentUser = session["user_id"]
        rate = request.form.get("stars")
        text = request.form.get("textarea")

        row = db.execute("SELECT id FROM books WHERE isbn = :isbn",
            {"isbn": isbn})

        bookId = row.fetchone() 
        bookId = bookId[0]

        row2 = db.execute("SELECT * FROM reviews WHERE user_id = :user_id AND book_id = :book_id",
                    {"user_id": currentUser,
                     "book_id": bookId})

        # User already do a review
        if row2.rowcount == 1:
            
            return render_template("error.html", message = "You alredy submit a review to this book")

        rate = int(rate)

        db.execute("INSERT INTO reviews (user_id, book_id, review, rating) VALUES (:user_id, :book_id, :review, :rating)",
                    {"user_id": currentUser, 
                    "book_id": bookId, 
                    "review": text, 
                    "rating": rate})

        db.commit()

        return redirect ("/search/" + isbn)

    else:
        # Info goodreads
        res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "sM3fmQ5RNWvuEO83ippaA", "isbns": isbn})
        average_rating=res.json()['books'][0]['average_rating']
        work_ratings_count=res.json()['books'][0]['work_ratings_count']

        row = db.execute("SELECT id FROM books WHERE isbn = :isbn",
                        {"isbn": isbn})

        book = db.execute("SELECT isbn FROM books WHERE isbn = :isbn", {"isbn": isbn})

        book = row.fetchone() 
        book = book[0]

        results = db.execute("SELECT users.username, review, rating FROM users INNER JOIN reviews ON users.id = reviews.user_id WHERE book_id = :book",
                                                {"book": book})                                 
        reviews = results.fetchall()

        if book is None:
            return render_template("error.html", message="No such book.")
            
        data = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn":isbn})
        return render_template("book.html", data = data, book = book, average_rating=average_rating,work_ratings_count=work_ratings_count, reviews = reviews)

@app.route("/api/<isbn>", methods=['GET'])
@login_required
def api(isbn):
    
    row = db.execute("SELECT title, author, year, isbn, \
                    COUNT(reviews.id) as review_count, \
                    AVG(reviews.rating) as average_score \
                    FROM books \
                    INNER JOIN reviews \
                    ON books.id = reviews.book_id \
                    WHERE isbn = :isbn \
                    GROUP BY title, author, year, isbn",
                    {"isbn": isbn})

    # Check for error
    if row.rowcount != 1:
        return render_template("error.html", message="This book dont have reviews")
  
    tmp = row.fetchone()

    # Convert to dictionary
    result = dict(tmp.items())

    result['average_score'] = float('%.2f'%(result['average_score']))

    return jsonify(result)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', message="Page not found!"), 404