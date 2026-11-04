# Proyecto-Inicial
Proyecto para ayudar a los deportistas a mejorar su alimentación, creado como nuestro proyecto inicial.

## Ejecutar localmente

```bash
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

Abre `http://127.0.0.1:8000/` para crear una cuenta. El registro lleva a la configuración de actividad y luego al inicio, donde puedes editar tu perfil y consultar el calendario de ejemplos de comidas.

## Flujo básico con Git

Trabaja en una rama propia y sincronízala antes de empezar:

```bash
git status
git pull
git switch -c nombre-de-mi-cambio
```

Después de probar tus cambios, guárdalos y súbelos:

```bash
git add .
git commit -m "Describe el cambio"
git push -u origin nombre-de-mi-cambio
```

Luego puedes abrir un pull request en GitHub para que el equipo revise e integre la rama.
