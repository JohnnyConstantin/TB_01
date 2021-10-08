import os
import sqlite3

#path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../db/orders.db')
path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../db/coins.db')
conn = sqlite3.connect(path, check_same_thread=False)


class Database:

# TODO: not complated

    # create a database connection to the sqlite database
    def connection(db_file):
        con = None
        try:
            con = sqlite3.connect(db_file)
        except Error as e:
            print(e)
        return con

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

    @staticmethod  # write symbol into table
    def write_symbol(table, data):
        data = data if type(data) == list else tuple(data)
        cur = conn.cursor()
        cur.execute('INSERT INTO "' + table + '" VALUES (?, ?, ?, ?)', data)
        # print('ADD: ' + str(data[0]))
        conn.commit()

    @staticmethod  # delete symbol from table
    def delete_symbol(table, symbol):
        cur = conn.cursor()
        cur.execute('DELETE FROM "' + table + '" WHERE symbol = ?', (symbol,))
        # print('DEL: ' + str(symbol))
        conn.commit()

    @staticmethod  # read symbol from table
    def read_symbol(table, symbol):
        cur = conn.cursor()
        cur.execute('SELECT * FROM "' + table + '" WHERE symbol = ?', (symbol,))
        return cur.fetchone()

    # query all rows from table
    @staticmethod
    def read_table(table):
        data = []  # list of dicts by column
        cur = conn.cursor()
        cur.execute('SELECT * FROM "' + table + '"')
        cols = tuple([d[0] for d in cur.description])
        for row in cur: data.append(dict(zip(cols, row)))
        return data

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
