document.addEventListener('DOMContentLoaded', () => {
    let pyHandler; // This will hold the Python 'handler' object
    const searchForm = document.getElementById('search-form');
    const searchInput = document.getElementById('search-input');
    const clockEl = document.getElementById('clock');
    
    // --- 1. Initialize the QWebChannel ---
    new QWebChannel(qt.webChannelTransport, (channel) => {
        // 'handler' is the name we registered in main_window.py
        pyHandler = channel.objects.handler;
        console.log("Home Page: WebChannel connection established.");
        
        if (!pyHandler) {
            console.error("Failed to connect to Python handler object.");
            searchInput.placeholder = "Search (disabled)";
            searchInput.disabled = true;
        }
    });

    // --- 2. Search Form Logic ---
    searchForm.addEventListener('submit', (e) => {
        e.preventDefault(); // Stop the form from submitting normally
        const term = searchInput.value.trim();
        
        if (term && pyHandler) {
            try {
                // This calls the '@pyqtSlot(str) def performSearch(self, term)'
                // in our WebChannelHandler (main_window.py)
                pyHandler.performSearch(term);
            } catch (err) {
                console.error("Error calling performSearch:", err);
                alert("Could not perform search. Connection to app lost.");
            }
        }
    });
    
    // --- 3. Live Clock Logic ---
    function updateClock() {
        const now = new Date();
        let hours = now.getHours();
        const minutes = now.getMinutes().toString().padStart(2, '0');
        const ampm = hours >= 12 ? 'PM' : 'AM';
        
        hours = hours % 12;
        hours = hours ? hours : 12; // '0' hour should be '12'
        
        clockEl.textContent = `${hours}:${minutes} ${ampm}`;
    }
    
    updateClock();
    setInterval(updateClock, 1000); // Update every second
});