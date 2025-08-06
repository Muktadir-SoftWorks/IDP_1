#!/usr/bin/env python3
import sqlite3
import json
import os
import uuid
import hashlib
import base64
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote
import io
import mimetypes
from datetime import datetime, timedelta
import secrets

class PetAdoptionHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.sessions = {}
        super().__init__(*args, **kwargs)

    def parse_multipart(self, data, boundary):
        """Parse multipart form data manually"""
        parts = data.split(('--' + boundary).encode())
        form_data = {}
        files = {}
        
        for part in parts[1:-1]:  # Skip first empty part and last closing part
            if not part.strip():
                continue
                
            # Split headers and content
            header_end = part.find(b'\r\n\r\n')
            if header_end == -1:
                continue
                
            headers = part[:header_end].decode('utf-8')
            content = part[header_end + 4:]
            
            # Remove trailing \r\n
            if content.endswith(b'\r\n'):
                content = content[:-2]
            
            # Parse Content-Disposition header
            name = None
            filename = None
            for line in headers.split('\r\n'):
                if line.startswith('Content-Disposition:'):
                    parts = line.split(';')
                    for p in parts:
                        p = p.strip()
                        if p.startswith('name="'):
                            name = p[6:-1]
                        elif p.startswith('filename="'):
                            filename = p[10:-1]
            
            if name:
                if filename:
                    # It's a file
                    files[name] = {
                        'filename': filename,
                        'content': content
                    }
                else:
                    # It's a regular form field
                    form_data[name] = content.decode('utf-8')
        
        return form_data, files
    def do_GET(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query = parse_qs(parsed_path.query)
        
        if path == '/' or path == '/index.html':
            self.serve_file('index.html')
        elif path == '/login.html':
            self.serve_file('login.html')
        elif path == '/signup.html':
            self.serve_file('signup.html')
        elif path == '/dashboard.html':
            if self.check_auth():
                self.serve_file('dashboard.html')
            else:
                self.redirect('/login.html')
        elif path == '/style.css':
            self.serve_file('style.css', 'text/css')
        elif path == '/script.js':
            self.serve_file('script.js', 'application/javascript')
        elif path == '/api/pets':
            self.get_pets(query)
        elif path == '/api/user':
            self.get_user()
        elif path == '/api/adoptions':
            self.get_adoptions()
        elif path == '/api/applications':
            self.get_applications()
        elif path == '/api/my-donations':
            self.get_my_donations()
        elif path.startswith('/uploads/'):
            self.serve_upload(path)
        else:
            self.send_error(404)

    def do_POST(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path == '/api/signup':
            self.handle_signup()
        elif path == '/api/login':
            self.handle_login()
        elif path == '/api/logout':
            self.handle_logout()
        elif path == '/api/apply':
            self.handle_apply()
        elif path == '/api/approve-application':
            self.handle_approve_application()
        elif path == '/api/donate':
            self.handle_donate()
        elif path == '/api/remove-application':
            self.handle_remove_application()
        elif path == '/api/remove-donation':
            self.handle_remove_donation()
        elif path == '/api/remove-adoption':
            self.handle_remove_adoption()
        else:
            self.send_error(404)

    def serve_file(self, filename, content_type='text/html'):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-type', content_type)
            self.end_headers()
            self.wfile.write(content.encode('utf-8'))
        except FileNotFoundError:
            self.send_error(404)

    def serve_upload(self, path):
        try:
            filename = path[1:]  # Remove leading slash
            with open(filename, 'rb') as f:
                content = f.read()
            content_type, _ = mimetypes.guess_type(filename)
            self.send_response(200)
            self.send_header('Content-type', content_type or 'application/octet-stream')
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_error(404)

    def get_session_id(self):
        cookies = self.headers.get('Cookie', '')
        for cookie in cookies.split(';'):
            if cookie.strip().startswith('session_id='):
                return cookie.split('=')[1].strip()
        return None

    def check_auth(self):
        session_id = self.get_session_id()
        if not session_id:
            return False
        
        conn = sqlite3.connect('pets.db')
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM sessions WHERE session_id = ? AND expires_at > ?', 
                      (session_id, datetime.now()))
        result = cursor.fetchone()
        conn.close()
        return result is not None

    def get_current_user(self):
        session_id = self.get_session_id()
        if not session_id:
            return None
        
        conn = sqlite3.connect('pets.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.id, u.name, u.email FROM users u
            JOIN sessions s ON u.id = s.user_id
            WHERE s.session_id = ? AND s.expires_at > ?
        ''', (session_id, datetime.now()))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {'id': result[0], 'name': result[1], 'email': result[2]}
        return None

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def redirect(self, location):
        self.send_response(302)
        self.send_header('Location', location)
        self.end_headers()

    def get_pets(self, query):
        page = int(query.get('page', [1])[0])
        per_page = 6
        offset = (page - 1) * per_page
        
        conn = sqlite3.connect('pets.db')
        cursor = conn.cursor()
        
        # Get total count
        cursor.execute('SELECT COUNT(*) FROM pets WHERE status = "available"')
        total = cursor.fetchone()[0]
        
        # Get pets for current page
        cursor.execute('''
            SELECT id, name, breed, age, species, image, bio, status, donated_by, location, price, created_at
            FROM pets WHERE status = "available"
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        ''', (per_page, offset))
        
        pets = []
        for row in cursor.fetchall():
            pets.append({
                'id': row[0],
                'name': row[1],
                'breed': row[2],
                'age': row[3],
                'species': row[4],
                'image': row[5],
                'bio': row[6],
                'status': row[7],
                'donated_by': row[8],
                'location': row[9],
                'price': row[10],
                'created_at': row[11]
            })
        
        conn.close()
        
        self.send_json({
            'pets': pets,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page
        })

    def get_user(self):
        user = self.get_current_user()
        if user:
            self.send_json(user)
        else:
            self.send_json({'error': 'Not authenticated'}, 401)

    def get_adoptions(self):
        user = self.get_current_user()
        if not user:
            self.send_json({'error': 'Not authenticated'}, 401)
            return
        
        conn = sqlite3.connect('pets.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT a.id, p.name, p.breed, p.species, p.image, a.adopted_at
            FROM adoptions a
            JOIN pets p ON a.pet_id = p.id
            WHERE a.adopter_id = ?
            ORDER BY a.adopted_at DESC
        ''', (user['id'],))
        
        adoptions = []
        for row in cursor.fetchall():
            adoptions.append({
                'id': row[0],
                'name': row[1],
                'breed': row[2],
                'species': row[3],
                'image': row[4],
                'adopted_at': row[5]
            })
        
        conn.close()
        self.send_json(adoptions)

    def get_applications(self):
        user = self.get_current_user()
        if not user:
            self.send_json({'error': 'Not authenticated'}, 401)
            return
        
        conn = sqlite3.connect('pets.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT aa.id, p.name as pet_name, p.image, aa.applicant_name, 
                   aa.applicant_email, aa.applicant_phone, aa.experience, 
                   aa.living_situation, aa.reason, aa.status, aa.applied_at
            FROM adoption_applications aa
            JOIN pets p ON aa.pet_id = p.id
            WHERE aa.applicant_id = ?
            ORDER BY aa.applied_at DESC
        ''', (user['id'],))
        
        applications = []
        for row in cursor.fetchall():
            applications.append({
                'id': row[0],
                'pet_name': row[1],
                'pet_image': row[2],
                'applicant_name': row[3],
                'applicant_email': row[4],
                'applicant_phone': row[5],
                'experience': row[6],
                'living_situation': row[7],
                'reason': row[8],
                'status': row[9],
                'applied_at': row[10]
            })
        
        conn.close()
        self.send_json(applications)

    def get_my_donations(self):
        user = self.get_current_user()
        if not user:
            self.send_json({'error': 'Not authenticated'}, 401)
            return
        
        conn = sqlite3.connect('pets.db')
        cursor = conn.cursor()
        
        # Get donated pets with application counts
        cursor.execute('''
            SELECT p.id, p.name, p.image, p.status, p.created_at,
                   COUNT(aa.id) as application_count
            FROM pets p
            LEFT JOIN adoption_applications aa ON p.id = aa.pet_id
            WHERE p.donated_by = ?
            GROUP BY p.id
            ORDER BY p.created_at DESC
        ''', (user['id'],))
        
        donations = []
        for row in cursor.fetchall():
            pet_id = row[0]
            
            # Get applications for this pet
            cursor.execute('''
                SELECT aa.id, aa.applicant_name, aa.applicant_email, 
                       aa.applicant_phone, aa.experience, aa.living_situation, 
                       aa.reason, aa.status, aa.applied_at
                FROM adoption_applications aa
                WHERE aa.pet_id = ?
                ORDER BY aa.applied_at DESC
            ''', (pet_id,))
            
            applications = []
            for app_row in cursor.fetchall():
                applications.append({
                    'id': app_row[0],
                    'applicant_name': app_row[1],
                    'applicant_email': app_row[2],
                    'applicant_phone': app_row[3],
                    'experience': app_row[4],
                    'living_situation': app_row[5],
                    'reason': app_row[6],
                    'status': app_row[7],
                    'applied_at': app_row[8]
                })
            
            donations.append({
                'id': row[0],
                'name': row[1],
                'image': row[2],
                'status': row[3],
                'created_at': row[4],
                'application_count': row[5],
                'applications': applications
            })
        
        conn.close()
        self.send_json(donations)
    def handle_signup(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))
        
        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        phone = data.get('phone', '').strip()
        
        if not all([name, email, password, phone]):
            self.send_json({'error': 'All fields are required'}, 400)
            return
        
        # Hash password
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        conn = sqlite3.connect('pets.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO users (name, email, password_hash, phone)
                VALUES (?, ?, ?, ?)
            ''', (name, email, password_hash, phone))
            conn.commit()
            self.send_json({'message': 'Account created successfully'})
        except sqlite3.IntegrityError:
            self.send_json({'error': 'Email already exists'}, 400)
        finally:
            conn.close()

    def handle_login(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))
        
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        if not all([email, password]):
            self.send_json({'error': 'Email and password are required'}, 400)
            return
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        conn = sqlite3.connect('pets.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id, name FROM users WHERE email = ? AND password_hash = ?', 
                      (email, password_hash))
        user = cursor.fetchone()
        
        if user:
            # Create session
            session_id = secrets.token_urlsafe(32)
            expires_at = datetime.now() + timedelta(days=7)
            
            cursor.execute('''
                INSERT INTO sessions (session_id, user_id, expires_at)
                VALUES (?, ?, ?)
            ''', (session_id, user[0], expires_at))
            conn.commit()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Set-Cookie', f'session_id={session_id}; Path=/; Max-Age=604800')
            self.end_headers()
            self.wfile.write(json.dumps({'message': 'Login successful', 'user': {'id': user[0], 'name': user[1]}}).encode('utf-8'))
        else:
            self.send_json({'error': 'Invalid email or password'}, 401)
        
        conn.close()

    def handle_logout(self):
        session_id = self.get_session_id()
        if session_id:
            conn = sqlite3.connect('pets.db')
            cursor = conn.cursor()
            cursor.execute('DELETE FROM sessions WHERE session_id = ?', (session_id,))
            conn.commit()
            conn.close()
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Set-Cookie', 'session_id=; Path=/; Max-Age=0')
        self.end_headers()
        self.wfile.write(json.dumps({'message': 'Logged out successfully'}).encode('utf-8'))

    def handle_apply(self):
        user = self.get_current_user()
        if not user:
            self.send_json({'error': 'Not authenticated'}, 401)
            return
        
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))
        
        pet_id = data.get('pet_id')
        experience = data.get('experience', '').strip()
        living_situation = data.get('living_situation', '').strip()
        reason = data.get('reason', '').strip()
        
        if not all([pet_id, experience, living_situation, reason]):
            self.send_json({'error': 'All fields are required'}, 400)
            return
        
        conn = sqlite3.connect('pets.db')
        cursor = conn.cursor()
        
        # Check if pet is available and get donor info
        cursor.execute('SELECT id, donated_by FROM pets WHERE id = ? AND status = "available"', (pet_id,))
        pet = cursor.fetchone()
        
        if not pet:
            self.send_json({'error': 'Pet not available'}, 400)
            conn.close()
            return
        
        # Check if user already applied for this pet
        cursor.execute('SELECT id FROM adoption_applications WHERE pet_id = ? AND applicant_id = ?', 
                      (pet_id, user['id']))
        existing_application = cursor.fetchone()
        
        if existing_application:
            self.send_json({'error': 'You have already applied for this pet'}, 400)
            conn.close()
            return
        
        try:
            # Create adoption application
            cursor.execute('''
                INSERT INTO adoption_applications 
                (pet_id, applicant_id, donor_id, applicant_name, applicant_email, 
                 applicant_phone, experience, living_situation, reason, applied_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (pet_id, user['id'], pet[1], user['name'], user['email'], 
                  user.get('phone', ''), experience, living_situation, reason, datetime.now()))
            
            conn.commit()
            self.send_json({'message': 'Application submitted successfully! The donor will review and contact you.'})
        except Exception as e:
            conn.rollback()
            self.send_json({'error': 'Failed to submit application'}, 500)
        finally:
            conn.close()

    def handle_approve_application(self):
        user = self.get_current_user()
        if not user:
            self.send_json({'error': 'Not authenticated'}, 401)
            return
        
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))
        
        application_id = data.get('application_id')
        
        conn = sqlite3.connect('pets.db')
        cursor = conn.cursor()
        
        # Get application details and verify donor ownership
        cursor.execute('''
            SELECT aa.pet_id, aa.applicant_id, aa.donor_id, p.donated_by
            FROM adoption_applications aa
            JOIN pets p ON aa.pet_id = p.id
            WHERE aa.id = ? AND aa.donor_id = ?
        ''', (application_id, user['id']))
        
        application = cursor.fetchone()
        
        if not application:
            self.send_json({'error': 'Application not found or unauthorized'}, 400)
            conn.close()
            return
        
        pet_id, applicant_id, donor_id, donated_by = application
        
        try:
            # Update pet status to adopted
            cursor.execute('UPDATE pets SET status = "adopted" WHERE id = ?', (pet_id,))
            
            # Create adoption record
            cursor.execute('''
                INSERT INTO adoptions (pet_id, adopter_id, donor_id, adopted_at)
                VALUES (?, ?, ?, ?)
            ''', (pet_id, applicant_id, donor_id, datetime.now()))
            
            # Update application status to approved
            cursor.execute('UPDATE adoption_applications SET status = "approved" WHERE id = ?', 
                          (application_id,))
            
            # Reject all other applications for this pet
            cursor.execute('UPDATE adoption_applications SET status = "rejected" WHERE pet_id = ? AND id != ?', 
                          (pet_id, application_id))
            
            conn.commit()
            self.send_json({'message': 'Application approved! Pet has been adopted.'})
        except Exception as e:
            conn.rollback()
            self.send_json({'error': 'Failed to approve application'}, 500)
        finally:
            conn.close()

    def handle_donate(self):
        user = self.get_current_user()
        if not user:
            self.send_json({'error': 'Not authenticated'}, 401)
            return
        
        # Parse multipart form data
        content_type = self.headers['Content-Type']
        if not content_type.startswith('multipart/form-data'):
            self.send_json({'error': 'Invalid content type'}, 400)
            return
        
        # Extract boundary from content type
        boundary = content_type.split('boundary=')[1]
        
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        # Parse multipart data
        form_data, files = self.parse_multipart(post_data, boundary)
        
        name = form_data.get('name', '').strip()
        age = form_data.get('age', '').strip()
        breed = form_data.get('breed', '').strip()
        species = form_data.get('species', '').strip()
        bio = form_data.get('bio', '').strip()
        location = form_data.get('location', 'dhaka').strip()
        price = form_data.get('price', '0').strip()
        
        if not all([name, age, breed, species, bio]):
            self.send_json({'error': 'All fields are required'}, 400)
            return
        
        # Handle file upload
        if 'image' not in files or not files['image']['filename']:
            self.send_json({'error': 'Image is required'}, 400)
            return
        
        image_file = files['image']
        
        # Create uploads directory if it doesn't exist
        os.makedirs('uploads', exist_ok=True)
        
        # Generate unique filename
        file_ext = os.path.splitext(image_file['filename'])[1]
        filename = f"{uuid.uuid4()}{file_ext}"
        filepath = os.path.join('uploads', filename)
        
        # Save uploaded file
        with open(filepath, 'wb') as f:
            f.write(image_file['content'])
        
        # Save to database
        conn = sqlite3.connect('pets.db')
        cursor = conn.cursor()
        
        try:
            price_value = int(price) if price and price.isdigit() else 0
            cursor.execute('''
                INSERT INTO pets (name, age, breed, species, bio, image, donated_by, status, created_at, location, price)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, int(age), breed, species, bio, filepath, user['id'], 'available', datetime.now(), location, price_value))
            conn.commit()
            self.send_json({'message': 'Pet donated successfully!'})
        except Exception as e:
            print(f"Error donating pet: {e}")
            self.send_json({'error': 'Failed to donate pet'}, 500)
        finally:
            conn.close()

