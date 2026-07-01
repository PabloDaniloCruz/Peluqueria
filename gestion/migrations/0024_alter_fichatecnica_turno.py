# Generated manually — make FichaTecnica.turno NOT NULL, change on_delete to CASCADE

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0023_constraints_unique_venta_comision_consumo_horario'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fichatecnica',
            name='turno',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='fichas_tecnicas',
                to='gestion.turno',
                verbose_name='turno asociado',
                help_text='Turno en el que se generó esta ficha',
            ),
        ),
    ]
