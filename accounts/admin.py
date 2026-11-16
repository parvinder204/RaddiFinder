from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.core.exceptions import ValidationError

from .models import OTP, Person


class UserCreationForm(forms.ModelForm):
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Password confirmation", widget=forms.PasswordInput)

    class Meta:
        model = Person
        fields = ("email", "phone")

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField()

    class Meta:
        model = Person
        fields = (
            "email",
            "phone",
            "first_name",
            "last_name",
            "role",
            "image",
            "is_active",
            "is_staff",
            "is_superuser",
            "password",
        )


class PersonAdmin(BaseUserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    list_display = ("id", "email", "phone", "role", "first_name", "last_name", "is_superuser")
    list_filter = ("role",)
    fieldsets = (
        (None, {"fields": ("email", "phone", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "image")}),
        ("Permissions", {"fields": ("is_superuser", "is_staff", "is_active")}),
        ("User Type", {"fields": ("role",)}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "phone", "password1", "password2"),
            },
        ),
    )
    search_fields = ("email", "first_name", "last_name", "phone")
    ordering = ("created",)
    filter_horizontal = ()


class OTPAdmin(admin.ModelAdmin):
    ordering = ("-created",)
    list_display = ("id", "phone", "correct", "attempts", "created")
    list_display_links = ("id", "phone")
    exclude = ("otp",)


admin.site.register(Person, PersonAdmin)
admin.site.register(OTP, OTPAdmin)
