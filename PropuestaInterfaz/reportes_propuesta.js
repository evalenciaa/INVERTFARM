const tabs = document.querySelectorAll('.tab-btn');
const panels = document.querySelectorAll('.tab-content');

tabs.forEach(tab => tab.addEventListener('click', () => {
    tabs.forEach(item => item.classList.remove('active'));
    panels.forEach(panel => panel.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById(tab.dataset.tab).classList.add('active');
}));
