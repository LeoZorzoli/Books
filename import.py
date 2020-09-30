import os, csv

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker


engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

def main():
    db.execute("CREATE TABLE books (isbn VARCHAR PRIMARY KEY,title VARCHAR NOT NULL,author VARCHAR NOT NULL,year VARCHAR NOT NULL)")
    db.execute("CREATE TABLE reviews (id INTEGER NOT NULL, user_id INTEGER NOT NULL, book_id INTEGER NOT NULL, review VARCHAR NOT NULL,  rating INTEGER NOT NULL)")
    f=open("books.csv")
    reader =csv.reader(f)
    for isbn,title,author,year in reader:
        if year == "year":
            print('working')
        else:    
            db.execute("INSERT INTO books (isbn, title, author, year) VALUES (:isbn,:title,:author,:year)",{"isbn":isbn,"title":title,"author":author,"year":year})

    print("done")            
    db.commit()    

if __name__=="__main__":
    main()