# Generated migration for adding discount fields and UserSearchHistory model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('hotels', '0005_rename_weighted_score_hotel_total_weighted_score_and_more'),
    ]

    operations = [
        # Add discount fields to Hotel model
        migrations.AddField(
            model_name='hotel',
            name='original_price',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='Giá gốc trước khi giảm (nếu có)',
                max_digits=10,
                null=True
            ),
        ),
        migrations.AddField(
            model_name='hotel',
            name='discount_percentage',
            field=models.PositiveIntegerField(
                default=0,
                help_text='Phần trăm giảm giá (0-100)'
            ),
        ),
        
        # Create UserSearchHistory model
        migrations.CreateModel(
            name='UserSearchHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('session_key', models.CharField(blank=True, max_length=255, null=True)),
                ('destination', models.CharField(max_length=255)),
                ('check_in', models.DateField(blank=True, null=True)),
                ('check_out', models.DateField(blank=True, null=True)),
                ('adults', models.PositiveIntegerField(default=1)),
                ('children', models.PositiveIntegerField(default=0)),
                ('rooms', models.PositiveIntegerField(default=1)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='search_history',
                    to=settings.AUTH_USER_MODEL
                )),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        
        # Add indexes for better performance
        migrations.AddIndex(
            model_name='usersearchhistory',
            index=models.Index(fields=['user', '-created_at'], name='hotels_user_user_id_idx'),
        ),
        migrations.AddIndex(
            model_name='usersearchhistory',
            index=models.Index(fields=['session_key', '-created_at'], name='hotels_user_session_idx'),
        ),
    ]
