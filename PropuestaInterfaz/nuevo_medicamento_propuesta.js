const antibioticoSwitch = document.getElementById('es-antibiotico');
const datosAntibiotico = document.getElementById('datos-antibiotico');
const form = document.getElementById('form-medicamento');

function actualizarDatosAntibiotico() {
    datosAntibiotico.classList.toggle('is-visible', antibioticoSwitch.checked);
}

antibioticoSwitch.addEventListener('change', actualizarDatosAntibiotico);
document.getElementById('limpiar-formulario').addEventListener('click', () => {
    form.reset();
    actualizarDatosAntibiotico();
    document.getElementById('clave').focus();
});
form.addEventListener('submit', event => event.preventDefault());
