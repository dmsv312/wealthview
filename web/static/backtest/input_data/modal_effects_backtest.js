let div_overlay = document.getElementById("overlay");
let modal_windows = document.getElementsByClassName("modal_block");

div_overlay.addEventListener("click", function(){
    div_overlay.style.display = "none";
    //проходимся по модальным окнам параметров
    for (let i=0; i < modal_windows.length; i++){
        if (modal_windows[i].style.display === "block")
            modal_windows[i].style.display = "none";
    }
    //проверяем окна авторизации и регистрации
    if (document.getElementById("login_block").style.right !==""){
        document.getElementById("login_block").style.right ="";
    }
    if (document.getElementById("register_block").style.right !==""){
        document.getElementById("register_block").style.right ="";
    }
});
//modal_add_active