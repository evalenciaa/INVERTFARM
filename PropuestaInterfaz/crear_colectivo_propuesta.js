document.addEventListener('DOMContentLoaded', () => {
    const cards = [...document.querySelectorAll('.tipo-card')];

    cards.forEach((card) => {
        card.addEventListener('click', () => {
            cards.forEach((item) => {
                item.classList.remove('selected');
                item.querySelector('input[type="radio"]').checked = false;
            });

            card.classList.add('selected');
            card.querySelector('input[type="radio"]').checked = true;
        });
    });
});
