from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User

from ..models import Profesional, HabilidadProfesional
from ..forms import ProfesionalForm


def es_admin(user):
    return user.is_superuser


@user_passes_test(es_admin)
def lista_profesionales(request):
    profesionales = Profesional.objects.filter(activo=True)
    return render(request, 'gestion/profesionales.html', {'profesionales': profesionales})


@user_passes_test(es_admin)
def crear_profesional(request):
    if request.method == 'POST':
        form = ProfesionalForm(request.POST)
        if form.is_valid():
            prof = form.save(commit=False)
            
            # Gestión del Usuario
            crear_usuario = form.cleaned_data.get('crear_usuario')
            if crear_usuario:
                username = form.cleaned_data.get('username')
                password = form.cleaned_data.get('password')
                user = User.objects.create_user(username=username, password=password)
                user.is_staff = True
                user.save()
                prof.usuario = user
            
            prof.save()

            # Guardar habilidades (M2M custom)
            servicios_seleccionados = form.cleaned_data['habilidades_list']
            for s in servicios_seleccionados:
                HabilidadProfesional.objects.create(profesional=prof, servicio=s)
            messages.success(request, 'Profesional creado correctamente.')
            return redirect('lista_profesionales')
    else:
        form = ProfesionalForm()
    return render(request, 'gestion/profesional_form.html', {'form': form, 'titulo': 'Nuevo Profesional'})


@user_passes_test(es_admin)
def editar_profesional(request, prof_id):
    prof = get_object_or_404(Profesional, id=prof_id)
    if request.method == 'POST':
        form = ProfesionalForm(request.POST, instance=prof)
        if form.is_valid():
            prof = form.save(commit=False)
            
            # Gestión del Usuario
            crear_usuario = form.cleaned_data.get('crear_usuario')
            if crear_usuario:
                username = form.cleaned_data.get('username')
                # Usamos strip() para ignorar espacios en blanco accidentales
                password = form.cleaned_data.get('password', '').strip()
                
                if prof.usuario:
                    # SOLO cambiamos la contraseña si el campo NO está vacío
                    if password:
                        prof.usuario.set_password(password)
                        prof.usuario.save()
                        messages.info(request, f"Se ha actualizado la contraseña de acceso para {username}.")
                else:
                    # Crear usuario nuevo (aquí el form ya validó que tenga password)
                    user = User.objects.create_user(username=username, password=password)
                    user.is_staff = True
                    user.save()
                    prof.usuario = user
            
            prof.save()

            # Actualizar habilidades
            servicios_seleccionados = form.cleaned_data['habilidades_list']
            HabilidadProfesional.objects.filter(profesional=prof).delete()
            for s in servicios_seleccionados:
                HabilidadProfesional.objects.create(profesional=prof, servicio=s)
            messages.success(request, 'Profesional actualizado correctamente.')
            return redirect('lista_profesionales')
    else:
        form = ProfesionalForm(instance=prof)
    return render(request, 'gestion/profesional_form.html', {'form': form, 'titulo': 'Editar Profesional'})


@user_passes_test(es_admin)
def eliminar_profesional(request, prof_id):
    prof = get_object_or_404(Profesional, id=prof_id)
    prof.activo = False
    prof.save()
    messages.success(request, f'Profesional {prof.nombre} {prof.apellido} dado de baja.')
    return redirect('lista_profesionales')
