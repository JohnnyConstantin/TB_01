import os
import sqlite3

path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../db/orders.db')
conn = sqlite3.connect(path, check_same_thread = False)

class Database():

# TODO: not complated

    # create a database connection to the sqlite database
    def connection(db_file):
        conn = None
        try:
            conn = sqlite3.connect(db_file)
        except Error as e:
            print(e)
        return conn

    # Save order; data = orderid,symbol,amount,price,side,quantity,profit
    @staticmethod
    def write(data):
        cur = conn.cursor()
        cur.execute('''INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?)''', data)
        conn.commit()

    # query order by id
    @staticmethod
    def read(orderid):
        cur = conn.cursor()
        cur.execute('SELECT * FROM orders WHERE orderid = ?', (orderid,))
        return cur.fetchone()

    # delete order by id
    @staticmethod
    def delete(orderid):
        cur = conn.cursor()
        cur.execute('DELETE FROM orders WHERE orderid = ?', (orderid,))
        conn.commit()
