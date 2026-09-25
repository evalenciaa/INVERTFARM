const backdrop = document.querySelector('.modal-backdrop');
const exportModal = document.querySelector('.export-modal');
const qrModal = document.querySelector('.qr-modal');

function setModal(modal, open) {
    modal.classList.toggle('is-open', open);
    backdrop.classList.toggle('is-open', open);
    modal.setAttribute('aria-hidden', String(!open));
}

document.querySelector('[data-open-export]').addEventListener('click', () => setModal(exportModal, true));
document.querySelector('[data-open-qr]').addEventListener('click', () => setModal(qrModal, true));
document.querySelectorAll('[data-close-modal]').forEach(button => button.addEventListener('click', () => {
    setModal(exportModal, false);
    setModal(qrModal, false);
}));
document.addEventListener('keydown', event => {
    if (event.key === 'Escape') {
        setModal(exportModal, false);
        setModal(qrModal, false);
    }
});
