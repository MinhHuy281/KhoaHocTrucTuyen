from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0007_coursecomment_lessoncomment'),
    ]

    operations = [
        migrations.AddField(
            model_name='enrollment',
            name='paid_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]