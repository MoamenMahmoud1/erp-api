from django.urls import path

from common.api.approval_requests import ApprovalRequestListCreateView, ApprovalReviewView

urlpatterns = [
    path("approvals/", ApprovalRequestListCreateView.as_view(), name="approval-request-list-create"),
    path("approvals/<int:approval_event_id>/<str:decision>/", ApprovalReviewView.as_view(), name="approval-review"),
]
