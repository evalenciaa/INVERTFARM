document.addEventListener('DOMContentLoaded', function () {
    const modulos = document.querySelectorAll('.modulo');
    const sidebar = document.querySelector('.sidebar');

    sidebar.classList.add('collapsed');

    modulos.forEach(modulo => {
        modulo.addEventListener('click', () => {
            const nombre = modulo.querySelector('span').innerText;
            console.log(`Ingresando a: ${nombre}`);
        });
    });
});
