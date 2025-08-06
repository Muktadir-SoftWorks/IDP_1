// Global variables
let currentPage = 1;
let currentUser = null;
let currentCategory = 'all';
let currentFilters = {};

// Initialize app
document.addEventListener('DOMContentLoaded', function() {
    checkAuthStatus();
    loadPets();
    setupEventListeners();
});

// Setup event listeners
function setupEventListeners() {
    // Category selection
    document.querySelectorAll('.category-item').forEach(item => {
        item.addEventListener('click', function() {
            selectCategory(this.dataset.category);
        });
    });

    // Search functionality
    document.getElementById('search-input').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            performSearch();
        }
    });

    document.querySelector('.search-btn').addEventListener('click', performSearch);

    // Sort functionality
    document.getElementById('sort-select').addEventListener('change', function() {
        loadPets(1, this.value);
    });

    // Filter functionality
    document.querySelector('.apply-filters-btn').addEventListener('click', applyFilters);

    // Modal close
    document.querySelector('.close-modal').addEventListener('click', closeModal);
    window.addEventListener('click', function(e) {
        if (e.target.classList.contains('modal')) {
            closeModal();
        }
    });

    // Logout
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', logout);
    }
}

// Authentication functions
async function checkAuthStatus() {
    try {
        const response = await fetch('/api/user');
        if (response.ok) {
            currentUser = await response.json();
            showUserSection();
        } else {
            showAuthSection();
        }
    } catch (error) {
        showAuthSection();
    }
}

function showUserSection() {
    const authSection = document.getElementById('auth-section');
    const userSection = document.getElementById('user-section');
    const userName = document.getElementById('user-name');
    
    if (authSection) authSection.style.display = 'none';
    if (userSection) userSection.style.display = 'flex';
    if (userName && currentUser) userName.textContent = `Hello, ${currentUser.name}`;
}

function showAuthSection() {
    const authSection = document.getElementById('auth-section');
    const userSection = document.getElementById('user-section');
    
    if (authSection) authSection.style.display = 'flex';
    if (userSection) userSection.style.display = 'none';
}

async function logout() {
    try {
        await fetch('/api/logout', { method: 'POST' });
        currentUser = null;
        showAuthSection();
        window.location.href = '/';
    } catch (error) {
        window.location.href = '/';
    }
}

// Category selection
function selectCategory(category) {
    currentCategory = category;
    currentPage = 1;
    
    // Update active category
    document.querySelectorAll('.category-item').forEach(item => {
        item.classList.remove('active');
    });
    document.querySelector(`[data-category="${category}"]`).classList.add('active');
    
    // Update breadcrumb
    const categoryNames = {
        'all': 'All Pets',
        'Dog': 'Dogs',
        'Cat': 'Cats',
        'Bird': 'Birds',
        'Rabbit': 'Rabbits',
        'Other': 'Others'
    };
    document.getElementById('current-category').textContent = categoryNames[category];
    
    loadPets();
}

// Search functionality
function performSearch() {
    const searchTerm = document.getElementById('search-input').value;
    const location = document.getElementById('location-select').value;
    
    currentFilters.search = searchTerm;
    currentFilters.location = location;
    currentPage = 1;
    
    loadPets();
}

// Filter functionality
function applyFilters() {
    const minPrice = document.getElementById('min-price').value;
    const maxPrice = document.getElementById('max-price').value;
    
    currentFilters.minPrice = minPrice;
    currentFilters.maxPrice = maxPrice;
    
    // Get selected age ranges
    const ageFilters = [];
    document.querySelectorAll('.checkbox-group input[type="checkbox"]:checked').forEach(checkbox => {
        if (checkbox.value.includes('-') || checkbox.value.includes('+')) {
            ageFilters.push(checkbox.value);
        }
    });
    currentFilters.ages = ageFilters;
    
    // Get selected locations
    const locationFilters = [];
    document.querySelectorAll('.checkbox-group input[type="checkbox"]:checked').forEach(checkbox => {
        if (['dhaka', 'chittagong', 'sylhet', 'rajshahi'].includes(checkbox.value)) {
            locationFilters.push(checkbox.value);
        }
    });
    currentFilters.locations = locationFilters;
    
    currentPage = 1;
    loadPets();
}

