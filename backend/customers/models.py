from django.db import models


class Customer(models.Model):
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=40, blank=True)
    address = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)
        indexes = [
            models.Index(fields=("name",), name="customers_customer_name_idx")
        ]

    def __str__(self):
        return self.name