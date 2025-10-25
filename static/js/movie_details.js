// In static/js/movie_details.js

// ===================================================================
// SECTION 1: DATA FETCHING FUNCTIONS
// These functions run when the page loads to fetch and display data.
// ===================================================================

/**
 * Fetches and displays the movie cast, making each member clickable.
 * @param {string} movieId - The ID of the movie.
 */
async function displayMovieCast(movieId) {
    const castContainer = document.getElementById('cast-container');
    if (!castContainer) return;

    try {
        const response = await fetch(`/api/movie/${movieId}/cast`);
        if (!response.ok) throw new Error(`API error: ${response.statusText}`);
        const credits = await response.json();
        const cast = credits.cast;

        castContainer.innerHTML = ''; // Clear the "Loading..." message

        cast.slice(0, 10).forEach(member => {
            const imageUrl = member.profile_path
                ? `https://image.tmdb.org/t/p/w200${member.profile_path}`
                : 'https://via.placeholder.com/200x300.png?text=No+Image';

            // Each cast member is wrapped in an <a> tag to link to their details page.
            const castElement = `
                <a href="/person/${member.id}" class="text-current no-underline">
                    <div class="flex flex-col items-center transform transition-transform hover:scale-105">
                        <img src="${imageUrl}" 
                             alt="${member.name}" 
                             class="cast-img w-24 h-24 md:w-32 md:h-32 rounded-full object-cover shadow-lg border-2 border-purple-500/50">
                        <p class="mt-3 font-bold text-white">${member.name}</p>
                        <p class="text-sm text-gray-400 text-center">${member.character}</p>
                    </div>
                </a>
            `;
            castContainer.innerHTML += castElement;
        });
    } catch (error) {
        console.error('Failed to fetch movie cast:', error);
        castContainer.innerHTML = '<p class="text-red-400">Could not load cast information.</p>';
    }
}

/**
 * Fetches and displays watch provider information for the movie.
 * @param {string} movieId - The ID of the movie.
 */
async function displayWatchProviders(movieId) {
    const container = document.getElementById('platform-container');
    if (!container) return;

    try {
        const response = await fetch(`/api/movie/${movieId}/platforms`);
        const providersIndia = await response.json();
        const uniqueProviders = new Map();

        const processProviderType = (providers) => {
            if (!providers) return;
            providers.forEach(provider => {
                if (!uniqueProviders.has(provider.provider_id)) {
                    uniqueProviders.set(provider.provider_id, {
                        name: provider.provider_name,
                        logo_path: provider.logo_path,
                    });
                }
            });
        };
        
        processProviderType(providersIndia.flatrate);
        processProviderType(providersIndia.rent);
        processProviderType(providersIndia.buy);

        container.innerHTML = '';
        
        if (uniqueProviders.size === 0) {
             container.innerHTML = '<p class="text-gray-400">Provider information not available.</p>';
             return;
        }

        uniqueProviders.forEach(provider => {
            const platformElement = `
                <div class="flex items-center gap-3 p-3 rounded-xl bg-purple-600/20 border-2 border-purple-500/30">
                    <img src="https://image.tmdb.org/t/p/w45${provider.logo_path}" alt="${provider.name}" class="w-8 h-8 rounded-md">
                    <span class="font-semibold text-lg">${provider.name}</span>
                </div>
            `;
            container.innerHTML += platformElement;
        });
    } catch (error) {
        container.innerHTML = '<p class="text-gray-400">Provider information not available.</p>';
    }
}


// ===================================================================
// SECTION 2: REVIEW HANDLING FUNCTIONS
// These functions manage submitting new reviews and updating the UI.
// ===================================================================

/**
 * Handles the click event of the "Submit Review" button for movies.
 */
