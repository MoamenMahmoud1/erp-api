from customers.models import Customer


def create_customer_sync(validated_data):
    return Customer.objects.create(**validated_data)


class CreateCustomer:
    def __call__(self, *, validated_data):
        return create_customer_sync(validated_data)
