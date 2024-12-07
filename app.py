import os
from flask import Flask, render_template, request, url_for, redirect
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

from sqlalchemy.sql import func


basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] =\
        'sqlite:///' + os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

with app.app_context():
    with db.engine.connect() as conn:
        result = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_publicationYear';"
        )).fetchone()
        if not result:
            conn.execute(text("CREATE INDEX idx_publicationYear ON Book(publicationYear)"))

        result = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_created_at';"
        )).fetchone()
        if not result:
            conn.execute(text("CREATE INDEX idx_created_at ON Book(created_at)"))


book_author = db.Table('book_author',
    db.Column('book_id', db.Integer, db.ForeignKey('book.id'), primary_key=True),
    db.Column('author_id', db.Integer, db.ForeignKey('author.id'), primary_key=True)
)
    
class Author(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    authorName = db.Column(db.String(200), nullable=False)
    def __repr__(self):
        return f'<Author "{self.authorName}">'


class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booktitle = db.Column(db.String(200), nullable=False)
    author = db.relationship('Author', secondary=book_author, lazy='subquery',
                               backref=db.backref('books', lazy=True))
    publicationYear = db.Column(db.Integer)
    created_at = db.Column(db.DateTime(timezone=True),
                        server_default=func.now())
    genre = db.Column(db.String(100))
    description = db.Column(db.Text)
    def __repr__(self):
        return f'<Book {self.booktitle}>'
    

@app.route('/')
def index():
    books = Book.query.all()
    return render_template('index.html', books=books)


@app.route('/create/', methods=('GET', 'POST'))
def create():
    if request.method == 'POST':
        booktitle = request.form['booktitle']
        authorName = request.form['authorName']
        genre = request.form['genre']
        publicationYear = int(request.form['publicationYear'])
        description = request.form['description']

        nAuthor = Author(authorName=authorName)
        
        db.session.add(nAuthor)
        db.session.commit()
        book = Book(booktitle=booktitle,
                          author=[nAuthor],
                          genre=genre,
                          publicationYear=publicationYear,
                          description=description)
        db.session.add(book)
        db.session.commit()

        return redirect(url_for('index'))

    return render_template('create.html')

@app.route('/delete/<int:book_id>', methods=['GET', 'POST'])
def delete_book(book_id):
    if request.method == 'POST':
        book_to_delete = Book.query.get_or_404(book_id)
        db.session.delete(book_to_delete)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/edit/<int:book_id>', methods=['GET', 'POST'])
def edit_book(book_id):
    book_to_edit = Book.query.get_or_404(book_id)
    
    if request.method == 'POST':
        book_to_edit.booktitle = request.form['booktitle']
        
   
        authors_input = request.form['author']
        authors_list = [author.strip() for author in authors_input.split(',') if author.strip()]
        
  
        book_to_edit.author.clear()
        

        for author_name in authors_list:
            # Find existing author or create a new one
            existing_author = Author.query.filter_by(authorName=author_name).first()
            if existing_author:
                book_to_edit.author.append(existing_author)
            else:
                new_author = Author(authorName=author_name)
                db.session.add(new_author)
                book_to_edit.author.append(new_author)
        
        book_to_edit.publicationYear = request.form['publicationYear']
        book_to_edit.genre = request.form['genre']
        book_to_edit.description = request.form['description']
        
        db.session.commit()
        return redirect(url_for('index'))

    return render_template('edit.html', book=book_to_edit)

@app.route('/report')
def get_book_report():

    stmt = text("SELECT COUNT(*) FROM Book")
    result = db.session.execute(stmt).fetchone()
    total_books = result[0]


    stmt_year = text("""
        WITH YearCounts AS (
            SELECT publicationYear, COUNT(*) AS books_count
            FROM Book
            GROUP BY publicationYear
        )
        SELECT publicationYear, books_count
        FROM YearCounts
        WHERE books_count = (SELECT MAX(books_count) FROM YearCounts)
    """)
    years_with_most_books = db.session.execute(stmt_year).fetchall()


    stmt_first = text("SELECT * FROM Book ORDER BY created_at ASC LIMIT 1")
    first_book = db.session.execute(stmt_first).fetchone()

    stmt_recent = text("SELECT * FROM Book ORDER BY created_at DESC LIMIT 1")
    most_recent_book = db.session.execute(stmt_recent).fetchone()

    return render_template('report.html', total_books=total_books,
                           years_with_most_books=years_with_most_books,
                           first_book=first_book, most_recent_book=most_recent_book)


@app.post('/<int:book_id>/delete/')
def delete(book_id):
    book = Book.query.get_or_404(book_id)
    db.session.delete(book)
    db.session.commit()
    return redirect(url_for('index'))