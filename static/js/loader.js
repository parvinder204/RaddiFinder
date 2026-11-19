/*
 * RFLoader - one themed loader for the whole site.
 *
 * It appears on its own when a same-origin request (XMLHttpRequest / fetch), a link
 * navigation or a form submit takes longer than a moment, and it can be driven by hand:
 *
 *     var id = RFLoader.show("Sending OTP...");
 *     RFLoader.hide(id);
 *
 * RFAjax - small POST helper used by the OTP screens. It locks the button, shows the
 * loader, applies a timeout and turns every failure (throttled, CSRF, network, 5xx) into a
 * readable message instead of a button that silently does nothing.
 */
(function () {
    "use strict";

    if (window.RFLoader) {
        return;
    }

    var CONFIG = {
        showDelay: 300,
        minVisible: 400,
        navigationDelay: 250,
        navigationTimeout: 12000,
        requestTimeout: 90000,
        defaultMessage: "Please wait\u2026",
        ignoreRequests: [/\/accounts\/session-status\//],
        ignoreNavigation: [/\/get-invoice\//, /\/media\//]
    };

    var tokens = {};
    var nextId = 1;
    var count = 0;
    var overlay = null;
    var label = null;
    var showTimer = null;
    var showDue = 0;
    var hideTimer = null;
    var visibleSince = 0;

    function matchesAny(list, value) {
        return list.some(function (pattern) {
            return pattern.test(value);
        });
    }

    function sameOrigin(url) {
        try {
            return new URL(url, window.location.href).origin === window.location.origin;
        } catch (error) {
            return false;
        }
    }

    function currentMessage() {
        var text = CONFIG.defaultMessage;
        Object.keys(tokens).forEach(function (id) {
            if (tokens[id].message) {
                text = tokens[id].message;
            }
        });
        return text;
    }

    function build() {
        if (overlay) {
            return;
        }
        overlay = document.createElement("div");
        overlay.className = "rf-loader";
        overlay.setAttribute("role", "status");
        overlay.setAttribute("aria-live", "polite");
        overlay.hidden = true;

        var panel = document.createElement("div");
        panel.className = "rf-loader__panel";

        var spinner = document.createElement("div");
        spinner.className = "rf-loader__spinner";
        spinner.setAttribute("aria-hidden", "true");
        var ring = document.createElement("span");
        ring.className = "rf-loader__ring";
        var logo = document.createElement("span");
        logo.className = "rf-loader__logo";
        spinner.appendChild(ring);
        spinner.appendChild(logo);

        label = document.createElement("p");
        label.className = "rf-loader__text";

        panel.appendChild(spinner);
        panel.appendChild(label);
        overlay.appendChild(panel);
        document.body.appendChild(overlay);
    }

    function reveal() {
        showTimer = null;
        showDue = 0;
        if (count === 0) {
            return;
        }
        if (!document.body) {
            document.addEventListener("DOMContentLoaded", reveal, { once: true });
            return;
        }
        build();
        label.textContent = currentMessage();
        overlay.hidden = false;
        if (!overlay.classList.contains("is-visible")) {
            visibleSince = Date.now();
            window.requestAnimationFrame(function () {
                overlay.classList.add("is-visible");
            });
        }
        document.body.classList.add("rf-loader-active");
        document.body.setAttribute("aria-busy", "true");
    }

    function conceal() {
        hideTimer = null;
        if (!overlay || count > 0) {
            return;
        }
        overlay.classList.remove("is-visible");
        document.body.classList.remove("rf-loader-active");
        document.body.removeAttribute("aria-busy");
        window.setTimeout(function () {
            if (count === 0 && !overlay.classList.contains("is-visible")) {
                overlay.hidden = true;
            }
        }, 220);
    }

    function show(message, options) {
        var settings = options || {};
        var id = nextId++;
        var delay = typeof settings.delay === "number" ? settings.delay : 0;
        tokens[id] = { message: message || "", timer: null };
        count++;

        if (settings.ttl) {
            tokens[id].timer = window.setTimeout(function () {
                hide(id);
            }, settings.ttl);
        }
        if (hideTimer) {
            window.clearTimeout(hideTimer);
            hideTimer = null;
        }

        if (overlay && overlay.classList.contains("is-visible")) {
            label.textContent = currentMessage();
        } else {
            var due = Date.now() + delay;
            if (!showTimer || due < showDue) {
                window.clearTimeout(showTimer);
                showDue = due;
                showTimer = window.setTimeout(reveal, delay);
            }
        }
        return id;
    }

    function hide(id) {
        var token = tokens[id];
        if (!token) {
            return;
        }
        window.clearTimeout(token.timer);
        delete tokens[id];
        count = Math.max(0, count - 1);
        if (count > 0) {
            if (overlay && !overlay.hidden) {
                label.textContent = currentMessage();
            }
            return;
        }
        window.clearTimeout(showTimer);
        showTimer = null;
        showDue = 0;
        if (overlay && !overlay.hidden) {
            var wait = Math.max(0, CONFIG.minVisible - (Date.now() - visibleSince));
            hideTimer = window.setTimeout(conceal, wait);
        }
    }

    function reset() {
        Object.keys(tokens).forEach(function (id) {
            window.clearTimeout(tokens[id].timer);
        });
        tokens = {};
        count = 0;
        window.clearTimeout(showTimer);
        showTimer = null;
        showDue = 0;
        window.clearTimeout(hideTimer);
        conceal();
    }

    function wrap(promise, message) {
        var id = show(message, { delay: 0 });
        var release = function () {
            hide(id);
        };
        promise.then(release, release);
        return promise;
    }

    window.RFLoader = { show: show, hide: hide, reset: reset, wrap: wrap };

    /* ---- Requests: every same-origin XHR / fetch that outlives showDelay ---- */

    function trackable(url) {
        return Boolean(url) && sameOrigin(url) && !matchesAny(CONFIG.ignoreRequests, url);
    }

    if (window.XMLHttpRequest) {
        var nativeOpen = XMLHttpRequest.prototype.open;
        var nativeSend = XMLHttpRequest.prototype.send;

        XMLHttpRequest.prototype.open = function (method, url) {
            this.rfUrl = String(url);
            return nativeOpen.apply(this, arguments);
        };

        XMLHttpRequest.prototype.send = function () {
            var xhr = this;
            if (!xhr.rfSilent && trackable(xhr.rfUrl)) {
                var id = show("", { delay: CONFIG.showDelay, ttl: CONFIG.requestTimeout });
                xhr.addEventListener("loadend", function () {
                    hide(id);
                });
            }
            return nativeSend.apply(xhr, arguments);
        };
    }

    if (typeof window.fetch === "function") {
        var nativeFetch = window.fetch;

        window.fetch = function (input, init) {
            var url = typeof input === "string" ? input : (input && input.url) || "";
            var silent = Boolean(init && init.rfNoLoader);
            if (silent) {
                init = Object.assign({}, init);
                delete init.rfNoLoader;
            }
            if (silent || !trackable(url)) {
                return nativeFetch.call(window, input, init);
            }
            var id = show("", { delay: CONFIG.showDelay, ttl: CONFIG.requestTimeout });
            return nativeFetch.call(window, input, init).then(
                function (response) {
                    hide(id);
                    return response;
                },
                function (error) {
                    hide(id);
                    throw error;
                }
            );
        };
    }

    /* ---- Navigation: links and form submits ---- */

    function navigableLink(link, href) {
        if (!href || /^(#|javascript:|mailto:|tel:|sms:|whatsapp:)/i.test(href)) {
            return false;
        }
        if (link.hasAttribute("download") || link.hasAttribute("data-bs-toggle") || link.hasAttribute("data-toggle")) {
            return false;
        }
        if (link.target && link.target !== "_self") {
            return false;
        }
        var url;
        try {
            url = new URL(href, window.location.href);
        } catch (error) {
            return false;
        }
        if (url.origin !== window.location.origin) {
            return false;
        }
        if (url.pathname === window.location.pathname && url.search === window.location.search && url.hash) {
            return false;
        }
        return !matchesAny(CONFIG.ignoreNavigation, url.pathname);
    }

    document.addEventListener("click", function (event) {
        if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
            return;
        }
        var link = event.target.closest && event.target.closest("a");
        if (!link || link.closest("[data-no-loader]")) {
            return;
        }
        var scripted = link.classList.contains("anchor");
        var href = scripted ? link.getAttribute("data-href") : link.getAttribute("href");

        window.setTimeout(function () {
            if (event.defaultPrevented && !scripted) {
                return;
            }
            if (navigableLink(link, href)) {
                show("", { delay: CONFIG.navigationDelay, ttl: CONFIG.navigationTimeout });
            }
        }, 0);
    });

    function formNavigates(form) {
        return !form.hasAttribute("data-no-loader") && !form.closest("[data-no-loader]") && (!form.target || form.target === "_self");
    }

    document.addEventListener("submit", function (event) {
        var form = event.target;
        window.setTimeout(function () {
            if (!event.defaultPrevented && formNavigates(form)) {
                show(form.getAttribute("data-loader-message") || "", {
                    delay: CONFIG.navigationDelay,
                    ttl: CONFIG.navigationTimeout
                });
            }
        }, 0);
    });

    if (window.HTMLFormElement) {
        var nativeSubmit = HTMLFormElement.prototype.submit;
        HTMLFormElement.prototype.submit = function () {
            if (formNavigates(this)) {
                show(this.getAttribute("data-loader-message") || "", {
                    delay: CONFIG.navigationDelay,
                    ttl: CONFIG.navigationTimeout
                });
            }
            return nativeSubmit.apply(this, arguments);
        };
    }

    window.addEventListener("pageshow", function (event) {
        if (event.persisted) {
            reset();
        }
    });

    /* ---- RFAjax ---- */

    var REQUEST_TIMEOUT = 25000;
    var STATUS_MESSAGES = {
        0: "Network error. Check your connection and try again.",
        400: "Something went wrong. Please try again.",
        403: "Your session has expired. Please refresh the page and try again.",
        404: "Something went wrong. Please try again.",
        429: "Too many requests. Please wait a few minutes and try again.",
        503: "Service is temporarily unavailable. Please try again."
    };

    function elementOf(target) {
        if (!target) {
            return null;
        }
        if (typeof target === "string") {
            return document.querySelector(target);
        }
        return target.jquery ? target[0] : target;
    }

    function lock(button) {
        if (!button) {
            return;
        }
        button.disabled = true;
        button.classList.add("is-loading");
        button.setAttribute("aria-busy", "true");
    }

    function unlock(button) {
        if (!button) {
            return;
        }
        button.disabled = false;
        button.classList.remove("is-loading");
        button.removeAttribute("aria-busy");
    }

    function requestError(status, data) {
        var message = (data && (data.message || data.detail)) || STATUS_MESSAGES[status];
        if (!message) {
            message = status >= 500 ? "Server error. Please try again in a moment." : STATUS_MESSAGES[400];
        }
        var error = new Error(message);
        error.status = status;
        error.data = data;
        return error;
    }

    function csrfToken(params) {
        var field = document.querySelector("input[name=csrfmiddlewaretoken]");
        return (field && field.value) || (params && params.csrfmiddlewaretoken) || "";
    }

    function post(url, params, options) {
        var settings = options || {};
        var button = elementOf(settings.button);

        if (button && button.getAttribute("aria-busy") === "true") {
            var busy = new Error("");
            busy.busy = true;
            return Promise.reject(busy);
        }

        var body = new URLSearchParams();
        Object.keys(params || {}).forEach(function (key) {
            if (params[key] !== undefined && params[key] !== null) {
                body.append(key, params[key]);
            }
        });
        body.set("csrfmiddlewaretoken", csrfToken(params));

        var controller = typeof AbortController === "function" ? new AbortController() : null;
        var timer = controller ? window.setTimeout(function () {
            controller.abort();
        }, settings.timeout || REQUEST_TIMEOUT) : null;
        var loaderId = show(settings.message || "", {
            delay: typeof settings.delay === "number" ? settings.delay : 0,
            ttl: (settings.timeout || REQUEST_TIMEOUT) + 5000
        });
        lock(button);

        function finish() {
            window.clearTimeout(timer);
            hide(loaderId);
            unlock(button);
        }

        var request = window.fetch(url, {
            method: "POST",
            credentials: "same-origin",
            headers: { "X-Requested-With": "XMLHttpRequest", Accept: "application/json" },
            body: body,
            signal: controller ? controller.signal : undefined,
            rfNoLoader: true
        }).then(
            function (response) {
                return response.text().then(function (text) {
                    var data = null;
                    try {
                        data = JSON.parse(text);
                    } catch (error) {
                        data = null;
                    }
                    if (!response.ok || data === null) {
                        throw requestError(response.ok ? 500 : response.status, data);
                    }
                    return data;
                });
            },
            function (error) {
                if (error && error.name === "AbortError") {
                    var timeout = new Error("The request took too long. Please try again.");
                    timeout.status = 0;
                    throw timeout;
                }
                throw requestError(0, null);
            }
        );

        return request.then(
            function (data) {
                finish();
                return data;
            },
            function (error) {
                finish();
                throw error;
            }
        );
    }

    function fail(error, target) {
        if (!error || error.busy) {
            return;
        }
        var message = error.message || STATUS_MESSAGES[400];
        var element = elementOf(target);
        if (element) {
            element.textContent = message;
        } else if (window.UX && typeof window.UX.toast === "function") {
            window.UX.toast(message, { type: "error", timeout: 5000 });
        } else {
            window.alert(message);
        }
    }

    window.RFAjax = { post: post, fail: fail, lock: lock, unlock: unlock };
})();