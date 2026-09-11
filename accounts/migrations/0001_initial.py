import django.contrib.auth.models
import django.contrib.auth.validators
from django.conf import settings
from django.db import migrations, models
from django.db.models.functions import Lower
from django.utils import timezone
import django.db.models.deletion
import phonenumber_field.modelfields
import accounts.managers


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="CustomUserModel",
            fields=[
                (
                    "id",
                    models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"),
                ),
                (
                    "password",
                    models.CharField(max_length=128, verbose_name="password"),
                ),
                (
                    "last_login",
                    models.DateTimeField(blank=True, null=True, verbose_name="last login"),
                ),
                (
                    "is_superuser",
                    models.BooleanField(
                        default=False,
                        help_text="Designates that this user has all permissions without explicitly assigning them.",
                        verbose_name="superuser status",
                    ),
                ),
                (
                    "username",
                    models.CharField(
                        error_messages={"unique": "A user with that username already exists."},
                        help_text="Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.",
                        max_length=150,
                        unique=True,
                        validators=[django.contrib.auth.validators.UnicodeUsernameValidator()],
                        verbose_name="username",
                    ),
                ),
                (
                    "first_name",
                    models.CharField(blank=True, max_length=150, verbose_name="first name"),
                ),
                (
                    "last_name",
                    models.CharField(blank=True, max_length=150, verbose_name="last name"),
                ),
                (
                    "email",
                    models.EmailField(max_length=254),
                ),
                ("is_staff", models.BooleanField(default=False, verbose_name="staff status")),
                ("is_active", models.BooleanField(default=True, verbose_name="active")),
                ("date_joined", models.DateTimeField(default=timezone.now, verbose_name="date joined")),
                (
                    "phone_number",
                    phonenumber_field.modelfields.PhoneNumberField(blank=True, max_length=128, null=True),
                ),
                ("is_verified", models.BooleanField(default=False)),
                ("photo", models.ImageField(blank=True, null=True, upload_to="photo/%Y/%m/%d/")),
                ("password_changed_at", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "groups",
                    models.ManyToManyField(
                        blank=True,
                        help_text="The groups this user belongs to. A user will get all permissions granted to each of their groups.",
                        related_name="accounts_customusermodel_set",
                        related_query_name="customusermodel",
                        to="auth.group",
                        verbose_name="groups",
                    ),
                ),
                (
                    "user_permissions",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Specific permissions for this user.",
                        related_name="accounts_customusermodel_set",
                        related_query_name="customusermodel",
                        to="auth.permission",
                        verbose_name="user permissions",
                    ),
                ),
            ],
            options={
                "verbose_name": "User",
                "verbose_name_plural": "Users",
                "constraints": [
                    models.CheckConstraint(
                        condition=~models.Q(("username__contains", "@")),
                        name="accounts_user_username_not_at",
                    ),
                    models.CheckConstraint(
                        condition=~models.Q(("email", "")),
                        name="accounts_user_email_not_empty",
                    ),
                    models.UniqueConstraint(
                        Lower("email"),
                        name="accounts_user_email_ci_unique",
                    ),
                ],
            },
            managers=[
                ("objects", accounts.managers.CustomUserManager()),
            ],
        ),
        migrations.CreateModel(
            name="Employee",
            fields=[
                (
                    "id",
                    models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True),
                ),
                (
                    "manager",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="team_members",
                        to="accounts.employee",
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="employee",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "work_site",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="employees",
                        to="organization.site",
                    ),
                ),
                (
                    "department",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="employees",
                        to="organization.department",
                    ),
                ),
            ],
            options={
                "verbose_name": "Employee",
                "verbose_name_plural": "Employees",
            },
            managers=[
                ("objects", accounts.managers.EmployeeManager()),
            ],
        ),
        migrations.CreateModel(
            name="RoleProfile",
            fields=[
                (
                    "id",
                    models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"),
                ),
                ("name", models.CharField(default="", max_length=150)),
                ("level", models.PositiveSmallIntegerField(db_index=True, default=0)),
                (
                    "scope",
                    models.CharField(
                        choices=[("company", "Company"), ("branch", "Branch"), ("site", "Site")],
                        db_index=True,
                        default="site",
                        max_length=20,
                    ),
                ),
                ("requires_shift", models.BooleanField(default=False)),
                ("description", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "group",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="role_profile",
                        to="auth.group",
                    ),
                ),
            ],
            options={
                "verbose_name": "Role profile",
                "verbose_name_plural": "Role profiles",
                "ordering": ("-level", "name", "pk"),
            },
        ),
    ]