def init_database():
    conn = sqlite3.connect('pets.db')
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            phone TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER NOT NULL,
            breed TEXT NOT NULL,
            species TEXT NOT NULL,
            bio TEXT NOT NULL,
            image TEXT NOT NULL,
            donated_by INTEGER NOT NULL,
            status TEXT DEFAULT 'available',
            location TEXT DEFAULT 'dhaka',
            price INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (donated_by) REFERENCES users (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS adoptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pet_id INTEGER NOT NULL,
            adopter_id INTEGER NOT NULL,
            donor_id INTEGER NOT NULL,
            adopted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (pet_id) REFERENCES pets (id),
            FOREIGN KEY (adopter_id) REFERENCES users (id),
            FOREIGN KEY (donor_id) REFERENCES users (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS adoption_applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pet_id INTEGER NOT NULL,
            applicant_id INTEGER NOT NULL,
            donor_id INTEGER NOT NULL,
            applicant_name TEXT NOT NULL,
            applicant_email TEXT NOT NULL,
            applicant_phone TEXT NOT NULL,
            experience TEXT NOT NULL,
            living_situation TEXT NOT NULL,
            reason TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (pet_id) REFERENCES pets (id),
            FOREIGN KEY (applicant_id) REFERENCES users (id),
            FOREIGN KEY (donor_id) REFERENCES users (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE NOT NULL,
            user_id INTEGER NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Insert sample data
    cursor.execute('SELECT COUNT(*) FROM users')
    if cursor.fetchone()[0] == 0:
        # Create sample user
        sample_password = hashlib.sha256('password123'.encode()).hexdigest()
        cursor.execute('''
            INSERT INTO users (name, email, password_hash, phone)
            VALUES (?, ?, ?, ?)
        ''', ('Admin User', 'admin@petcenter.com', sample_password, '555-0123'))
        
        admin_id = cursor.lastrowid
        
        # Create sample pets
        sample_pets = [
            ('Buddy', 3, 'Golden Retriever', 'Dog', 'Friendly and energetic golden retriever who loves playing fetch and swimming. Great with kids!', 'https://images.pexels.com/photos/551628/pexels-photo-551628.jpeg?auto=compress&cs=tinysrgb&w=400', 'dhaka', 15000),
            ('Luna', 2, 'Siamese', 'Cat', 'Beautiful and intelligent Siamese cat with striking blue eyes. Loves attention and purring.', 'https://images.pexels.com/photos/45201/kitty-cat-kitten-pet-45201.jpeg?auto=compress&cs=tinysrgb&w=400', 'chittagong', 8000),
            ('Max', 4, 'German Shepherd', 'Dog', 'Loyal and protective German Shepherd. Well-trained and perfect for active families.', 'https://images.pexels.com/photos/1108099/pexels-photo-1108099.jpeg?auto=compress&cs=tinysrgb&w=400', 'dhaka', 25000),
            ('Whiskers', 5, 'Persian', 'Cat', 'Gentle Persian cat with long, fluffy fur. Calm and affectionate, perfect for quiet homes.', 'https://images.pexels.com/photos/596590/pexels-photo-596590.jpeg?auto=compress&cs=tinysrgb&w=400', 'sylhet', 12000),
            ('Bella', 2, 'Labrador', 'Dog', 'Sweet and gentle Labrador who loves everyone she meets. Great with children and other pets.', 'https://images.pexels.com/photos/1805164/pexels-photo-1805164.jpeg?auto=compress&cs=tinysrgb&w=400', 'rajshahi', 0),
            ('Mittens', 3, 'Maine Coon', 'Cat', 'Majestic Maine Coon with a playful personality. Loves climbing and interactive toys.', 'https://images.pexels.com/photos/1170986/pexels-photo-1170986.jpeg?auto=compress&cs=tinysrgb&w=400', 'dhaka', 18000),
            ('Charlie', 1, 'Beagle', 'Dog', 'Young and playful Beagle puppy. Full of energy and loves to explore. Perfect for active families.', 'https://images.pexels.com/photos/1254140/pexels-photo-1254140.jpeg?auto=compress&cs=tinysrgb&w=400', 'chittagong', 10000),
            ('Shadow', 4, 'British Shorthair', 'Cat', 'Calm and dignified British Shorthair. Independent but affectionate. Great for apartment living.', 'https://images.pexels.com/photos/1741205/pexels-photo-1741205.jpeg?auto=compress&cs=tinysrgb&w=400', 'dhaka', 0)
        ]
        
        for pet in sample_pets:
            cursor.execute('''
                INSERT INTO pets (name, age, breed, species, bio, image, donated_by, status, created_at, location, price)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (*pet[:6], admin_id, 'available', datetime.now(), pet[6], pet[7]))
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_database()
    server = HTTPServer(('localhost', 8000), PetAdoptionHandler)
    print("Server running on http://localhost:8000")
    server.serve_forever()