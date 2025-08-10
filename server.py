@@ .. @@
     def get_pets(self, query):
         page = int(query.get('page', [1])[0])
         per_page = 6
         offset = (page - 1) * per_page
         
         conn = sqlite3.connect('pets.db')
         cursor = conn.cursor()
         
-        # Get total count
-        cursor.execute('SELECT COUNT(*) FROM pets WHERE status = "available"')
+        # Build WHERE clause based on filters
+        where_conditions = ['status = "available"']
+        params = []
+        
+        # Category filter
+        if 'category' in query and query['category'][0] != 'all':
+            where_conditions.append('species = ?')
+            params.append(query['category'][0])
+        
+        # Search filter
+        if 'search' in query and query['search'][0]:
+            search_term = f"%{query['search'][0]}%"
+            where_conditions.append('(name LIKE ? OR breed LIKE ? OR bio LIKE ?)')
+            params.extend([search_term, search_term, search_term])
+        
+        # Location filter
+        if 'location' in query and query['location'][0]:
+            where_conditions.append('location = ?')
+            params.append(query['location'][0])
+        
+        # Price filters
+        if 'minPrice' in query and query['minPrice'][0]:
+            where_conditions.append('price >= ?')
+            params.append(int(query['minPrice'][0]))
+        
+        if 'maxPrice' in query and query['maxPrice'][0]:
+            where_conditions.append('price <= ?')
+            params.append(int(query['maxPrice'][0]))
+        
+        # Age filters
+        if 'ages[]' in query:
+            age_conditions = []
+            for age_range in query['ages[]']:
+                if age_range == '0-1':
+                    age_conditions.append('age BETWEEN 0 AND 1')
+                elif age_range == '1-3':
+                    age_conditions.append('age BETWEEN 1 AND 3')
+                elif age_range == '3-5':
+                    age_conditions.append('age BETWEEN 3 AND 5')
+                elif age_range == '5+':
+                    age_conditions.append('age >= 5')
+            
+            if age_conditions:
+                where_conditions.append(f"({' OR '.join(age_conditions)})")
+        
+        # Location filters (from checkboxes)
+        if 'locations[]' in query:
+            location_conditions = []
+            for location in query['locations[]']:
+                location_conditions.append('location = ?')
+                params.append(location)
+            
+            if location_conditions:
+                where_conditions.append(f"({' OR '.join(location_conditions)})")
+        
+        where_clause = ' AND '.join(where_conditions)
+        
+        # Sort options
+        sort_clause = 'ORDER BY created_at DESC'  # default
+        if 'sort' in query:
+            sort_option = query['sort'][0]
+            if sort_option == 'oldest':
+                sort_clause = 'ORDER BY created_at ASC'
+            elif sort_option == 'price-low':
+                sort_clause = 'ORDER BY price ASC'
+            elif sort_option == 'price-high':
+                sort_clause = 'ORDER BY price DESC'
+        
+        # Get total count
+        cursor.execute(f'SELECT COUNT(*) FROM pets WHERE {where_clause}', params)
         total = cursor.fetchone()[0]
         
         # Get pets for current page
-        cursor.execute('''
-            SELECT id, name, breed, age, species, image, bio, status, donated_by, location, price, created_at
-            FROM pets WHERE status = "available"
-            ORDER BY created_at DESC
-            LIMIT ? OFFSET ?
-        ''', (per_page, offset))
+        cursor.execute(f'''
+            SELECT id, name, breed, age, species, image, bio, status, donated_by, location, price, created_at
+            FROM pets WHERE {where_clause}
+            {sort_clause}
+            LIMIT ? OFFSET ?
+        ''', params + [per_page, offset])
         
         pets = []
         for row in cursor.fetchall():
@@ .. @@
         elif path == '/api/remove-donation':
             self.handle_remove_donation()
-        elif path == '/api/remove-adoption':
-            self.handle_remove_adoption()
+        elif path == '/api/delete-pet':
+            self.handle_delete_pet()
         else:
             self.send_error(404)

@@ .. @@
         finally:
             conn.close()

+    def handle_remove_donation(self):
+        user = self.get_current_user()
+        if not user:
+            self.send_json({'error': 'Not authenticated'}, 401)
+            return
+        
+        content_length = int(self.headers['Content-Length'])
+        post_data = self.rfile.read(content_length)
+        data = json.loads(post_data.decode('utf-8'))
+        
+        donation_id = data.get('donation_id')
+        
+        conn = sqlite3.connect('pets.db')
+        cursor = conn.cursor()
+        
+        # Verify ownership
+        cursor.execute('SELECT donated_by FROM pets WHERE id = ?', (donation_id,))
+        pet = cursor.fetchone()
+        
+        if not pet or pet[0] != user['id']:
+            self.send_json({'error': 'Pet not found or unauthorized'}, 400)
+            conn.close()
+            return
+        
+        try:
+            # Delete all applications for this pet
+            cursor.execute('DELETE FROM adoption_applications WHERE pet_id = ?', (donation_id,))
+            
+            # Delete the pet
+            cursor.execute('DELETE FROM pets WHERE id = ?', (donation_id,))
+            
+            conn.commit()
+            self.send_json({'message': 'Donation deleted successfully'})
+        except Exception as e:
+            conn.rollback()
+            self.send_json({'error': 'Failed to delete donation'}, 500)
+        finally:
+            conn.close()
+
+    def handle_delete_pet(self):
+        user = self.get_current_user()
+        if not user or user['email'] != 'admin@petcenter.com':
+            self.send_json({'error': 'Unauthorized'}, 403)
+            return
+        
+        content_length = int(self.headers['Content-Length'])
+        post_data = self.rfile.read(content_length)
+        data = json.loads(post_data.decode('utf-8'))
+        
+        pet_id = data.get('pet_id')
+        
+        conn = sqlite3.connect('pets.db')
+        cursor = conn.cursor()
+        
+        try:
+            # Delete all applications for this pet
+            cursor.execute('DELETE FROM adoption_applications WHERE pet_id = ?', (pet_id,))
+            
+            # Delete any adoptions for this pet
+            cursor.execute('DELETE FROM adoptions WHERE pet_id = ?', (pet_id,))
+            
+            # Delete the pet
+            cursor.execute('DELETE FROM pets WHERE id = ?', (pet_id,))
+            
+            conn.commit()
+            self.send_json({'message': 'Pet deleted successfully'})
+        except Exception as e:
+            conn.rollback()
+            self.send_json({'error': 'Failed to delete pet'}, 500)
+        finally:
+            conn.close()
+
 def init_database():