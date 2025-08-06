// Simple pet data (no database needed for beginners)
const pets = [
    {
        id: 1,
        name: "Buddy",
        species: "Dog",
        breed: "Golden Retriever",
        age: 3,
        description: "Friendly and energetic dog who loves playing fetch. Great with kids!",
        image: "https://images.pexels.com/photos/551628/pexels-photo-551628.jpeg?auto=compress&cs=tinysrgb&w=400",
        price: 0,
        location: "Dhaka"
    },
    {
        id: 2,
        name: "Luna",
        species: "Cat",
        breed: "Siamese",
        age: 2,
        description: "Beautiful cat with striking blue eyes. Loves attention and purring.",
        image: "https://images.pexels.com/photos/45201/kitty-cat-kitten-pet-45201.jpeg?auto=compress&cs=tinysrgb&w=400",
        price: 5000,
        location: "Chittagong"
    },
    {
        id: 3,
        name: "Max",
        species: "Dog",
        breed: "German Shepherd",
        age: 4,
        description: "Loyal and protective dog. Well-trained and perfect for families.",
        image: "https://images.pexels.com/photos/1108099/pexels-photo-1108099.jpeg?auto=compress&cs=tinysrgb&w=400",
        price: 15000,
        location: "Dhaka"
    },
    {
        id: 4,
        name: "Whiskers",
        species: "Cat",
        breed: "Persian",
        age: 5,
        description: "Gentle cat with long, fluffy fur. Perfect for quiet homes.",
        image: "https://images.pexels.com/photos/596590/pexels-photo-596590.jpeg?auto=compress&cs=tinysrgb&w=400",
        price: 8000,
        location: "Sylhet"
    },
    {
        id: 5,
        name: "Charlie",
        species: "Bird",
        breed: "Parrot",
        age: 2,
        description: "Colorful and talkative parrot. Loves to learn new words!",
        image: "https://images.pexels.com/photos/1661179/pexels-photo-1661179.jpeg?auto=compress&cs=tinysrgb&w=400",
        price: 3000,
        location: "Dhaka"
    },
    {
        id: 6,
        name: "Bella",
        species: "Dog",
        breed: "Labrador",
        age: 2,
        description: "Sweet and gentle dog who loves everyone. Great with children.",
        image: "https://images.pexels.com/photos/1805164/pexels-photo-1805164.jpeg?auto=compress&cs=tinysrgb&w=400",
        price: 0,
        location: "Rajshahi"
    }
];

// Global variables
let currentCategory = 'all';
let searchTerm = '';

// Initialize the app
document.addEventListener('DOMContentLoaded', function() {
    displayPets(pets);
    setupEventListeners();
});

// Setup event listeners
function setupEventListeners() {
    // Category buttons
    document.querySelectorAll('.category-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            // Remove active class from all buttons
            document.querySelectorAll('.category-btn').forEach(b => b.classList.remove('active'));
            // Add active class to clicked button
            this.classList.add('active');
            
            currentCategory = this.dataset.category;
            filterAndDisplayPets();
        });
    });

    // Search functionality
    document.getElementById('search-btn').addEventListener('click', performSearch);
    document.getElementById('search-input').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            performSearch();
        }
    });

    // Modal close
    document.querySelector('.close').addEventListener('click', closeModal);
    window.addEventListener('click', function(e) {
        if (e.target.classList.contains('modal')) {
            closeModal();
        }
    });
}

// Display pets in the grid
function displayPets(petsToShow) {
    const petsGrid = document.getElementById('pets-grid');
    
    if (petsToShow.length === 0) {
        petsGrid.innerHTML = '<div class="no-pets">No pets found matching your search.</div>';
        return;
    }
    
    petsGrid.innerHTML = petsToShow.map(pet => `
        <div class="pet-card" onclick="showPetDetails(${pet.id})">
            <img src="${pet.image}" alt="${pet.name}" class="pet-image">
            <div class="pet-info">
                <h3 class="pet-name">${pet.name}</h3>
                <div class="pet-details">
                    <strong>${pet.species}</strong> • ${pet.breed} • ${pet.age} years old
                </div>
                <p class="pet-description">${pet.description}</p>
                <div class="pet-price ${pet.price === 0 ? 'free' : ''}">
                    ${pet.price === 0 ? 'Free' : '৳' + pet.price}
                </div>
            </div>
        </div>
    `).join('');
}

// Filter and display pets based on category and search
function filterAndDisplayPets() {
    let filteredPets = pets;
    
    // Filter by category
    if (currentCategory !== 'all') {
        filteredPets = filteredPets.filter(pet => pet.species === currentCategory);
    }
    
    // Filter by search term
    if (searchTerm) {
        filteredPets = filteredPets.filter(pet => 
            pet.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
            pet.breed.toLowerCase().includes(searchTerm.toLowerCase()) ||
            pet.species.toLowerCase().includes(searchTerm.toLowerCase()) ||
            pet.description.toLowerCase().includes(searchTerm.toLowerCase())
        );
    }
    
    displayPets(filteredPets);
}

// Perform search
function performSearch() {
    searchTerm = document.getElementById('search-input').value.trim();
    filterAndDisplayPets();
}

// Show pet details in modal
function showPetDetails(petId) {
    const pet = pets.find(p => p.id === petId);
    if (!pet) return;
    
    const petDetails = document.getElementById('pet-details');
    petDetails.innerHTML = `
        <img src="${pet.image}" alt="${pet.name}" class="pet-detail-image">
        <h2 class="pet-detail-title">${pet.name}</h2>
        
        <div class="pet-detail-info">
            <div class="info-item">
                <div class="info-label">Species:</div>
                <div>${pet.species}</div>
            </div>
            <div class="info-item">
                <div class="info-label">Breed:</div>
                <div>${pet.breed}</div>
            </div>
            <div class="info-item">
                <div class="info-label">Age:</div>
                <div>${pet.age} years old</div>
            </div>
            <div class="info-item">
                <div class="info-label">Location:</div>
                <div>${pet.location}</div>
            </div>
            <div class="info-item">
                <div class="info-label">Price:</div>
                <div class="${pet.price === 0 ? 'free' : ''}">${pet.price === 0 ? 'Free' : '৳' + pet.price}</div>
            </div>
        </div>
        
        <div class="pet-detail-description">
            <h4>About ${pet.name}:</h4>
            <p>${pet.description}</p>
        </div>
        
        <button class="contact-btn" onclick="contactOwner('${pet.name}')">
            Contact for Adoption
        </button>
    `;
    
    document.getElementById('pet-modal').style.display = 'block';
}

// Close modal
function closeModal() {
    document.getElementById('pet-modal').style.display = 'none';
}

// Contact owner (simplified)
function contactOwner(petName) {
    alert(`Thank you for your interest in ${petName}! In a real application, this would connect you with the pet owner. For now, you can call us at: +880 1234-567890`);
}

// Make functions available globally
window.showPetDetails = showPetDetails;
window.contactOwner = contactOwner;