"""
Database module for Layout Heatmap project management
Handles all SQLite database operations for projects, labels, and variables
"""

import sqlite3
import json
import sys
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import os


class Database:
    def __init__(self, db_path: str = None):
        """Initialize database connection"""
        # If no path provided, save database in appropriate location
        if db_path is None:
            # Check if running as a PyInstaller executable
            if getattr(sys, 'frozen', False):
                # Running as executable - save database in same folder as .exe
                application_path = os.path.dirname(sys.executable)
            else:
                # Running as script - save in project root (parent of src/)
                script_dir = os.path.dirname(os.path.abspath(__file__))
                application_path = os.path.dirname(script_dir)
            
            # Save database in application directory
            db_path = os.path.join(application_path, "layout_projects.db")
        
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self.connect()
        self.create_tables()
    
    def connect(self):
        """Connect to SQLite database"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        self.cursor = self.conn.cursor()
    
    def create_tables(self):
        """Create all necessary tables if they don't exist"""
        # Projects table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                pdf_path TEXT,
                shapes_path TEXT,
                created_date TEXT NOT NULL,
                last_modified TEXT NOT NULL
            )
        ''')
        
        # Variables table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS variables (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                text_color TEXT,
                bg_color TEXT,
                text_size INTEGER,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
        ''')
        
        # Migrate existing variables table if needed
        self.cursor.execute("PRAGMA table_info(variables)")
        columns = [col[1] for col in self.cursor.fetchall()]
        
        if 'text_color' not in columns:
            self.cursor.execute("ALTER TABLE variables ADD COLUMN text_color TEXT")
        if 'bg_color' not in columns:
            self.cursor.execute("ALTER TABLE variables ADD COLUMN bg_color TEXT")
        if 'text_size' not in columns:
            self.cursor.execute("ALTER TABLE variables ADD COLUMN text_size INTEGER")
        
        # Variable rules table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS variable_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                variable_id INTEGER NOT NULL,
                operator TEXT NOT NULL,
                threshold REAL NOT NULL,
                color TEXT NOT NULL,
                rule_order INTEGER NOT NULL,
                FOREIGN KEY (variable_id) REFERENCES variables(id) ON DELETE CASCADE
            )
        ''')
        
        # Labels table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS labels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                shape_index INTEGER NOT NULL,
                position_x REAL NOT NULL,
                position_y REAL NOT NULL,
                has_leader INTEGER NOT NULL,
                leader_points TEXT,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
        ''')
        
        # Label lines table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS label_lines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                label_id INTEGER NOT NULL,
                line_index INTEGER NOT NULL,
                text TEXT,
                font_size INTEGER NOT NULL,
                font_color TEXT NOT NULL,
                bg_color TEXT NOT NULL,
                variable_name TEXT,
                FOREIGN KEY (label_id) REFERENCES labels(id) ON DELETE CASCADE
            )
        ''')
        
        # Migrate label_lines table to add new columns if needed
        self.cursor.execute("PRAGMA table_info(label_lines)")
        label_line_columns = [col[1] for col in self.cursor.fetchall()]
        
        if 'is_sales' not in label_line_columns:
            self.cursor.execute("ALTER TABLE label_lines ADD COLUMN is_sales INTEGER DEFAULT 0")
        if 'unit_metric' not in label_line_columns:
            self.cursor.execute("ALTER TABLE label_lines ADD COLUMN unit_metric TEXT DEFAULT 'None'")
        
        self.conn.commit()
    
    # ===== PROJECT OPERATIONS =====
    
    def create_project(self, name: str, pdf_path: str = "", shapes_path: str = "") -> int:
        """Create a new project and return its ID"""
        now = datetime.now().isoformat()
        self.cursor.execute('''
            INSERT INTO projects (name, pdf_path, shapes_path, created_date, last_modified)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, pdf_path, shapes_path, now, now))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_all_projects(self) -> List[Dict]:
        """Get all projects"""
        self.cursor.execute('SELECT * FROM projects ORDER BY last_modified DESC')
        return [dict(row) for row in self.cursor.fetchall()]
    
    def get_project(self, project_id: int) -> Optional[Dict]:
        """Get a specific project by ID"""
        self.cursor.execute('SELECT * FROM projects WHERE id = ?', (project_id,))
        row = self.cursor.fetchone()
        return dict(row) if row else None
    
    def update_project(self, project_id: int, pdf_path: str = None, shapes_path: str = None):
        """Update project paths"""
        now = datetime.now().isoformat()
        if pdf_path is not None:
            self.cursor.execute('UPDATE projects SET pdf_path = ?, last_modified = ? WHERE id = ?',
                              (pdf_path, now, project_id))
        if shapes_path is not None:
            self.cursor.execute('UPDATE projects SET shapes_path = ?, last_modified = ? WHERE id = ?',
                              (shapes_path, now, project_id))
        self.conn.commit()
    
    def delete_project(self, project_id: int):
        """Delete a project and all associated data"""
        self.cursor.execute('DELETE FROM projects WHERE id = ?', (project_id,))
        self.conn.commit()
    
    def rename_project(self, project_id: int, new_name: str):
        """Rename a project"""
        now = datetime.now().isoformat()
        self.cursor.execute(
            'UPDATE projects SET name = ?, last_modified = ? WHERE id = ?',
            (new_name, now, project_id)
        )
        self.conn.commit()
    
    def touch_project(self, project_id: int):
        """Update last_modified timestamp"""
        now = datetime.now().isoformat()
        self.cursor.execute('UPDATE projects SET last_modified = ? WHERE id = ?', (now, project_id))
        self.conn.commit()
    
    # ===== VARIABLE OPERATIONS =====
    
    def save_variables(self, project_id: int, variables: List):
        """Save all variables and their rules for a project"""
        # Delete existing variables for this project
        self.cursor.execute('DELETE FROM variables WHERE project_id = ?', (project_id,))
        
        # Insert new variables
        for var in variables:
            self.cursor.execute('''
                INSERT INTO variables (project_id, name, text_color, bg_color, text_size)
                VALUES (?, ?, ?, ?, ?)
            ''', (project_id, var.name, var.text_color, var.bg_color, var.text_size))
            variable_id = self.cursor.lastrowid
            
            # Insert rules for this variable
            for idx, rule in enumerate(var.rules):
                self.cursor.execute('''
                    INSERT INTO variable_rules (variable_id, operator, threshold, color, rule_order)
                    VALUES (?, ?, ?, ?, ?)
                ''', (variable_id, rule.operator, rule.threshold, rule.color, idx))
        
        self.conn.commit()
        self.touch_project(project_id)
    
    def load_variables(self, project_id: int) -> List[Dict]:
        """Load all variables and their rules for a project"""
        self.cursor.execute('SELECT * FROM variables WHERE project_id = ?', (project_id,))
        variables = []
        
        for var_row in self.cursor.fetchall():
            var_dict = dict(var_row)
            
            # Get rules for this variable
            self.cursor.execute('''
                SELECT * FROM variable_rules 
                WHERE variable_id = ? 
                ORDER BY rule_order
            ''', (var_dict['id'],))
            
            var_dict['rules'] = [dict(rule_row) for rule_row in self.cursor.fetchall()]
            variables.append(var_dict)
        
        return variables
    
    # ===== LABEL OPERATIONS =====
    
    def save_labels(self, project_id: int, labels: List):
        """Save all labels for a project"""
        # Delete existing labels for this project
        self.cursor.execute('DELETE FROM labels WHERE project_id = ?', (project_id,))
        
        # Insert new labels
        for label in labels:
            # Serialize leader_points to JSON
            leader_points_json = json.dumps(label.leader_points) if label.leader_points else None
            
            self.cursor.execute('''
                INSERT INTO labels (project_id, shape_index, position_x, position_y, 
                                   has_leader, leader_points)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (project_id, label.shape_index, label.position[0], label.position[1],
                  1 if label.has_leader else 0, leader_points_json))
            
            label_id = self.cursor.lastrowid
            
            # Insert label lines
            for idx, text in enumerate(label.text_lines):
                font_size = label.line_font_sizes[idx] if idx < len(label.line_font_sizes) else 12
                font_color = label.line_font_colors[idx] if idx < len(label.line_font_colors) else "#000000"
                bg_color = label.line_bg_colors[idx] if idx < len(label.line_bg_colors) else "#FFFFFF"
                variable_name = label.line_variables[idx] if idx < len(label.line_variables) else "None"
                is_sales = label.line_is_sales[idx] if idx < len(label.line_is_sales) else False
                unit_metric = label.line_unit_metric[idx] if idx < len(label.line_unit_metric) else "None"
                
                self.cursor.execute('''
                    INSERT INTO label_lines (label_id, line_index, text, font_size, 
                                            font_color, bg_color, variable_name, is_sales, unit_metric)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (label_id, idx, text, font_size, font_color, bg_color, variable_name, 
                      1 if is_sales else 0, unit_metric))
        
        self.conn.commit()
        self.touch_project(project_id)
    
    def load_labels(self, project_id: int) -> List[Dict]:
        """Load all labels for a project"""
        self.cursor.execute('SELECT * FROM labels WHERE project_id = ?', (project_id,))
        labels = []
        
        for label_row in self.cursor.fetchall():
            label_dict = dict(label_row)
            
            # Deserialize leader_points
            if label_dict['leader_points']:
                label_dict['leader_points'] = json.loads(label_dict['leader_points'])
            else:
                label_dict['leader_points'] = []
            
            # Get label lines
            self.cursor.execute('''
                SELECT * FROM label_lines 
                WHERE label_id = ? 
                ORDER BY line_index
            ''', (label_dict['id'],))
            
            label_dict['lines'] = [dict(line_row) for line_row in self.cursor.fetchall()]
            labels.append(label_dict)
        
        return labels
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
