import django.db.models.deletion
from django.db import migrations, models


def create_aliases_for_existing_lookups(apps, schema_editor):
    WordVariantLookup = apps.get_model('bnt_searcher', 'WordVariantLookup')
    WordVariantAlias = apps.get_model('bnt_searcher', 'WordVariantAlias')
    WordVariantAlias.objects.bulk_create([
        WordVariantAlias(searched_term=lookup.headword, lookup=lookup)
        for lookup in WordVariantLookup.objects.all()
    ])


class Migration(migrations.Migration):

    dependencies = [
        ('bnt_searcher', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='WordVariantLookup',
            old_name='search_term',
            new_name='headword',
        ),
        migrations.CreateModel(
            name='WordVariantAlias',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('searched_term', models.CharField(max_length=63, unique=True)),
                ('lookup', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='aliases', to='bnt_searcher.wordvariantlookup')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Word Variant Alias',
                'verbose_name_plural': 'Word Variant Aliases',
            },
        ),
        migrations.RunPython(
            create_aliases_for_existing_lookups,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
