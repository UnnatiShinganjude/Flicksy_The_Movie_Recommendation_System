// In static/js/main.js

document.addEventListener('DOMContentLoaded', () => {

    // --- Carousel Logic ---
    const carousel = document.querySelector('.carousel-items');
    if (carousel) {
        const items = document.querySelectorAll('.carousel-item');
        const indicators = document.querySelectorAll('.carousel-indicators button');
        const totalItems = items.length;
        const prevBtn = document.getElementById('prevBtn');
        const nextBtn = document.getElementById('nextBtn');
        let currentIndex = 0;

        function updateCarousel() {
            if (totalItems > 0) {
                const offset = -currentIndex * 100;
                carousel.style.transform = `translateX(${offset}%)`;
                indicators.forEach((dot, idx) => {
                    dot.classList.toggle('bg-white', idx === currentIndex);
                    dot.classList.toggle('bg-gray-400', idx !== currentIndex);
                });
            }
        }
        
        if (totalItems > 0 && prevBtn && nextBtn) {
            prevBtn.addEventListener('click', () => {
                currentIndex = (currentIndex - 1 + totalItems) % totalItems;
                updateCarousel();
            });

            nextBtn.addEventListener('click', () => {
                currentIndex = (currentIndex + 1) % totalItems;
                updateCarousel();
            });

            indicators.forEach((dot) => {
                dot.addEventListener('click', () => {
                    currentIndex = parseInt(dot.dataset.index);
                    updateCarousel();
                });
            });

            setInterval(() => {
                if (nextBtn) {
                    nextBtn.click();
                }
            }, 5000);

            updateCarousel();
        }
    }

    // --- Search Logic ---
    const searchInput = document.querySelector('.search-input');
    const resultsBox = document.getElementById('search-results');

    if (searchInput && resultsBox) {
        searchInput.addEventListener('input', function() {
            let query = this.value.trim();

            if (query.length < 2) {
                resultsBox.classList.add('hidden');
                resultsBox.innerHTML = '';
                return;
            }

            fetch(`/search?q=${encodeURIComponent(query)}`)
                .then(res => res.json())
                .then(data => {
                    resultsBox.innerHTML = '';

                    if (data.movies.length === 0 && data.tv_shows.length === 0 && data.people.length === 0) {
                        resultsBox.innerHTML = `<p class="p-4 text-gray-400">No results found</p>`;
                        resultsBox.classList.remove('hidden');
                        return;
                    }

                    if (data.movies.length > 0) {
                        resultsBox.innerHTML += `<h3 class="text-gray-300 font-bold px-4 pt-2 text-sm border-b border-gray-700 pb-2">Movies</h3>`;
                        data.movies.slice(0, 5).forEach(movie => {
                            resultsBox.appendChild(createResultItem(
                                movie.title, 
                                movie.poster_path,
                                `/movie/${movie.id}`
                            ));
                        });
                    }

                    if (data.tv_shows.length > 0) {
                         resultsBox.innerHTML += `<h3 class="text-gray-300 font-bold px-4 pt-2 text-sm border-b border-gray-700 pb-2">TV Shows</h3>`;
                         data.tv_shows.slice(0,5).forEach(tv => {
                            resultsBox.appendChild(createResultItem(
                                tv.name,
                                tv.poster_path,
                                `/tv/${tv.id}`
                            ));
                         });
                    }

                    if (data.people.length > 0) {
                        resultsBox.innerHTML += `<h3 class="text-gray-300 font-bold px-4 pt-2 text-sm border-b border-gray-700 pb-2">Actors</h3>`;
                        data.people.slice(0, 5).forEach(person => {
                            resultsBox.appendChild(createResultItem(
                                person.name,
                                person.profile_path,
                                `/person/${person.id}`
                            ));
                        });
                    }

                    resultsBox.classList.remove('hidden');
                })
                .catch(err => {
                    console.error("Fetch Error:", err);
                    resultsBox.classList.add('hidden');
                });
        });
    }

    function createResultItem(name, imgPath, url) {
        const imgUrl = imgPath ? `https://image.tmdb.org/t/p/w92${imgPath}` : '/static/images/no-image.jpg';
        
        const link = document.createElement('a');
        link.href = url;
        link.className = "flex items-center p-2 hover:bg-gray-800 cursor-pointer";
        link.innerHTML = `
            <img src="${imgUrl}" class="w-10 h-14 object-cover rounded mr-3 flex-shrink-0" alt="${name}">
            <span class="text-white text-sm">${name}</span>
        `;
        return link;
    }

    document.addEventListener('click', function(e) {
        if (resultsBox && !e.target.closest('.relative')) {
            resultsBox.classList.add('hidden');
        }
    });

    // ===================================================================
    // === NEW: WATCHLIST LOGIC (Now correctly placed INSIDE the listener) ===
    // ===================================================================
    const allWatchlistButtons = document.querySelectorAll('.add-to-watchlist');

    allWatchlistButtons.forEach(button => {
        button.addEventListener('click', function() {
            const tmdbId = this.dataset.tmdbId;
            const mediaType = this.dataset.mediaType;
            const buttonContent = this.querySelector('.button-content, i');

            fetch('/api/watchlist/add', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    tmdb_id: parseInt(tmdbId),
                    media_type: mediaType
                }),
            })
            .then(response => {
                if (response.status === 401) {
                    window.location.href = '/login';
                    return;
                }
                return response.json();
            })
            .then(data => {
                if (data && (data.success || data.message.includes("already in watchlist"))) {
                    this.disabled = true;
                    this.style.cursor = 'not-allowed';

                    if (buttonContent) {
                        if (buttonContent.tagName === 'DIV') {
                           buttonContent.innerHTML = `
                                <div class="w-5 h-5 flex items-center justify-center mr-2">
                                    <i class="ri-check-line"></i>
                                </div>
                                <span>Added</span>`;
                        } else {
                           buttonContent.classList.remove('ri-add-line');
                           buttonContent.classList.add('ri-check-line');
                        }
                    }
                } else if (data) {
                    alert(data.error || 'An unknown error occurred.');
                }
            })
            .catch(error => {
                console.error('Error adding to watchlist:', error);
                alert('Could not add to watchlist. Please try again.');
            });
        });
    });

}); 