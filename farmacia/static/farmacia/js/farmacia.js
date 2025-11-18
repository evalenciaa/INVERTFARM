document.addEventListener('DOMContentLoaded', function() {
    // Efecto hover para las tarjetas
    const cards = document.querySelectorAll('.module-card');
    
    cards.forEach(card => {
        card.addEventListener('click', function() {
            // Aquí puedes añadir lógica para redireccionar
            console.log('Navegando a: ' + this.querySelector('h3').textContent);
        });
    });
});