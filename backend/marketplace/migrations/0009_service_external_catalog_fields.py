from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('marketplace', '0008_accountitem_description'),
    ]

    operations = [
        migrations.AddField(
            model_name='service',
            name='listing_type',
            field=models.CharField(choices=[('service', 'Service'), ('product', 'Product')], db_index=True, default='service', max_length=20),
        ),
        migrations.AddField(
            model_name='service',
            name='external_url',
            field=models.URLField(blank=True, default='', max_length=500),
        ),
        migrations.AddField(
            model_name='service',
            name='image_url',
            field=models.URLField(blank=True, default='', max_length=1000),
        ),
    ]
