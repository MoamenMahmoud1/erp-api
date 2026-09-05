def update_coupon_sync(instance, validated_data):
    for attribute, value in validated_data.items():
        setattr(instance, attribute, value)
    instance.save()
    return instance


class UpdateCoupon:
    def __call__(self, *, instance, validated_data):
        return update_coupon_sync(instance, validated_data)
