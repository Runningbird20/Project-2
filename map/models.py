from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class OfficeLocation(models.Model):
    job_post = models.OneToOneField(
        'jobposts.JobPost',
        on_delete=models.CASCADE,
        related_name='office_location',
    )
    address_line_1 = models.CharField(max_length=255, blank=True)
    address_line_2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, blank=True, default='United States')
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        validators=[
            MinValueValidator(Decimal('-90')),
            MaxValueValidator(Decimal('90')),
        ],
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        validators=[
            MinValueValidator(Decimal('-180')),
            MaxValueValidator(Decimal('180')),
        ],
    )

    class Meta:
        ordering = ['job_post_id']

    def __str__(self):
        return f'{self.job_post.title} office'

    @property
    def full_address(self):
        parts = [
            self.address_line_1,
            self.address_line_2,
            self.city,
            self.state,
            self.postal_code,
            self.country,
        ]
        return ', '.join([part for part in parts if part])

    @property
    def osm_embed_url(self):
        lat = float(self.latitude)
        lon = float(self.longitude)
        delta = 0.01
        bbox = f'{lon - delta},{lat - delta},{lon + delta},{lat + delta}'
        marker = f'{lat},{lon}'
        return f'https://www.openstreetmap.org/export/embed.html?bbox={bbox}&layer=mapnik&marker={marker}'

    @property
    def osm_link_url(self):
        lat = float(self.latitude)
        lon = float(self.longitude)
        return f'https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=15/{lat}/{lon}'
