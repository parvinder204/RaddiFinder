(function () {
    "use strict";

    var DEBOUNCE_MS = 400;
    var FOCUS_KEY = "list-search-focus";

    function remember() {
        try {
            sessionStorage.setItem(FOCUS_KEY, window.location.pathname);
        } catch (error) {
            return;
        }
    }

    function restoreFocus(input) {
        try {
            if (sessionStorage.getItem(FOCUS_KEY) !== window.location.pathname) {
                return;
            }
            sessionStorage.removeItem(FOCUS_KEY);
        } catch (error) {
            return;
        }
        input.focus();
        var end = input.value.length;
        input.setSelectionRange(end, end);
    }

    document.querySelectorAll("form.js-list-controls").forEach(function (form) {
        form.querySelectorAll("[data-auto-submit]").forEach(function (select) {
            select.addEventListener("change", function () {
                form.submit();
            });
        });

        form.querySelectorAll("[data-debounce-submit]").forEach(function (input) {
            var timer = null;
            var lastValue = input.value;
            restoreFocus(input);
            input.addEventListener("input", function () {
                clearTimeout(timer);
                timer = setTimeout(function () {
                    if (input.value === lastValue) {
                        return;
                    }
                    lastValue = input.value;
                    remember();
                    form.submit();
                }, DEBOUNCE_MS);
            });
        });
    });
})();
