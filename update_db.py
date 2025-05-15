import sqlite3

def update_database():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    
    # Aggiungi la colonna position
    try:
        c.execute("ALTER TABLE links ADD COLUMN position INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        print("Column 'position' might already exist")

    # Aggiorna le posizioni esistenti in base all'ID
    c.execute("UPDATE links SET position = id WHERE position = 0")
    
    conn.commit()
    conn.close()
    print("Database updated successfully!")

if __name__ == "__main__":
    update_database()
