"""Add fictional demo records to an empty local database."""
import sqlite3
from pathlib import Path
ROOT=Path(__file__).resolve().parent; DB=ROOT/'instance'/'veriestate.db'
SAMPLES=[
("Demo Listing A — Sunrise Residency","Flat 302, Sunrise Residency, Lake View Road","Gotri","Vadodara","Gujarat","Apartment",980,"DEMO-101","Fictional 2-bedroom apartment in Sunrise Residency, Gotri."),
("Demo Listing B — Sunrise Residency variant","Flat 302 Sunrise Residency, Lake View Rd.","Gotri","Vadodara","Gujarat","Apartment",1000,"","Fictional 2 bedroom flat at Sunrise Residency in Gotri area."),
("Demo Listing C — Green Park Plot","Plot 18, Green Park Road","Sevasi","Vadodara","Gujarat","Plot",1500,"DEMO-203","Fictional residential plot in Sevasi, Vadodara."),
("Demo Listing D — Riverfront Apartment","Apartment B-204, Riverfront Homes","Alkapuri","Vadodara","Gujarat","Apartment",1250,"DEMO-304","Fictional apartment listing for demonstration."),
("Demo Listing E — Palm Court Villa","Villa 12, Palm Court, Palm Road","Vesu","Surat","Gujarat","Villa",2400,"DEMO-405","Fictional villa listing for demonstration.")]
def main():
 DB.parent.mkdir(exist_ok=True); con=sqlite3.connect(DB)
 con.execute("""CREATE TABLE IF NOT EXISTS listings (id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,address TEXT NOT NULL,locality TEXT NOT NULL,city TEXT NOT NULL,state TEXT DEFAULT '',property_type TEXT NOT NULL,area_sqft REAL,property_id TEXT DEFAULT '',description TEXT DEFAULT '',created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
 if con.execute('SELECT COUNT(*) FROM listings').fetchone()[0]: print('Listings already exist; no samples inserted.'); con.close(); return
 con.executemany("INSERT INTO listings(title,address,locality,city,state,property_type,area_sqft,property_id,description) VALUES (?,?,?,?,?,?,?,?,?)",SAMPLES); con.commit(); con.close(); print('Inserted five FICTIONAL demo listings (not real properties).')
if __name__=='__main__': main()

