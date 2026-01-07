"""
Quick script to check what's saved in the database
"""
import sqlite3
import json

db_path = "layout_projects.db"
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=" * 60)
print("DATABASE CONTENTS")
print("=" * 60)

# Check projects
cursor.execute("SELECT * FROM projects")
projects = cursor.fetchall()
print(f"\n📁 PROJECTS ({len(projects)}):")
for p in projects:
    print(f"  - ID: {p['id']}, Name: {p['name']}")
    print(f"    PDF: {p['pdf_path']}")
    print(f"    Shapes: {p['shapes_path']}")
    print(f"    Modified: {p['last_modified']}")
    
    # Check variables for this project
    cursor.execute("SELECT * FROM variables WHERE project_id = ?", (p['id'],))
    variables = cursor.fetchall()
    print(f"    Variables: {len(variables)}")
    for v in variables:
        print(f"      - {v['name']}")
        cursor.execute("SELECT * FROM variable_rules WHERE variable_id = ?", (v['id'],))
        rules = cursor.fetchall()
        print(f"        Rules: {len(rules)}")
    
    # Check labels for this project
    cursor.execute("SELECT * FROM labels WHERE project_id = ?", (p['id'],))
    labels = cursor.fetchall()
    print(f"    Labels: {len(labels)}")
    for label in labels:
        cursor.execute("SELECT * FROM label_lines WHERE label_id = ?", (label['id'],))
        lines = cursor.fetchall()
        print(f"      - Shape {label['shape_index']}: {len(lines)} lines")
        for line in lines:
            print(f"        '{line['text']}'")

print("\n" + "=" * 60)

conn.close()