// Pet loading functions
async function loadPets(page = 1, sort = 'newest') {
    try {
        showLoading();
        
        let url = `/api/pets?page=${page}`;
        if (currentCategory !== 'all') {
            url += `&category=${currentCategory}`;
        }
        if (sort) {
            url += `&sort=${sort}`;
        }
        
        // Add filters to URL
        Object.keys(currentFilters).forEach(key => {
            if (currentFilters[key] && currentFilters[key] !== '') {
                if (Array.isArray(currentFilters[key])) {
                    currentFilters[key].forEach(value => {
                        url += `&${key}[]=${value}`;
                    });
                } else {
                    url += `&${key}=${currentFilters[key]}`;
                }
            }
        });
        
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

function displayPets(pets) {
    const petsGrid = document.getElementById('pets-grid');
    
    if (!petsGrid) return;
    
    if (pets.length === 0) {
        petsGrid.innerHTML = '<div class="no-data">No pets found matching your criteria.</div>';
        return;
    }
    
    petsGrid.innerHTML = pets.map(pet => `
        <div class="pet-card" onclick="showPetDetails(${pet.id})">
            <img src="${pet.image}" alt="${pet.name}" class="pet-image" onerror="this.src='https://images.pexels.com/photos/45201/kitty-cat-kitten-pet-45201.jpeg?auto=compress&cs=tinysrgb&w=400'">
            <div class="pet-info">
                <div class="pet-header">
                    <h3 class="pet-name">${pet.name}</h3>
                    <div class="pet-price ${pet.price ? '' : 'free'}">
                        ${pet.price ? '৳' + pet.price : 'Free'}
                    </div>
                </div>
                <div class="pet-details">
                    <span class="pet-detail">${pet.species}</span>
                    <span class="pet-detail">${pet.breed}</span>
                    <span class="pet-detail">${pet.age} years</span>
                </div>
                <p class="pet-description">${pet.bio}</p>
                <div class="pet-location">📍 ${pet.location || 'Dhaka'}</div>
                <div class="pet-actions">
                    ${currentUser ? 
                        `<button class="adopt-btn" onclick="event.stopPropagation(); adoptPet(${pet.id})">Adopt Now</button>
                         <button class="contact-btn" onclick="event.stopPropagation(); contactSeller(${pet.id})"></button>` :
                        `<button class="adopt-btn" onclick="event.stopPropagation(); window.location.href='/login.html'">Login to Adopt</button>`
                    }
                </div>
            </div>
        </div>
    `).join('');
}

function updateResultsCount(total) {
    const resultsCount = document.getElementById('results-count');
    if (resultsCount) {
        resultsCount.textContent = `${total} ads found`;
    }
}

function updatePagination(data) {
    const pagination = document.getElementById('pagination');
    const prevBtn = document.getElementById('prev-btn');
    const nextBtn = document.getElementById('next-btn');
    const pageNumbers = document.getElementById('page-numbers');
    
    if (!pagination) return;
    
    if (data.total_pages > 1) {
        pagination.style.display = 'flex';
        
        // Update prev/next buttons
        prevBtn.disabled = data.page <= 1;
        nextBtn.disabled = data.page >= data.total_pages;
        
        // Update page numbers
        let pagesHtml = '';
        const startPage = Math.max(1, data.page - 2);
        const endPage = Math.min(data.total_pages, data.page + 2);
        
        for (let i = startPage; i <= endPage; i++) {
            pagesHtml += `<button class="page-number ${i === data.page ? 'active' : ''}" onclick="loadPets(${i})">${i}</button>`;
        }
        
        pageNumbers.innerHTML = pagesHtml;
        
        // Add event listeners for prev/next
        prevBtn.onclick = () => loadPets(data.page - 1);
        nextBtn.onclick = () => loadPets(data.page + 1);
    } else {
        pagination.style.display = 'none';
    }
}

// Pet detail functions
async function showPetDetails(petId) {
    try {
        const response = await fetch(`/api/pets?page=1`);
        const data = await response.json();
        const pet = data.pets.find(p => p.id === petId);
        
        if (pet) {
            displayPetModal(pet);
            document.getElementById('pet-modal').style.display = 'block';
        }
    } catch (error) {
        console.error('Error loading pet details:', error);
        showError('Failed to load pet details. Please try again.');
    }
}

function displayPetModal(pet) {
    const petDetails = document.getElementById('pet-details');
    if (!petDetails) return;
    
    petDetails.innerHTML = `
        <div class="pet-detail-modal">
            <img src="${pet.image}" alt="${pet.name}" class="pet-detail-image" onerror="this.src='https://images.pexels.com/photos/45201/kitty-cat-kitten-pet-45201.jpeg?auto=compress&cs=tinysrgb&w=400'">
            
            <div class="pet-detail-header">
                <h2 class="pet-detail-title">${pet.name}</h2>
                <div class="pet-detail-price ${pet.price ? '' : 'free'}">
                    ${pet.price ? '৳' + pet.price : 'Free'}
                </div>
            </div>
            
            <div class="pet-detail-specs">
                <div class="pet-spec"><strong>Species:</strong> ${pet.species}</div>
                <div class="pet-spec"><strong>Breed:</strong> ${pet.breed}</div>
                <div class="pet-spec"><strong>Age:</strong> ${pet.age} years</div>
                <div class="pet-spec"><strong>Status:</strong> ${pet.status}</div>
                <div class="pet-spec"><strong>Location:</strong> ${pet.location || 'Dhaka'}</div>
                <div class="pet-spec"><strong>Posted:</strong> ${new Date(pet.created_at).toLocaleDateString()}</div>
            </div>
            
            <div class="pet-detail-description">
                <h4>About ${pet.name}</h4>
                <p>${pet.bio}</p>
            </div>
            
            <div class="pet-detail-actions">
                ${currentUser ? 
                    `<button class="adopt-btn" onclick="adoptPet(${pet.id})">Adopt ${pet.name}</button>
                     <button class="contact-btn" onclick="contactSeller(${pet.id})"></button>` :
                    `<button class="adopt-btn" onclick="window.location.href='/login.html'">Login to Adopt</button>`
                }
            </div>
        </div>
    `;
}

function closeModal() {
    const modal = document.getElementById('pet-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// Adoption and contact functions
async function adoptPet(petId) {
    if (!currentUser) {
        window.location.href = '/login.html';
        return;
    }
    
    // Show adoption application form
    showAdoptionForm(petId);
}

function showAdoptionForm(petId) {
    const formHtml = `
        <div class="adoption-form-modal">
            <h3>Adoption Application</h3>
            <form id="adoption-form">
                <input type="hidden" id="pet-id" value="${petId}">
                
                <div class="form-group">
                    <label for="experience">Pet Care Experience *</label>
                    <textarea id="experience" placeholder="Describe your experience with pets..." required></textarea>
                </div>
                
                <div class="form-group">
                    <label for="living-situation">Living Situation *</label>
                    <textarea id="living-situation" placeholder="Describe your home, yard, family members..." required></textarea>
                </div>
                
                <div class="form-group">
                    <label for="reason">Why do you want to adopt this pet? *</label>
                    <textarea id="reason" placeholder="Tell us why you want to adopt this pet..." required></textarea>
                </div>
                
                <div class="form-actions">
                    <button type="button" onclick="closeModal()" class="cancel-btn">Cancel</button>
                    <button type="submit" class="submit-btn">Submit Application</button>
                </div>
            </form>
        </div>
    `;
    
    document.getElementById('pet-details').innerHTML = formHtml;
    document.getElementById('pet-modal').style.display = 'block';
    
    // Handle form submission
    document.getElementById('adoption-form').addEventListener('submit', handleAdoptionApplication);
}

async function handleAdoptionApplication(e) {
    e.preventDefault();
    
    const petId = document.getElementById('pet-id').value;
    const experience = document.getElementById('experience').value.trim();
    const livingSituation = document.getElementById('living-situation').value.trim();
    const reason = document.getElementById('reason').value.trim();
    
    if (!experience || !livingSituation || !reason) {
        showError('Please fill in all fields');
        return;
    }
    
    try {
        const response = await fetch('/api/apply', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                pet_id: petId,
                experience: experience,
                living_situation: livingSituation,
                reason: reason
            })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showSuccess(result.message);
            closeModal();
            // Don't reload pets as the pet should still be available for other applications
        } else {
            showError(result.error);
        }
    } catch (error) {
        console.error('Error submitting application:', error);
        showError('Failed to submit application. Please try again.');
    }
}

// Utility functions
function showLoading() {
    const petsGrid = document.getElementById('pets-grid');
    if (petsGrid) {
        petsGrid.innerHTML = `
            <div class="loading">
                <div class="spinner"></div>
                <p>Loading pets...</p>
            </div>
        `;
    }
}

function showSuccess(message) {
    showMessage(message, 'success');
}

function showError(message) {
    showMessage(message, 'error');
}

function showMessage(text, type) {
    // Remove existing messages
    const existingMessages = document.querySelectorAll('.message');
    existingMessages.forEach(msg => msg.remove());
    
    // Create and show new message
    const notification = document.createElement('div');
    notification.className = `message ${type}`;
    notification.textContent = text;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 5000);
}

// Make functions globally available
window.selectCategory = selectCategory;
window.showPetDetails = showPetDetails;
window.closeModal = closeModal;
window.adoptPet = adoptPet;
window.loadPets = loadPets;