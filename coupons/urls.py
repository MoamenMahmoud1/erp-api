from adrf.routers import SimpleRouter

from .api.views import CouponViewSet


app_name = "coupons"

router = SimpleRouter()

router.register(
    "coupons",
    CouponViewSet,
    basename="coupon",
)

urlpatterns = router.urls
