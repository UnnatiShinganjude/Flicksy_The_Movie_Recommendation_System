
// static/js/watchlist.js

document.addEventListener('DOMContentLoaded', () => {
    
    // --- Logic for the main Watchlist Page ---
    const watchlistContainer = document.getElementById('watchlist-container');
    if (watchlistContainer) {
        fetchWatchlist();
    }

    // --- Logic for Add/Remove Buttons on ANY page ---
    // Use event delegation to handle clicks on buttons that might not exist on page load.
    document.body.addEventListener('click', function(event) {
        const target = event.target.closest('.watchlist-btn');
        if (!target) return;

        const movieId = target.dataset.movieId;
        const tvId = target.dataset.tvId;
        const action = target.dataset.action; // 'add' or 'remove'

        if (action === 'add') {
            addToWatchlist(movieId, tvId, target);
        } else if (action === 'remove') {
            removeFromWatchlist(movieId, tvId, target);
        }
    });
});

/**
 * Fetches the user's watchlist from the backend and displays it.
 */
async function fetchWatchlist() {
    const container = document.getElementById('watchlist-container');
    try {
        const response = await fetch('/api/watchlist');
        if (!response.ok) throw new Error('Could not fetch watchlist');
        
        const watchlistItems = await response.json();

        if (watchlistItems.length === 0) {
            container.innerHTML = `<p class="text-center text-gray-400 text-lg col-span-full">Your watchlist is empty. Add some movies and TV shows!</p>`;
            return;
        }

        container.innerHTML = ''; // Clear the loading/empty message
        watchlistItems.forEach(item => {
            const isMovie = item.media_type === 'movie';
            const title = isMovie ? item.title : item.name;
            const overview = item.overview || 'No overview available.';
            const releaseYear = isMovie 
                ? (item.release_date ? item.release_date.split('-')[0] : 'N/A')
                : (item.first_air_date ? item.first_air_date.split('-')[0] : 'N/A');

            const card = `
                <div class="watchlist-item" id="item-${item.media_type}-${item.tmdb_id}">
                    <a href="/${item.media_type}/${item.tmdb_id}">
                        <img src="https://image.tmdb.org/t/p/w500${item.poster_path}" class="watchlist-poster" alt="Poster for ${title}">
                    </a>
                    <div class="watchlist-overlay">
                        <div>
                            <div class="overlay-title">${title} (${releaseYear})</div>
                            <div class="star-rating">
                                <i class="ri-star-fill text-yellow-400"></i> ${item.vote_average.toFixed(1)}
                            </div>
                            <div class="overlay-desc">${overview.substring(0, 120)}...</div>
                        </div>
                        <div class="overlay-buttons">
                            <a href="/${item.media_type}/${item.tmdb_id}" class="watch-btn">Details</a>
                            <button class="remove-btn watchlist-btn" data-action="remove" data-${isMovie ? 'movie-id' : 'tv-id'}="${item.tmdb_id}">
                                <i class="ri-delete-bin-line"></i> Remove
                            </button>
                        </div>
                    </div>
                </div>
            `;
            container.innerHTML += card;
        });
    } catch (error) {
        console.error('Error fetching watchlist:', error);
        container.innerHTML = '<p class="text-center text-red-400">Failed to load your watchlist. Please try again later.</p>';
    }
}

/**
 * Sends a request to the backend to add an item to the watchlist.
 * @param {string|null} movieId - The TMDB ID of the movie.
 * @param {string|null} tvId - The TMDB ID of the TV show.
 * @param {HTMLElement} button - The button that was clicked.
 */
async function addToWatchlist(movieId, tvId, button) {
    const mediaType = movieId ? 'movie' : 'tv';
    const tmdbId = movieId || tvId;

    try {
        const response = await fetch('/api/watchlist/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ media_type: mediaType, tmdb_id: tmdbId }),
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || 'Failed to add to watchlist');
        
        // --- Visual Feedback: Update the button ---
        button.innerHTML = `<i class="ri-check-line"></i> Added`;
        button.classList.remove('bg-transparent');
        button.classList.add('bg-green-500');
        button.dataset.action = 'remove'; // Change action to 'remove'
        
    } catch (error) {
        console.error('Error adding to watchlist:', error);
        alert(error.message); // Show an alert to the user
    }
}

/**
 * Sends a request to the backend to remove an item from the watchlist.
 * @param {string|null} movieId - The TMDB ID of the movie.
 * @param {string|null} tvId - The TMDB ID of the TV show.
 * @param {HTMLElement} button - The button that was clicked.
 */
async function removeFromWatchlist(movieId, tvId, button) {
    const mediaType = movieId ? 'movie' : 'tv';
    const tmdbId = movieId || tvId;

    try {
        const response = await fetch('/api/watchlist/remove', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ media_type: mediaType, tmdb_id: tmdbId }),
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || 'Failed to remove from watchlist');

        // --- Visual Feedback ---
        // If we are on the watchlist page, remove the card directly.
        const cardToRemove = document.getElementById(`item-${mediaType}-${tmdbId}`);
        if (cardToRemove) {
            cardToRemove.style.transition = 'transform 0.3s ease, opacity 0.3s ease';
            cardToRemove.style.transform = 'scale(0.9)';
            cardToRemove.style.opacity = '0';
            setTimeout(() => cardToRemove.remove(), 300);
        } else {
            // If on a details page, revert the button back to the "Add" state.
            button.innerHTML = `<i class="ri-bookmark-line"></i> Watchlist`;
            button.classList.remove('bg-green-500');
            button.classList.add('bg-transparent');
            button.dataset.action = 'add';
        }

    } catch (error) {
        console.error('Error removing from watchlist:', error);
        alert(error.message);
    }
}