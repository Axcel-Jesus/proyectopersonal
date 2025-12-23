let nombre = document.getElementById("nombre");
let correo = document.getElementById("correo");
let contraseña = document.getElementById("contraseña");
let pais = document.getElementById("pais");
let edad = document.getElementById("edad");

let btnRegistrarse = document.getElementById("btn-login");
let btnIniciarSesion = document.getElementById("btnIniciarSesion");

btnRegistrarse.addEventListener("click", function() {
    if (nombre.value == "") {
        alert("El nombre es obligatorio");  
    } else if (correo.value == "") {
        alert("El correo es obligatorio");
    } else if (contraseña.value == "") {
        alert("La contraseña es obligatorio");
    } else if (pais.value == "") {
        alert("El pais es obligatorio");
    } else if (edad.value == "") {
        alert("La edad es obligatorio");
    } else {
        alert("Registro exitoso");
        window.location.href = "iniciarsecion.html";
    }
});

let iniciarCorreo = document.getElementById("IniciarCorreo");
let iniciarContraseña = document.getElementById("IniciarContraseña");

btn-singin.addEventListener("click", function() {
    if (iniciarCorreo.value == "") {
        alert("El correo es obligatorio");
    } else if (iniciarContraseña.value == "") {
        alert("La contraseña es obligatorio");
    } else if (iniciarContraseña.value.equals(contraseña.value) == false) {
        alert("Las contraseñas no coinciden");
    }
    else {
        alert("Iniciar sesión exitoso");
    }
});

