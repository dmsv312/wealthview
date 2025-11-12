/******************* VALIDATE: PASSWORD *******************/
function check_password(p, min_length = 6) {
    if (p.length < min_length) return "Пароль должен состоять минимум из " + min_length + " символов.";
    // if (p.match(/^\d+$/)) return "Пароль не может быть полностью цифровым.";
    // if (p.match(/^((test)*(123)*)*'$/)) return "Пароль не может быть часто используемым паролем";
    // if (p.count(username)) return "Пароль не должен быть слишком похож на вашу другую личную информацию.";
    return "Пароль валиден";
}

function check_confirm(p1, p2) {
    if (p1 === "" && p2 === "") {
        return "";
    } else if (p1 === p2) {
        return "Пароли совпадают";
    } else {
        return "Пароли не совпадают";
    }
}

function validate_password() {
    //Store the field objects into variables ...
    let password = $('#pass1');
    let confirm = $('#pass2');
    let message_1 = $('#msg_1');
    let message_2 = $('#msg_2');
    //Set the colors we will be using ...
    const good_color = "#66cc66";
    const bad_color = "#ff6666";
    // Get results of check
    let result_1 = check_password(password.val());
    let result_2 = check_confirm(password.val(), confirm.val());
    // Compute valid
    let is_password_valid = result_1 === "Пароль валиден";
    let are_passwords_matching = result_2 === "Пароли совпадают";
    set_status(password, is_password_valid);
    set_status(confirm, are_passwords_matching);
    // Show message
    if (is_password_valid) {
        message_1.addClass("text-muted");
    }
    else {
        message_1.removeClass("text-muted");
        message_1.css({'color' : '#ff6666'});
    }
    if (are_passwords_matching) {
        message_2.addClass("text-muted");
    }
    else {
        message_2.removeClass("text-muted");
        message_2.css({'color' : '#ff6666'});
    }
    message_1.html(result_1);
    message_2.html(result_2);
    return is_password_valid && are_passwords_matching;
}

function validate_password_change() {
    //Store the field objects into variables ...
    let password = $('#change_password1');
    let confirm = $('#change_password2');
    let message_1 = $('#change_msg_1');
    let message_2 = $('#change_msg_2');
    //Set the colors we will be using ...
    const good_color = "#66cc66";
    const bad_color = "#ff6666";
    // Get results of check
    let result_1 = check_password(password.val());
    let result_2 = check_confirm(password.val(), confirm.val());
    // Compute valid
    let is_password_valid = result_1 === "Пароль валиден";
    let are_passwords_matching = result_2 === "Пароли совпадают";
    set_status(password, is_password_valid);
    set_status(confirm, are_passwords_matching);
    // Show message
    if (is_password_valid) {
        message_1.addClass("text-muted");
    }
    else {
        message_1.removeClass("text-muted");
        message_1.css({'color' : '#ff6666'});
    }
    if (are_passwords_matching) {
        message_2.addClass("text-muted");
    }
    else {
        message_2.removeClass("text-muted");
        message_2.css({'color' : '#ff6666'});
    }
    message_1.html(result_1);
    message_2.html(result_2);
    return is_password_valid && are_passwords_matching;
}

/******************* VALIDATE: USERNAME, EMAIL ************/
function validate_login(login_type, login_label, label_true = "занят", label_false = "свободен", label_null = "не валиден") {
    let is_valid = false;
    let login = $("#" + login_type);
    let data = {};
    data[login_type] = login.val();
    let msg_element = $("#msg_" + login_type);

    $.ajax({
        async: false,
        type: "GET",
        url: '/ajax/is_exist_' + login_type + "/",
        data: data,
        contentType: 'json',
        success: function (data) {
            // Process message
            let message = "";
            if (data.is_taken == null) {
                message = label_null;
            } else if (data.is_taken) {
                message = label_true;
            } else {
                message = label_false;
                is_valid = true; // login is valid!
            }
            // Show message
            msg_element.html(login_label + " " + message);
        }
    });
    if (is_valid) {
        msg_element.addClass("text-muted");
    }
    else {
        msg_element.removeClass("text-muted");
        msg_element.css({'color' : '#ff6666'});
    }
    set_status(login, is_valid);
    return is_valid;
}

function validate_login_forget_password() {
    let is_valid = false;
    let login = $("#forget_password_email");
    login.css({'color' : '#000'});
    let data = {};
    data["email"] = login.val();

    $.ajax({
        async: false,
        type: "GET",
        url: '/ajax/is_exist_email/',
        data: data,
        contentType: 'json',
        success: function (data) {
            if (data.is_taken) {
                is_valid = true;
                login.css({'color' : '#28a745'}); //email is exist
            } else {
                is_valid = false;
                login.css({'color' : '#ff6666'});
            }
        }
    });
    return is_valid;
}

/******************* BASE BLOCK: VALIDATE FORM ************/
$(function () {
    let is_valid_username = false;
    let are_valid_passwords = false;
    let is_valid_email = false;

    watch_username();
    watch_password();
    watch_email();
    watch_password_change();
    watch_forget_password_email();

    function watch_username() {
        $("#username").change(function () {
            is_valid_username = validate_login("username", "Имя пользователя", "занято", "свободно", "не валидно");
        });
    }

    function watch_password() {
        $("#pass1").change(function () {
            are_valid_passwords = validate_password();
        });
        $("#pass2").change(function () {
            are_valid_passwords = validate_password();
        });
    }

    function watch_password_change() {
        $("#change_password1").change(function () {
            are_valid_passwords = validate_password_change();
        });
        $("#change_password2").change(function () {
            are_valid_passwords = validate_password_change();
        });
    }

    function watch_email() {
        $("#email").change(function () {
            is_valid_email = validate_login("email", "Email");
        });
    }

    function watch_forget_password_email() {
        $("#forget_password_email").change(function () {
            is_valid_email = validate_login_forget_password();
        });
    }

});

function valid_registration_form() {
        let is_valid_username = validate_login("username", "Имя пользователя", "занято", "свободно", "не валидно");
        let are_valid_passwords = validate_password();
        let is_valid_email = validate_login("email", "Email");

        if (are_valid_passwords && is_valid_username && is_valid_email)
            return true;
        else
            return false;
    }

function valid_change_password_form() {
    return validate_password_change();
}

function valid_forget_password_form() {
    return validate_login_forget_password();
}