from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_bcrypt import Bcrypt
from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId
from datetime import timedelta

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a more secure secret key in production
bcrypt = Bcrypt(app)

# MongoDB Connection
client = MongoClient("mongodb://localhost:27017/")
db = client["library_db"]
users_collection = db["users"]
books_collection = db["books"]
borrowed_books_collection = db["borrowed_books"]

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
        is_admin = username.lower() == "admin"

        if users_collection.find_one({"username": username}):
            flash("Username already exists!", "danger")
            return redirect(url_for('signup'))

        users_collection.insert_one({"username": username, "password": password, "is_admin": is_admin})
        flash("Signup successful! Please login.", "success")
        return redirect(url_for('login'))
    
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = users_collection.find_one({"username": username})

        if user and bcrypt.check_password_hash(user['password'], password):
            session['user'] = username
            session['is_admin'] = user.get("is_admin", False)
            flash("Login successful!", "success")
            return redirect(url_for('dashboard'))

        flash("Invalid username or password", "danger")
    return render_template('login.html')
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))

    category = request.args.get('category', 'All')
    query = request.args.get('query', '').strip()
    search_by = request.args.get('search_by', 'title')

    filter_query = {} if category == 'All' else {"category": category}
    if query:
        filter_query[search_by] = {"$regex": query, "$options": "i"}

    books = list(books_collection.find(filter_query))

    borrowed_isbns = borrowed_books_collection.distinct("isbn")
    available_books_count = books_collection.count_documents({"isbn": {"$nin": borrowed_isbns}})
    borrowed_books_count = len(borrowed_isbns)

    if session.get('is_admin'):
        borrowed_books = list(borrowed_books_collection.find())
        count = None
    else:
        borrowed_books = list(borrowed_books_collection.find({"borrowed_by": session['user']}))
        count = len(borrowed_books)

    from datetime import datetime
    for book in borrowed_books:
        book['is_overdue'] = book.get('return_date') and book['return_date'] < datetime.now()

    categories = books_collection.distinct("category")

    return render_template('dashboard.html',
                           books=books,
                           borrowed_books=borrowed_books,
                           username=session['user'],
                           is_admin=session.get('is_admin', False),
                           categories=categories,
                           selected_category=category,
                           query=query,
                           search_by=search_by,
                           count=count,
                           available_books_count=available_books_count,
                           borrowed_books_count=borrowed_books_count)




@app.route('/add_book', methods=['POST'])
def add_book():
    if 'user' not in session or not session.get('is_admin', False):
        flash("You must be an admin to add books.", "danger")
        return redirect(url_for('dashboard'))
    
    book_data = {
        "title": request.form['title'],
        "author": request.form['author'],
        "isbn": request.form['isbn'],
        "category": request.form.get('category', 'General')
    }
    books_collection.insert_one(book_data)
    flash("Book added successfully!", "success")
    return redirect(url_for('dashboard'))

@app.route('/delete_book/<string:isbn>')
def delete_book(isbn):
    if 'user' not in session or not session.get('is_admin', False):
        flash("You must be an admin to delete books.", "danger")
        return redirect(url_for('dashboard'))
    
    books_collection.delete_one({"isbn": isbn})
    flash("Book deleted successfully!", "success")
    return redirect(url_for('dashboard'))



@app.route('/borrow/<string:isbn>')
def borrow_book(isbn):
    if 'user' not in session:
        return redirect(url_for('login'))

    user = session['user']

    # Step 1: Check if user already borrowed 5 books
    current_borrowed = borrowed_books_collection.count_documents({'borrowed_by': user})
    if current_borrowed >= 5:
        flash("You can't borrow more than 5 books at a time (limit is 5 books for 10 days).", "danger")
        return redirect(url_for('dashboard'))

    # Step 2: Find the book in available books
    book = books_collection.find_one({"isbn": isbn})
    if not book:
        flash("This book is no longer available to borrow.", "danger")
        return redirect(url_for('dashboard'))

    # Step 3: Set return deadline (10 days from today)
    return_date = datetime.now() + timedelta(days=10)

    # Step 4: Move book to borrowed collection
    borrowed_books_collection.insert_one({
        "title": book["title"],
        "author": book["author"],
        "isbn": book["isbn"],
        "category": book.get("category", "General"),
        "borrowed_by": user,
        "borrowed_at": datetime.now(),
        "return_date": return_date
    })

    # Step 5: Remove book from available books
    books_collection.delete_one({"isbn": isbn})

    flash("Book borrowed successfully! Return within 10 days.", "success")
    return redirect(url_for('dashboard'))


@app.route('/return/<string:isbn>')
def return_book(isbn):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    book = borrowed_books_collection.find_one({"isbn": isbn, "borrowed_by": session['user']})
    if book:
        books_collection.insert_one({
            "title": book["title"],
            "author": book["author"],
            "isbn": book["isbn"],
            "category": book.get("category", "General")
        })
        borrowed_books_collection.delete_one({"isbn": isbn, "borrowed_by": session['user']})
        flash("Book returned successfully!", "success")
    else:
        flash("You cannot return this book!", "danger")
    return redirect(url_for('dashboard'))

@app.route('/book/<isbn>')
def book_details(isbn):
    # Your logic here
    return render_template('book_details.html', book_isbn=isbn)

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully!", "info")
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)