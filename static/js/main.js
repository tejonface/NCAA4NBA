// NBA Prospect Schedule - Main JavaScript

// Toggle info popover
function toggleInfo() {
    const overlay = document.getElementById('info-overlay');
    const popover = document.getElementById('info-popover');
    
    overlay.classList.toggle('active');
    popover.classList.toggle('active');
}

// Close popover when clicking outside
document.addEventListener('DOMContentLoaded', function() {
    const overlay = document.getElementById('info-overlay');
    if (overlay) {
        overlay.addEventListener('click', function() {
            toggleInfo();
        });
    }
});
