var fprm = document.getElementById('sd_form');
var preloader = document.getElementById('page-preloader');

fprm.addEventListener('submit', function() {
    preloader.classList.remove("hide")
});