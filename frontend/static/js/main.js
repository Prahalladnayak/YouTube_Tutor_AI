// frontend/static/js/main.js

document.addEventListener('DOMContentLoaded', function() {
    // 1. Auto-fade Django messages/alerts after 5 seconds for cleaner interface
    const messages = document.querySelectorAll('.alert');
    messages.forEach(function(message) {
        setTimeout(function() {
            message.style.transition = 'opacity 0.5s ease';
            message.style.opacity = '0';
            setTimeout(function() {
                message.remove();
            }, 500);
        }, 5000);
    });

    // 2. Client-side double submission protection
    const forms = document.querySelectorAll('form');
    forms.forEach(function(form) {
        form.addEventListener('submit', function() {
            const submitButtons = form.querySelectorAll('button[type="submit"]');
            submitButtons.forEach(function(btn) {
                // Disable button in a microtask to allow form submission to occur
                setTimeout(function() {
                    btn.disabled = true;
                }, 50);
            });
        });
    });

    // 3. Clipboard copy utility (useful for copying RAG answers or learning paths)
    window.copyToClipboard = function(text, elementId) {
        navigator.clipboard.writeText(text).then(function() {
            const copyBtn = document.getElementById(elementId);
            if (copyBtn) {
                const originalContent = copyBtn.innerHTML;
                copyBtn.innerHTML = '<i class="bi bi-check-lg"></i> Copied!';
                copyBtn.style.pointerEvents = 'none';
                setTimeout(function() {
                    copyBtn.innerHTML = originalContent;
                    copyBtn.style.pointerEvents = 'auto';
                }, 2000);
            }
        }).catch(function(err) {
            console.error('Failed to copy: ', err);
        });
    };
});