async function submitReview() {
    const reviewTextArea = document.getElementById('reviewText');
    const messageDiv = document.getElementById('review-message');
    const ratingInput = document.querySelector('input[name="rating"]:checked');

    const reviewText = reviewTextArea.value.trim();
    const rating = ratingInput ? ratingInput.value : null;

    if (!rating) {
        messageDiv.innerHTML = `<p class="text-red-400">Please select a star rating.</p>`;
        return;
    }
    if (reviewText === '') {
        messageDiv.innerHTML = `<p class="text-red-400">Please write a review.</p>`;
        return;
    }

    const movieId = window.location.pathname.split('/').pop();

    try {
        const response = await fetch(`/movie/${movieId}/review`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ review_text: reviewText, rating: parseInt(rating) }),
        });
        const result = await response.json();

        if (response.ok) {
            messageDiv.innerHTML = `<p class="text-green-400 font-bold">${result.message}</p>`;
            reviewTextArea.value = '';
            if (ratingInput) ratingInput.checked = false;
            addNewReviewToDOM(result.review); 
        } else {
            messageDiv.innerHTML = `<p class="text-red-400">${result.error || 'An unknown error occurred.'}</p>`;
        }
    } catch (error) {
        console.error('Error submitting review:', error);
        messageDiv.innerHTML = `<p class="text-red-400">A network error occurred. Please try again.</p>`;
    }
}

/**
 * Creates the HTML for a new review and prepends it to the reviews container.
 * @param {object} review - The review object returned from the server.
 */
function addNewReviewToDOM(review) {
    const reviewsContainer = document.getElementById('reviews-container');
    const placeholder = reviewsContainer.querySelector('p');
    if (placeholder) {
        placeholder.remove();
    }

    let starsHTML = '';
    for (let i = 1; i <= 5; i++) {
        starsHTML += `<i class="ri-star-fill ${i <= review.rating ? 'text-yellow-400' : 'text-gray-600'}"></i>`;
    }

    const newReviewElement = document.createElement('div');
    newReviewElement.className = 'glass-panel p-4 flex items-start space-x-4 w-96 flex-shrink-0';
    newReviewElement.innerHTML = `
        <div class="flex-shrink-0">
            <div class="w-12 h-12 rounded-full bg-purple-800 flex items-center justify-center font-bold text-xl">
                ${review.author[0]}
            </div>
        </div>
        <div class="flex-1 min-w-0">
            <div class="flex items-center space-x-3">
                <span class="font-semibold">${review.author}</span>
                <span class="text-sm text-gray-400">via Flicksy</span>
            </div>
            <div class="flex text-yellow-400 mt-1">${starsHTML}</div>
            <p class="text-gray-300 mt-2 text-sm leading-relaxed break-words">${review.content}</p>
        </div>
    `;
    reviewsContainer.prepend(newReviewElement);
}


// ===================================================================
// SECTION 3: UI INTERACTION FUNCTION
// This function handles interactive UI elements like scrollers.
// ===================================================================

/**
 * Sets up arrow button controls for the horizontal review scroller.
 */
function setupReviewScroller() {
    const reviewsContainer = document.getElementById('reviews-container');
    const scrollLeftBtn = document.getElementById('scroll-left-btn');
    const scrollRightBtn = document.getElementById('scroll-right-btn');

    if (!reviewsContainer || !scrollLeftBtn || !scrollRightBtn) {
        return;
    }

    const scrollAmount = 400;

    const updateArrowStates = () => {
        scrollLeftBtn.disabled = reviewsContainer.scrollLeft < 1;
        const maxScrollLeft = reviewsContainer.scrollWidth - reviewsContainer.clientWidth;
        scrollRightBtn.disabled = reviewsContainer.scrollLeft >= (maxScrollLeft - 1);
    };

    scrollRightBtn.addEventListener('click', () => {
        reviewsContainer.scrollBy({ left: scrollAmount, behavior: 'smooth' });
    });
    
    scrollLeftBtn.addEventListener('click', () => {
        reviewsContainer.scrollBy({ left: -scrollAmount, behavior: 'smooth' });
    });

    reviewsContainer.addEventListener('scroll', updateArrowStates);
    setTimeout(updateArrowStates, 500); 
}


// ===================================================================
// SECTION 4: MAIN SETUP SCRIPT (The "Brain")
// This runs when the page is loaded and calls all the other functions.
// ===================================================================

document.addEventListener('DOMContentLoaded', () => {
    const movieId = window.location.pathname.split('/').pop();

    if (movieId && !isNaN(movieId)) {
        // 1. Fetch and display all dynamic content for the page.
        displayMovieCast(movieId);
        displayWatchProviders(movieId);
        
        // 2. Set up the interactive horizontal review scroller.
        setupReviewScroller();
        
        // 3. Add the event listener for the review submit button.
        const submitBtn = document.getElementById('submitReviewBtn');
        if (submitBtn) {
            submitBtn.addEventListener('click', submitReview);
        }
    } else {
        console.error("Could not find a valid Movie ID in the URL.");
    }
});
