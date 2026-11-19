(function () {
    "use strict";

    var KEY = "rf_wizard_draft";
    var MAX_AGE_MS = 3 * 60 * 60 * 1000;
    var STEP_ID = /^step-(\d+)$/;
    var AUTHENTICATED_STEP = 3;
    var settings = { authenticated: false, userId: "" };
    var started = false;
    var finished = false;

    function storage() {
        try {
            return window.localStorage;
        } catch (error) {
            return null;
        }
    }

    function discard() {
        var store = storage();
        if (!store) {
            return;
        }
        try {
            store.removeItem(KEY);
        } catch (error) {
            return;
        }
    }

    function read() {
        var store = storage();
        if (!store) {
            return null;
        }
        var draft = null;
        try {
            draft = JSON.parse(store.getItem(KEY));
        } catch (error) {
            return null;
        }
        if (!draft) {
            return null;
        }
        var expired = typeof draft.savedAt !== "number" || Date.now() - draft.savedAt > MAX_AGE_MS;
        if (expired || !Array.isArray(draft.items)) {
            discard();
            return null;
        }
        return draft;
    }

    function checkedIds() {
        return Array.prototype.map.call(document.querySelectorAll("input.p_items:checked"), function (box) {
            return box.value;
        });
    }

    function currentStep() {
        var panels = document.querySelectorAll(".setup-content");
        for (var index = 0; index < panels.length; index += 1) {
            var match = STEP_ID.exec(panels[index].id);
            if (match && panels[index].getClientRects().length > 0) {
                return Number(match[1]);
            }
        }
        return 1;
    }

    function save() {
        if (!started || finished) {
            return;
        }
        var items = checkedIds();
        if (!items.length) {
            discard();
            return;
        }
        var store = storage();
        if (!store) {
            return;
        }
        var draft = {
            items: items,
            step: currentStep(),
            owner: settings.userId || null,
            savedAt: Date.now()
        };
        try {
            store.setItem(KEY, JSON.stringify(draft));
        } catch (error) {
            return;
        }
    }

    function restore() {
        var draft = read();
        if (!draft) {
            return;
        }
        if (draft.owner && draft.owner !== settings.userId) {
            discard();
            return;
        }
        var ids = draft.items.filter(function (id) {
            return document.getElementById("check-" + id);
        });
        if (!ids.length) {
            discard();
            return;
        }
        $(".uatc").removeClass("disabled");
        $("#push_it").attr("lock", "false");
        ids.forEach(function (id) {
            $("#check-" + id).prop("checked", true);
            ItemClick(id);
        });
        var step = 1;
        if (draft.step >= 2) {
            step = settings.authenticated ? AUTHENTICATED_STEP : 2;
        }
        if (step > 1) {
            $("#step-btn-" + step).click();
        }
    }

    function bind() {
        document.addEventListener("change", function (event) {
            if (event.target.matches && event.target.matches("input.p_items")) {
                save();
            }
        });
        document.addEventListener("click", function (event) {
            if (event.target.closest && event.target.closest(".setup-panel a, .nextBtn, .back_button, #check_login")) {
                window.setTimeout(save, 0);
            }
        });
        window.addEventListener("pagehide", save);
        document.addEventListener("visibilitychange", function () {
            if (document.visibilityState === "hidden") {
                save();
            }
        });
    }

    function start(options) {
        settings.authenticated = Boolean(options.authenticated);
        settings.userId = options.userId ? String(options.userId) : "";
        if (options.restore) {
            restore();
        }
        started = true;
        save();
        bind();
    }

    function finish() {
        finished = true;
        discard();
    }

    window.RaddiWizard = { start: start, finish: finish };
})();
