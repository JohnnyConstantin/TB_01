import os
import sqlite3

#path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../db/orders.db')
path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../db/coins.db')
conn = sqlite3.connect(path, check_same_thread=False)

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
        cur.execute('INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?)', data)
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

    # save symbol in table
    @staticmethod
    def write_symbol(table, data):
        cur = conn.cursor()
        cur.execute('INSERT INTO "' + table + '" VALUES (?, ?, ?)', data)
        conn.commit()

    # query symbol from table
    @staticmethod
    def read_symbol(table, symbol):
        cur = conn.cursor()
        cur.execute('SELECT * FROM "' + table + '" WHERE symbol = ?', (symbol,))
        return cur.fetchone()

    # query all rows from table
    @staticmethod
    def read_table(table):
        cur = conn.cursor()
        cur.execute('SELECT * FROM "' + table + '"')
        return cur
#        return cur.fetchone()

    # delete all rows in table
    @staticmethod
    def clear_table(table):
        cur = conn.cursor()
        cur.execute('DELETE FROM "' + table + '"')
#        conn.commit()

    # check if table is empty
    @staticmethod
    def empty_table(table):
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) from "' + table + '"')
        res = cur.fetchall()
        if res[0][0] == 0:
            return None
        return res
