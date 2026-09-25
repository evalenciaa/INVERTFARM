const exportModal = document.querySelector('.export-modal');
const exportBackdrop = document.querySelector('.modal-backdrop');

function setExportModal(open) {
    exportModal.classList.toggle('is-open', open);
    exportBackdrop.classList.toggle('is-open', open);
    exportModal.setAttribute('aria-hidden', String(!open));
}

document.querySelectorAll('[data-open-export]').forEach(button => button.addEventListener('click', () => setExportModal(true)));
document.querySelectorAll('[data-close-export]').forEach(button => button.addEventListener('click', () => setExportModal(false)));
document.addEventListener('keydown', event => { if (event.key === 'Escape') setExportModal(false); });
