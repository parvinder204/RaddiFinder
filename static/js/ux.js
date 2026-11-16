(function () {
    "use strict";

    var body = document.body;
    var approved = new WeakSet();
    var queue = Promise.resolve();
    var modalParts = null;
    var toastRegion = null;
    var reducedMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    function createElement(tag, className, attributes) {
        var element = document.createElement(tag);
        if (className) {
            element.className = className;
        }
        Object.keys(attributes || {}).forEach(function (name) {
            element.setAttribute(name, attributes[name]);
        });
        return element;
    }

    function buildModal() {
        var backdrop = createElement("div", "ux-modal-backdrop", { hidden: "" });
        var dialog = createElement("div", "ux-modal", {
            role: "alertdialog",
            "aria-modal": "true",
            "aria-labelledby": "ux-modal-title",
            "aria-describedby": "ux-modal-message",
            tabindex: "-1"
        });
        var icon = createElement("div", "ux-modal__icon", { "aria-hidden": "true" });
        var title = createElement("h2", "ux-modal__title", { id: "ux-modal-title" });
        var message = createElement("p", "ux-modal__message", { id: "ux-modal-message" });
        var actions = createElement("div", "ux-modal__actions");
        var cancel = createElement("button", "ux-btn ux-btn--secondary", { type: "button" });
        var ok = createElement("button", "ux-btn ux-btn--primary", { type: "button" });

        actions.appendChild(cancel);
        actions.appendChild(ok);
        [icon, title, message, actions].forEach(function (part) {
            dialog.appendChild(part);
        });
        backdrop.appendChild(dialog);
        body.appendChild(backdrop);

        return {
            backdrop: backdrop,
            dialog: dialog,
            icon: icon,
            title: title,
            message: message,
            cancel: cancel,
            ok: ok
        };
    }

    function openModal(options) {
        return new Promise(function (resolve) {
            if (!modalParts) {
                modalParts = buildModal();
            }
            var parts = modalParts;
            var previousFocus = document.activeElement;
            var danger = options.variant === "danger";

            parts.dialog.classList.toggle("ux-modal--danger", danger);
            parts.icon.textContent = danger ? "!" : "?";
            parts.title.textContent = options.title;
            parts.message.textContent = options.message;
            parts.cancel.textContent = options.cancelText;
            parts.ok.textContent = options.confirmText;
            parts.ok.className = "ux-btn " + (danger ? "ux-btn--danger" : "ux-btn--primary");

            function close(result) {
                document.removeEventListener("keydown", onKeydown, true);
                parts.backdrop.removeEventListener("click", onBackdrop);
                parts.cancel.removeEventListener("click", onCancel);
                parts.ok.removeEventListener("click", onOk);
                parts.backdrop.classList.remove("is-open");
                body.classList.remove("ux-modal-open");
                window.setTimeout(
                    function () {
                        parts.backdrop.hidden = true;
                        if (previousFocus && typeof previousFocus.focus === "function") {
                            previousFocus.focus({ preventScroll: true });
                        }
                        resolve(result);
                    },
                    reducedMotion ? 0 : 180
                );
            }

            function onCancel() {
                close(false);
            }

            function onOk() {
                close(true);
            }

            function onBackdrop(event) {
                if (event.target === parts.backdrop) {
                    close(false);
                }
            }

            function onKeydown(event) {
                if (event.key === "Escape") {
                    event.preventDefault();
                    event.stopPropagation();
                    close(false);
                    return;
                }
                if (event.key !== "Tab") {
                    return;
                }
                var focusable = [parts.cancel, parts.ok];
                var index = focusable.indexOf(document.activeElement);
                if (event.shiftKey && index <= 0) {
                    event.preventDefault();
                    parts.ok.focus();
                } else if (!event.shiftKey && index === focusable.length - 1) {
                    event.preventDefault();
                    parts.cancel.focus();
                } else if (index === -1) {
                    event.preventDefault();
                    parts.cancel.focus();
                }
            }

            parts.backdrop.addEventListener("click", onBackdrop);
            parts.cancel.addEventListener("click", onCancel);
            parts.ok.addEventListener("click", onOk);
            document.addEventListener("keydown", onKeydown, true);

            parts.backdrop.hidden = false;
            body.classList.add("ux-modal-open");
            window.requestAnimationFrame(function () {
                parts.backdrop.classList.add("is-open");
                (danger ? parts.cancel : parts.ok).focus({ preventScroll: true });
            });
        });
    }

    function confirmAction(options) {
        var settings = {
            title: options.title || "Are you sure?",
            message: options.message || "",
            confirmText: options.confirmText || "Confirm",
            cancelText: options.cancelText || "Cancel",
            variant: options.variant || "primary"
        };
        queue = queue.then(function () {
            return openModal(settings);
        });
        return queue;
    }

    function ensureToastRegion() {
        if (!toastRegion) {
            toastRegion = createElement("div", "ux-toast-region", {
                role: "status",
                "aria-live": "polite"
            });
            body.appendChild(toastRegion);
        }
        return toastRegion;
    }

    function toast(message, options) {
        var settings = options || {};
        var element = createElement(
            "div",
            "ux-toast" + (settings.type === "error" ? " ux-toast--error" : "")
        );
        var text = createElement("span");
        var close = createElement("button", "ux-toast__close", {
            type: "button",
            "aria-label": "Dismiss"
        });

        text.textContent = message;
        close.textContent = "\u00d7";
        element.appendChild(text);
        element.appendChild(close);
        ensureToastRegion().appendChild(element);

        function dismiss() {
            element.classList.remove("is-visible");
            window.setTimeout(function () {
                element.remove();
            }, reducedMotion ? 0 : 200);
        }

        close.addEventListener("click", dismiss);
        window.requestAnimationFrame(function () {
            element.classList.add("is-visible");
        });
        window.setTimeout(dismiss, settings.timeout || 3500);
    }

    function formOf(element) {
        if (element.tagName === "FORM") {
            return element;
        }
        return element.form || element.closest("form");
    }

    function needsConfirmation(element) {
        var field = element.getAttribute("data-confirm-field");
        if (!field) {
            return true;
        }
        var form = formOf(element);
        var control = form && form.elements[field];
        if (!control) {
            return false;
        }
        var values = (element.getAttribute("data-confirm-values") || "").split("|");
        return values.indexOf(control.value) !== -1;
    }

    function describe(element) {
        var field = element.getAttribute("data-confirm-field");
        var form = field ? formOf(element) : null;
        var value = form && form.elements[field] ? form.elements[field].value : "";
        var dangerValues = (element.getAttribute("data-confirm-danger-values") || "").split("|");
        var danger = dangerValues.indexOf(value) !== -1;
        return {
            title: element.getAttribute("data-confirm-title"),
            message: (element.getAttribute("data-confirm") || "").replace("{value}", value),
            confirmText: danger
                ? element.getAttribute("data-confirm-danger-ok") || element.getAttribute("data-confirm-ok")
                : element.getAttribute("data-confirm-ok"),
            cancelText: element.getAttribute("data-confirm-cancel"),
            variant: danger ? "danger" : element.getAttribute("data-confirm-variant")
        };
    }

    document.addEventListener(
        "click",
        function (event) {
            var trigger = event.target.closest && event.target.closest("[data-confirm]");
            if (!trigger || trigger.tagName === "FORM") {
                return;
            }
            if (approved.has(trigger)) {
                approved.delete(trigger);
                return;
            }
            if (trigger.disabled || trigger.getAttribute("aria-disabled") === "true") {
                return;
            }
            if (!needsConfirmation(trigger)) {
                return;
            }
            var form = trigger.type === "submit" ? formOf(trigger) : null;
            if (form && !form.checkValidity()) {
                return;
            }
            event.preventDefault();
            event.stopImmediatePropagation();
            confirmAction(describe(trigger)).then(function (accepted) {
                if (accepted) {
                    approved.add(trigger);
                    trigger.click();
                }
            });
        },
        true
    );

    document.addEventListener(
        "submit",
        function (event) {
            var form = event.target;
            if (form.getAttribute("data-ux-submitting") === "1") {
                event.preventDefault();
                event.stopImmediatePropagation();
                return;
            }
            if (!form.hasAttribute("data-confirm")) {
                return;
            }
            if (approved.has(form)) {
                approved.delete(form);
                return;
            }
            if (!needsConfirmation(form)) {
                return;
            }
            event.preventDefault();
            event.stopImmediatePropagation();
            var submitter = event.submitter || null;
            confirmAction(describe(form)).then(function (accepted) {
                if (!accepted) {
                    return;
                }
                approved.add(form);
                if (typeof form.requestSubmit === "function") {
                    form.requestSubmit(submitter || undefined);
                } else {
                    form.submit();
                }
            });
        },
        true
    );

    function releaseForm(form, submitter) {
        form.removeAttribute("data-ux-submitting");
        if (submitter) {
            submitter.classList.remove("is-loading");
            submitter.removeAttribute("aria-busy");
        }
    }

    document.addEventListener("submit", function (event) {
        var form = event.target;
        if (event.defaultPrevented || form.hasAttribute("data-no-loading")) {
            return;
        }
        var submitter = event.submitter || form.querySelector('[type="submit"]');
        form.setAttribute("data-ux-submitting", "1");
        if (submitter) {
            submitter.classList.add("is-loading");
            submitter.setAttribute("aria-busy", "true");
        }
        window.setTimeout(function () {
            releaseForm(form, submitter);
        }, 10000);
    });

    window.addEventListener("pageshow", function (event) {
        if (!event.persisted) {
            return;
        }
        Array.prototype.forEach.call(document.querySelectorAll("[data-ux-submitting]"), function (form) {
            releaseForm(form, form.querySelector(".is-loading"));
        });
    });

    function copyText(value) {
        if (navigator.clipboard && window.isSecureContext) {
            return navigator.clipboard.writeText(value);
        }
        return new Promise(function (resolve, reject) {
            var field = createElement("textarea", "", { readonly: "", "aria-hidden": "true" });
            field.value = value;
            field.style.position = "fixed";
            field.style.opacity = "0";
            body.appendChild(field);
            field.select();
            var copied = document.execCommand && document.execCommand("copy");
            field.remove();
            return copied ? resolve() : reject(new Error("copy failed"));
        });
    }

    document.addEventListener("click", function (event) {
        var trigger = event.target.closest && event.target.closest("[data-copy]");
        if (!trigger) {
            return;
        }
        event.preventDefault();
        copyText(trigger.getAttribute("data-copy"))
            .then(function () {
                toast(trigger.getAttribute("data-copy-message") || "Copied to clipboard");
            })
            .catch(function () {
                toast("Unable to copy", { type: "error" });
            });
    });

    function setupBackToTop() {
        var button = createElement("button", "ux-back-to-top", {
            type: "button",
            "aria-label": "Back to top",
            title: "Back to top"
        });
        button.textContent = "\u2191";
        body.appendChild(button);

        var ticking = false;
        function update() {
            button.classList.toggle("is-visible", window.scrollY > 400);
            ticking = false;
        }
        window.addEventListener(
            "scroll",
            function () {
                if (!ticking) {
                    ticking = true;
                    window.requestAnimationFrame(update);
                }
            },
            { passive: true }
        );
        button.addEventListener("click", function () {
            window.scrollTo({ top: 0, behavior: reducedMotion ? "auto" : "smooth" });
        });
        update();
    }

    function setupOfflineBanner() {
        var banner = createElement("div", "ux-offline-banner", { role: "alert", hidden: "" });
        banner.textContent = "You are offline. Changes will not be saved until you reconnect.";
        body.appendChild(banner);
        function sync() {
            banner.hidden = navigator.onLine;
        }
        window.addEventListener("online", sync);
        window.addEventListener("offline", sync);
        sync();
    }

    var FIELD_HINTS = [
        { pattern: /otp/i, attributes: { inputmode: "numeric", autocomplete: "one-time-code" } },
        { pattern: /phone/i, attributes: { inputmode: "tel", autocomplete: "tel-national" } },
        { pattern: /pin[-_]?code|zip/i, attributes: { inputmode: "numeric", autocomplete: "postal-code" } },
        { pattern: /^email$/i, attributes: { autocomplete: "email" } },
        { pattern: /first[-_]?name/i, attributes: { autocomplete: "given-name" } },
        { pattern: /last[-_]?name/i, attributes: { autocomplete: "family-name" } },
        { pattern: /^address$/i, attributes: { autocomplete: "street-address" } },
        { pattern: /^password[12]$/i, attributes: { autocomplete: "new-password" } },
        { pattern: /^password$/i, attributes: { autocomplete: "current-password" } }
    ];

    function applyFieldHints() {
        Array.prototype.forEach.call(document.querySelectorAll("input[name], textarea[name]"), function (field) {
            var name = field.getAttribute("name");
            FIELD_HINTS.some(function (hint) {
                if (!hint.pattern.test(name)) {
                    return false;
                }
                Object.keys(hint.attributes).forEach(function (attribute) {
                    if (!field.hasAttribute(attribute)) {
                        field.setAttribute(attribute, hint.attributes[attribute]);
                    }
                });
                return true;
            });
        });
    }

    function markCurrentNavigation() {
        var path = window.location.pathname.replace(/\/$/, "") || "/";
        Array.prototype.forEach.call(document.querySelectorAll(".offcanvas .nav-link[href]"), function (link) {
            var target = (link.getAttribute("href") || "").replace(/\/$/, "") || "/";
            if (target !== "#" && target === path) {
                link.classList.add("is-current");
                link.setAttribute("aria-current", "page");
            }
        });
    }

    function addSkipLink() {
        var target = document.getElementById("main-content");
        if (!target) {
            return;
        }
        var link = createElement("a", "ux-skip-link", { href: "#main-content" });
        link.textContent = "Skip to main content";
        body.insertBefore(link, body.firstChild);
    }

    window.UX = { confirm: confirmAction, toast: toast };

    setupBackToTop();
    setupOfflineBanner();
    applyFieldHints();
    markCurrentNavigation();
    addSkipLink();
})();
