/******************* STATUS SHOW ***************************/
function set_success_status(element) {
    element.removeClass("text-danger").addClass("text-success");
}

function set_error_status(element) {
    element.removeClass("text-success").addClass("text-danger");
}

function set_status(element, status_success) {
    if (status_success) {
        set_success_status(element);
    } else {
        set_error_status(element)
    }
}

function set_accessibility(element, state) {
    if (state) {
        // alert("ENABLED");
        element.removeClass("disabled");
        element.prop('disabled', false);
    } else {
        // alert("DISABLED");
        element.addClass("disabled");
        element.prop('disabled', true);
    }
}

function set_validity(element, state, message_if_invalid) {
    if (state) {
        element.setCustomValidity("");
    } else {
        element.setCustomValidity(message_if_invalid);
    }
}