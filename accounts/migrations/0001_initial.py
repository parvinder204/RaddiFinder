import uuid
import accounts.managers
import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("common_models", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="OTP",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("modified", models.DateTimeField(auto_now=True)),
                ("otp", models.CharField(max_length=6, verbose_name="OTP")),
                (
                    "phone",
                    models.CharField(max_length=10, unique=True, verbose_name="Phone Number"),
                ),
                (
                    "correct",
                    models.BooleanField(default=False, verbose_name="Is otp correct"),
                ),
                (
                    "attempts",
                    models.PositiveSmallIntegerField(default=0, verbose_name="Failed attempts"),
                ),
                (
                    "last_sent",
                    models.DateTimeField(
                        default=django.utils.timezone.now, verbose_name="Last sent"
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="Person",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("password", models.CharField(max_length=128, verbose_name="password")),
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
                ("created", models.DateTimeField(auto_now_add=True)),
                ("modified", models.DateTimeField(auto_now=True)),
                (
                    "address",
                    models.TextField(blank=True, null=True, verbose_name="Address"),
                ),
                (
                    "pin_code",
                    models.CharField(
                        blank=True, max_length=6, null=True, verbose_name="Zip Code"
                    ),
                ),
                (
                    "first_name",
                    models.CharField(
                        blank=True, max_length=50, null=True, verbose_name="first Name"
                    ),
                ),
                (
                    "last_name",
                    models.CharField(
                        blank=True, max_length=50, null=True, verbose_name="last Name"
                    ),
                ),
                (
                    "email",
                    models.EmailField(
                        blank=True,
                        error_messages={"unique": "A user with that email already exists."},
                        max_length=254,
                        null=True,
                        unique=True,
                        verbose_name="email",
                    ),
                ),
                (
                    "phone",
                    models.CharField(
                        blank=True,
                        error_messages={
                            "unique": "A user with that phone number already exists."
                        },
                        max_length=10,
                        null=True,
                        unique=True,
                        validators=[
                            django.core.validators.RegexValidator(
                                "^\\d{10}$", "Phone number must be exactly 10 digits."
                            )
                        ],
                        verbose_name="phone Number",
                    ),
                ),
                (
                    "role",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("Customer", "Customer"),
                            ("Admin", "Admin"),
                            ("Pickup", "Pickup"),
                            ("SuperUser", "SuperUser"),
                        ],
                        max_length=50,
                        null=True,
                        verbose_name="role of user",
                    ),
                ),
                (
                    "image",
                    models.ImageField(
                        blank=True,
                        null=True,
                        upload_to="user_images",
                        verbose_name="profile Picture",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="Is set to True only for superusers,staffs and users with verified email/phone",
                        verbose_name="active",
                    ),
                ),
                (
                    "is_staff",
                    models.BooleanField(
                        default=False,
                        help_text="Designates whether the user can log into this admin site.",
                        verbose_name="staff",
                    ),
                ),
                (
                    "city",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="common_models.city",
                        verbose_name="City",
                    ),
                ),
                (
                    "groups",
                    models.ManyToManyField(
                        blank=True,
                        help_text="The groups this user belongs to. A user will get all permissions granted to each of their groups.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.group",
                        verbose_name="groups",
                    ),
                ),
                (
                    "state",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="common_models.state",
                        verbose_name="State",
                    ),
                ),
                (
                    "user_permissions",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Specific permissions for this user.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.permission",
                        verbose_name="user permissions",
                    ),
                ),
            ],
            options={
                "verbose_name": "user",
                "verbose_name_plural": "users",
            },
            managers=[
                ("objects", accounts.managers.UserManager()),
            ],
        ),
    ]
