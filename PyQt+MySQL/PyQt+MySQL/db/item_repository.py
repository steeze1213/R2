from db.connection import get_connection

class ItemRepository:

    def fetch_all(self):
        sql = "SELECT id, code, name, price, stock FROM items ORDER BY id"
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                return cur.fetchall()

    def insert(self, code, name, price, stock):
        sql = "INSERT INTO items (code, name, price, stock) VALUES (%s, %s, %s, %s)"
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (code, name, price, stock))
                conn.commit()
            return True
        except:
            return False

    def update(self, item_id, code, name, price, stock):
        sql = """
        UPDATE items
        SET code=%s, name=%s, price=%s, stock=%s
        WHERE id=%s
        """
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (code, name, price, stock, item_id))
                conn.commit()
            return True
        except:
            return False

    def delete(self, item_id):
        sql = "DELETE FROM items WHERE id=%s"
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (item_id,))
            conn.commit()

    def exists_code(self, code):
        sql = "SELECT COUNT(*) FROM items WHERE code=%s"
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (code,))
                count, = cur.fetchone()
                return count > 0