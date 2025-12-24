document.addEventListener('DOMContentLoaded', () => {
    const form = document.querySelector('form.login-form');
    if (!form) return;

    // Registration form handler (page: registrarse.html)
    const nombreEl = document.getElementById('nombre');
    if (nombreEl) {
        form.addEventListener('submit', async (ev) => {
            ev.preventDefault();
            const correo = document.getElementById('correo');
            const pass = document.getElementById('contraseña');
            const pais = document.getElementById('pais');
            const edad = document.getElementById('edad');
            if (!nombreEl.value) return alert('El nombre es obligatorio');
            if (!correo || !correo.value) return alert('El correo es obligatorio');
            if (!pass || !pass.value) return alert('La contraseña es obligatoria');
            if (!pais || !pais.value) return alert('El país es obligatorio');
            if (!edad || !edad.value) return alert('La edad es obligatoria');
            try {
                const resp = await fetch('/api/clientes', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ nombre: nombreEl.value, correo: correo.value, contrasena: pass.value, pais: pais.value, edad: Number(edad.value) })
                });
                if (resp.ok) {
                    alert('Registro exitoso');
                    window.location.href = '/iniciarsecion';
                } else {
                    const txt = await resp.text();
                    alert('Error: ' + txt);
                }
            } catch (e) {
                alert('Error de conexión: ' + e.message);
            }
        });
        return;
    }

    // Login form handler (page: iniciarsecion.html)
    const correoIn = document.getElementById('iniciarCorreo');
    const passIn = document.getElementById('Iniciar');
    if (correoIn && passIn) {
        form.addEventListener('submit', async (ev) => {
            ev.preventDefault();
            const correoVal = correoIn.value.trim();
            const passVal = passIn.value;
            if (!correoVal || !passVal) return alert('Correo y contraseña son requeridos');
            try {
                const resp = await fetch('/api/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ correo: correoVal, contrasena: passVal })
                });
                if (resp.status === 404) { alert('Cuenta no existe'); return; }
                if (resp.status === 401) { alert('Contraseña incorrecta'); return; }
                if (!resp.ok) { const txt = await resp.text(); alert('Error: ' + txt); return; }
                const data = await resp.json();
                try { localStorage.setItem('usuario_nombre', data.nombre || 'visitante'); } catch (e) {}
                alert('Inicio de sesión exitoso');
                window.location.href = '/inicio';
            } catch (e) {
                alert('Error de conexión: ' + e.message);
            }
        });
    }
});

