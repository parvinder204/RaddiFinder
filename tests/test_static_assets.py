import re
from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.staticfiles import finders

ASSETS = [
    "css/theme.css",
    "css/admin-modern.css",
    "css/calendar-picker.css",
    "css/select-picker.css",
    "css/list-controls.css",
    "js/calendar-picker.js",
    "js/select-picker.js",
    "js/list-controls.js",
    "js/waves-shim.js",
    "customer/js/wizard-draft.js",
    "customer/css/modern.css",
    "images/logo.png",
]

STATIC_TAG = re.compile(r"""\{%\s*static\s+['"]([^'"]+)['"]""")
COMMENT_BLOCK = re.compile(r"\{%\s*comment\s*%\}.*?\{%\s*endcomment\s*%\}", re.S)


@pytest.mark.parametrize("path", ASSETS)
def test_design_assets_exist(path):
    assert finders.find(path) is not None


def test_every_static_file_used_by_a_template_exists():
    missing = set()
    for template in Path(settings.BASE_DIR, "templates").rglob("*.html"):
        text = COMMENT_BLOCK.sub("", template.read_text(errors="ignore"))
        for path in STATIC_TAG.findall(text):
            if finders.find(path) is None:
                missing.add((template.name, path))
    assert missing == set()


def test_static_files_do_not_point_at_missing_source_maps():
    offenders = []
    for path in Path(settings.BASE_DIR, "static").rglob("*"):
        if path.suffix in (".css", ".js") and "sourceMappingURL" in path.read_text(errors="ignore"):
            offenders.append(str(path))
    assert offenders == []
