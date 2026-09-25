const uploadArea = document.getElementById('upload-area');
const fileInput = document.getElementById('archivo-excel');
const fileInfo = document.getElementById('file-info');
const fileName = document.getElementById('file-name');
const fileSize = document.getElementById('file-size');

function mostrarArchivo(file) {
    if (!file) return;
    fileName.textContent = file.name;
    fileSize.textContent = `${(file.size / 1024 / 1024).toFixed(2)} MB · listo para procesar`;
    uploadArea.hidden = true;
    fileInfo.hidden = false;
}

document.getElementById('btn-seleccionar').addEventListener('click', event => { event.stopPropagation(); fileInput.click(); });
uploadArea.addEventListener('click', () => fileInput.click());
uploadArea.addEventListener('dragover', event => { event.preventDefault(); uploadArea.classList.add('drag-over'); });
uploadArea.addEventListener('dragleave', () => uploadArea.classList.remove('drag-over'));
uploadArea.addEventListener('drop', event => { event.preventDefault(); uploadArea.classList.remove('drag-over'); mostrarArchivo(event.dataTransfer.files[0]); });
fileInput.addEventListener('change', () => mostrarArchivo(fileInput.files[0]));
document.getElementById('btn-remove').addEventListener('click', () => { fileInput.value = ''; fileInfo.hidden = true; uploadArea.hidden = false; });
document.getElementById('form-carga-masiva').addEventListener('submit', event => event.preventDefault());
