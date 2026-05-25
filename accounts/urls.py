from django.urls import path

from .views import (
    UserRegistrationView, LogoutView, UserLoginView,
    UserDashboardView, EmployeeDashboardView, ManagerDashboardView, AdminDashboardView,
    ResetRegistrationView
)


app_name = 'accounts'

urlpatterns = [
    path(
        "login/", UserLoginView.as_view(),
        name="user_login"
    ),
    path(
        "logout/", LogoutView.as_view(),
        name="user_logout"
    ),
    path(
        "register/", UserRegistrationView.as_view(),
        name="user_registration"
    ),
    path(
        "dashboard/", UserDashboardView.as_view(),
        name="user_dashboard"
    ),
    path(
        "employee/dashboard/", EmployeeDashboardView.as_view(),
        name="employee_dashboard"
    ),
    path(
        "manager/dashboard/", ManagerDashboardView.as_view(),
        name="manager_dashboard"
    ),
    path(
        "admin/dashboard/", AdminDashboardView.as_view(),
        name="admin_dashboard"
    ),
    path(
        "reset-registration/", ResetRegistrationView.as_view(),
        name="reset_registration"
    ),
]

