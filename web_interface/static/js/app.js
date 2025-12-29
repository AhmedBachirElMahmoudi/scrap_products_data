const API_BASE = 'http://localhost:5000/api';
let allProducts = [];
let filteredProducts = [];
let currentFilter = 'all';
let currentPage = 1;
const itemsPerPage = 50;
let totalPages = 1;

// Charger les statistiques
async function loadStats() {
    try {
        const response = await fetch(`${API_BASE}/stats`);
        const data = await response.json();

        if (data.success) {
            document.getElementById('total-products').textContent = data.stats.total_products;
            document.getElementById('dix-cheaper').textContent = data.stats.dix_cheaper;
            document.getElementById('dix-percentage').textContent = data.stats.dix_cheaper_percentage + '%';
        }
    } catch (error) {
        console.error('Erreur chargement stats:', error);
    }
}

// Charger les produits
async function loadProducts() {
    try {
        const response = await fetch(`${API_BASE}/products`);
        const data = await response.json();

        if (data.success) {
            allProducts = data.products;
            filteredProducts = allProducts;
            updatePagination();
            displayCurrentPage();
            document.getElementById('loading').style.display = 'none';
            document.getElementById('products-table').style.display = 'table';
            document.getElementById('pagination').style.display = 'flex';
        }
    } catch (error) {
        console.error('Erreur chargement produits:', error);
        document.getElementById('loading').innerHTML = '<p>Erreur de chargement</p>';
    }
}

// Mise à jour pagination
function updatePagination() {
    totalPages = Math.ceil(filteredProducts.length / itemsPerPage);
    if (currentPage > totalPages) currentPage = 1;

    document.getElementById('page-info').textContent = `Page ${currentPage} / ${totalPages}`;
    document.getElementById('btn-first').disabled = currentPage === 1;
    document.getElementById('btn-prev').disabled = currentPage === 1;
    document.getElementById('btn-next').disabled = currentPage === totalPages;
    document.getElementById('btn-last').disabled = currentPage === totalPages;
}

// Afficher la page courante
function displayCurrentPage() {
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    const pageProducts = filteredProducts.slice(startIndex, endIndex);

    displayProducts(pageProducts);
}

// Afficher les produits
function displayProducts(products) {
    const tbody = document.getElementById('products-body');
    tbody.innerHTML = '';

    if (products.length === 0 && filteredProducts.length === 0) {
        document.getElementById('products-table').style.display = 'none';
        document.getElementById('no-results').style.display = 'block';
        document.getElementById('pagination').style.display = 'none';
        return;
    }

    document.getElementById('products-table').style.display = 'table';
    document.getElementById('no-results').style.display = 'none';

    products.forEach(product => {
        const row = document.createElement('tr');
        const statusBadge = getStatusBadge(product.status);
        const diffText = product.dix_vs_min || '-';
        const minPrice = product.min_competitor;

        // Helper to check if a specific price is the minimum
        const isBestPrice = (price) => {
            return minPrice && price === minPrice;
        };

        row.innerHTML = `
            <td><strong>${product.reference}</strong></td>
            <td class="price price-dix">${formatPrice(product.dix_price)}</td>
            <td class="price ${isBestPrice(product.competitor_prices.crenova) ? 'price-best-competitor' : ''}">${formatPrice(product.competitor_prices.crenova)}</td>
            <td class="price ${isBestPrice(product.competitor_prices.duga) ? 'price-best-competitor' : ''}">${formatPrice(product.competitor_prices.duga)}</td>
            <td class="price ${isBestPrice(product.competitor_prices.linksolutions) ? 'price-best-competitor' : ''}">${formatPrice(product.competitor_prices.linksolutions)}</td>
            <td class="price ${isBestPrice(product.competitor_prices.tabtel) ? 'price-best-competitor' : ''}">${formatPrice(product.competitor_prices.tabtel)}</td>
            <td class="price ${isBestPrice(product.competitor_prices.mies) ? 'price-best-competitor' : ''}">${formatPrice(product.competitor_prices.mies)}</td>
            <td class="price ${isBestPrice(product.competitor_prices.rightech) ? 'price-best-competitor' : ''}">${formatPrice(product.competitor_prices.rightech)}</td>
            <td class="price ${isBestPrice(product.competitor_prices.joutech) ? 'price-best-competitor' : ''}">${formatPrice(product.competitor_prices.joutech)}</td>
            <td class="${getDiffClass(diffText)}">${diffText}</td>
            <td>${statusBadge}</td>
        `;
        tbody.appendChild(row);
    });
}

// Navigation pagination
function nextPage() {
    if (currentPage < totalPages) {
        currentPage++;
        updatePagination();
        displayCurrentPage();
    }
}

function previousPage() {
    if (currentPage > 1) {
        currentPage--;
        updatePagination();
        displayCurrentPage();
    }
}

function goToPage(page) {
    currentPage = page;
    updatePagination();
    displayCurrentPage();
}

// Filtrer les produits
async function filterProducts(filter) {
    currentFilter = filter;

    document.querySelectorAll('.filter-buttons .btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.getElementById(`filter-${filter}`).classList.add('active');

    if (filter === 'cheaper') {
        filteredProducts = allProducts.filter(p => p.status === 'best');
    } else if (filter === 'expensive') {
        filteredProducts = allProducts.filter(p => p.status === 'expensive');
    } else {
        filteredProducts = allProducts;
    }

    currentPage = 1;
    updatePagination();
    displayCurrentPage();
}

// Recherche
let searchTimeout;
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('search-input').addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        const query = e.target.value.trim();

        if (query.length === 0) {
            filteredProducts = allProducts;
            currentPage = 1;
            updatePagination();
            displayCurrentPage();
            return;
        }

        searchTimeout = setTimeout(async () => {
            if (query.length < 2) return;

            try {
                const response = await fetch(`${API_BASE}/products/search?q=${encodeURIComponent(query)}`);
                const data = await response.json();

                if (data.success) {
                    filteredProducts = data.products;
                    currentPage = 1;
                    updatePagination();
                    displayCurrentPage();
                }
            } catch (error) {
                console.error('Erreur recherche:', error);
            }
        }, 300);
    });

    // Initialisation
    loadStats();
    loadProducts();
});

// Utilitaires
function formatPrice(price) {
    if (price === null || price === undefined) {
        return '<span class="price-null">N/A</span>';
    }
    return `${price.toFixed(2)} MAD`;
}

function getStatusBadge(status) {
    const badges = {
        'best': '<span class="badge badge-best">Meilleur Prix</span>',
        'competitive': '<span class="badge badge-competitive">Compétitif</span>',
        'expensive': '<span class="badge badge-expensive">Cher</span>'
    };
    return badges[status] || '';
}

function getDiffClass(diff) {
    if (!diff || diff === '-') return '';
    return diff.includes('+') ? 'diff-negative' : 'diff-positive';
}
