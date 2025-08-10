@@ .. @@
 // Global variables
 let currentPage = 1;
 let currentUser = null;
 let currentCategory = 'all';
-let currentFilters = {};
+let currentFilters = {
+    search: '',
+    location: '',
+    minPrice: '',
+    maxPrice: '',
+    ages: [],
+    locations: []
+};

 // Initialize app
@@ .. @@
 // Filter functionality
 function applyFilters() {
     const minPrice = document.getElementById('min-price').value;
     const maxPrice = document.getElementById('max-price').value;
     
     currentFilters.minPrice = minPrice;
     currentFilters.maxPrice = maxPrice;
     
     // Get selected age ranges
     const ageFilters = [];
-    document.querySelectorAll('.checkbox-group input[type="checkbox"]:checked').forEach(checkbox => {
+    document.querySelectorAll('.filter-group:nth-child(2) .checkbox-group input[type="checkbox"]:checked').forEach(checkbox => {
         if (checkbox.value.includes('-') || checkbox.value.includes('+')) {
             ageFilters.push(checkbox.value);
         }
     });
     currentFilters.ages = ageFilters;
     
     // Get selected locations
     const locationFilters = [];
-    document.querySelectorAll('.checkbox-group input[type="checkbox"]:checked').forEach(checkbox => {
+    document.querySelectorAll('.filter-group:nth-child(3) .checkbox-group input[type="checkbox"]:checked').forEach(checkbox => {
         if (['dhaka', 'chittagong', 'sylhet', 'rajshahi'].includes(checkbox.value)) {
             locationFilters.push(checkbox.value);
         }
     });
     currentFilters.locations = locationFilters;
     
     currentPage = 1;
     loadPets();
 }

@@ .. @@
 async function loadPets(page = 1, sort = 'newest') {
     try {
         showLoading();
         
-        let url = `/api/pets?page=${page}`;
+        const params = new URLSearchParams();
+        params.append('page', page);
+        
         if (currentCategory !== 'all') {
-            url += `&category=${currentCategory}`;
+            params.append('category', currentCategory);
         }
         if (sort) {
-            url += `&sort=${sort}`;
+            params.append('sort', sort);
         }
         
         // Add filters to URL
         Object.keys(currentFilters).forEach(key => {
             if (currentFilters[key] && currentFilters[key] !== '') {
                 if (Array.isArray(currentFilters[key])) {
                     currentFilters[key].forEach(value => {
-                        url += `&${key}[]=${value}`;
+                        params.append(`${key}[]`, value);
                     });
                 } else {
-                    url += `&${key}=${currentFilters[key]}`;
+                    params.append(key, currentFilters[key]);
                 }
             }
         });
         
+        const url = `/api/pets?${params.toString()}`;
         const response = await fetch(url);
         const data = await response.json();
         
         displayPets(data.pets);
         updatePagination(data);
         updateResultsCount(data.total);
         currentPage = page;
     } catch (error) {
         console.error('Error loading pets:', error);
         showError('Failed to load pets. Please try again.');
     }
 }

@@ .. @@
                 <div class="pet-actions">
                     ${currentUser ? 
-                        `<button class="adopt-btn" onclick="event.stopPropagation(); adoptPet(${pet.id})">Adopt Now</button>
-                         <button class="contact-btn" onclick="event.stopPropagation(); contactSeller(${pet.id})"></button>` :
+                        `<button class="adopt-btn" onclick="event.stopPropagation(); adoptPet(${pet.id})">Adopt Now</button>` +
+                        (currentUser.email === 'admin@petcenter.com' ? 
+                            `<button class="delete-btn" onclick="event.stopPropagation(); deletePet(${pet.id})">Delete</button>` : '') :
                         `<button class="adopt-btn" onclick="event.stopPropagation(); window.location.href='/login.html'">Login to Adopt</button>`
                     }
                 </div>
@@ .. @@
             <div class="pet-detail-actions">
                 ${currentUser ? 
-                    `<button class="adopt-btn" onclick="adoptPet(${pet.id})">Adopt ${pet.name}</button>
-                     <button class="contact-btn" onclick="contactSeller(${pet.id})"></button>` :
+                    `<button class="adopt-btn" onclick="adoptPet(${pet.id})">Adopt ${pet.name}</button>` +
+                    (currentUser.email === 'admin@petcenter.com' ? 
+                        `<button class="delete-btn" onclick="deletePet(${pet.id})">Delete Pet</button>` : '') :
                     `<button class="adopt-btn" onclick="window.location.href='/login.html'">Login to Adopt</button>`
                 }
             </div>
@@ .. @@
     }
 }

+// Delete pet function (admin only)
+async function deletePet(petId) {
+    if (!currentUser || currentUser.email !== 'admin@petcenter.com') {
+        showError('Unauthorized action');
+        return;
+    }
+    
+    if (!confirm('Are you sure you want to delete this pet? This action cannot be undone.')) {
+        return;
+    }
+    
+    try {
+        const response = await fetch('/api/delete-pet', {
+            method: 'POST',
+            headers: {
+                'Content-Type': 'application/json',
+            },
+            body: JSON.stringify({ pet_id: petId })
+        });
+        
+        const result = await response.json();
+        
+        if (response.ok) {
+            showSuccess(result.message);
+            closeModal();
+            loadPets(); // Reload pets
+        } else {
+            showError(result.error);
+        }
+    } catch (error) {
+        console.error('Error deleting pet:', error);
+        showError('Failed to delete pet. Please try again.');
+    }
+}
+
 // Utility functions
@@ .. @@
 // Make functions globally available
 window.selectCategory = selectCategory;
 window.showPetDetails = showPetDetails;
 window.closeModal = closeModal;
 window.adoptPet = adoptPet;
 window.loadPets = loadPets;
+window.deletePet = deletePet;