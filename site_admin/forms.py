from django import forms

from common_models.models import Item, PickupBoy


class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = "__all__"
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "id": "validationCustom04",
                    "placeholder": "Product Name",
                    "name": "name",
                }
            ),
            "price": forms.TextInput(
                attrs={
                    "class": "form-control number-only",
                    "id": "validationCustom04",
                    "placeholder": "INR-20",
                    "name": "price",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "style-description form-control",
                    "id": "validationCustom04",
                    "name": "description",
                }
            ),
            "unit": forms.Select(
                attrs={
                    "class": "form-select",
                    "id": "productunit",
                    "name": "unit",
                    "required": "true",
                }
            ),
            "image": forms.ClearableFileInput(
                attrs={
                    "class": "file-upload",
                    "accept": "image/*",
                    "id": "id_image",
                    "name": "image",
                }
            ),
        }


class PickupBoyForm(forms.ModelForm):
    class Meta:
        model = PickupBoy
        fields = "__all__"
        widgets = {
            "full_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "id": "validationCustom04",
                    "placeholder": "Name",
                    "name": "name",
                }
            ),
            "phone": forms.TextInput(
                attrs={
                    "class": "form-control number-only",
                    "id": "validationCustom04",
                    "placeholder": "59874522",
                    "name": "phone",
                }
            ),
        }

    def clean_phone(self):
        phone = self.cleaned_data["phone"].strip()
        if not phone.isdigit():
            raise forms.ValidationError("Enter a valid phone number.")
        return phone
