document.addEventListener('DOMContentLoaded', function() {
    // Las animaciones de las tarjetas se mantienen en CSS.
    const cards = document.querySelectorAll('.module-card');
    
    cards.forEach(card => {
        card.addEventListener('click', function() {
            const title = this.querySelector('h2, h3');
            if (title) console.log('Navegando a: ' + title.textContent);
        });
    });
});
