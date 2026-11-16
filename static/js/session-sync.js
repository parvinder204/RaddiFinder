(function () {
    "use strict";

    var configNode = document.getElementById("session-sync-config");
    if (!configNode) {
        return;
    }

    var config;
    try {
        config = JSON.parse(configNode.textContent);
    } catch (error) {
        return;
    }

    var CHANNEL_NAME = "raddifinder-session";
    var STORAGE_EVENT_KEY = "raddifinder:logout";
    var SENSITIVE_KEY = /(token|jwt|authori[sz]ation|session|credential|secret|^access$|^refresh$)/i;
    var ACTIVITY_EVENTS = ["mousemove", "mousedown", "keydown", "scroll", "touchstart", "click"];

    var channel = typeof window.BroadcastChannel === "function" ? new BroadcastChannel(CHANNEL_NAME) : null;
    var idleMs = (config.idleTimeout || 1800) * 1000;
    var heartbeatMs = Math.max(15000, Math.floor(idleMs / 3));
    var pollMs = Math.max(10000, (config.pollInterval || 30) * 1000);
    var lastActivity = Date.now();
    var lastHeartbeat = Date.now();
    var checking = false;
    var leaving = false;

    function eachStore(callback) {
        [window.localStorage, window.sessionStorage].forEach(function (store) {
            try {
                callback(store);
            } catch (error) {
                return;
            }
        });
    }

    function purgeSensitiveKeys() {
        eachStore(function (store) {
            Object.keys(store).forEach(function (key) {
                if (SENSITIVE_KEY.test(key)) {
                    store.removeItem(key);
                }
            });
        });
    }

    function clearAllStorage() {
        eachStore(function (store) {
            store.clear();
        });
    }

    function announceLogout() {
        var message = { type: "logout", at: Date.now() };
        if (channel) {
            channel.postMessage(message);
        }
        try {
            window.localStorage.setItem(STORAGE_EVENT_KEY, JSON.stringify(message));
            window.localStorage.removeItem(STORAGE_EVENT_KEY);
        } catch (error) {
            return;
        }
    }

    function leave(url) {
        if (leaving) {
            return;
        }
        leaving = true;
        window.location.replace(url);
    }

    if (config.mode === "logout") {
        announceLogout();
        clearAllStorage();
        leave(config.postLogoutUrl);
        return;
    }

    purgeSensitiveKeys();

    function handleRemoteLogout() {
        if (!config.authenticated) {
            return;
        }
        clearAllStorage();
        leave(config.postLogoutUrl);
    }

    if (channel) {
        channel.addEventListener("message", function (event) {
            if (event.data && event.data.type === "logout") {
                handleRemoteLogout();
            }
        });
    }

    window.addEventListener("storage", function (event) {
        if (event.key === STORAGE_EVENT_KEY && event.newValue) {
            handleRemoteLogout();
        }
    });

    function onSessionChanged(authenticated) {
        if (authenticated) {
            window.location.reload();
            return;
        }
        announceLogout();
        clearAllStorage();
        leave(config.postLogoutUrl);
    }

    function requestStatus(active) {
        if (checking || leaving) {
            return;
        }
        checking = true;
        var url = config.statusUrl + (active ? "?active=1" : "");
        fetch(url, {
            credentials: "same-origin",
            cache: "no-store",
            headers: { Accept: "application/json" }
        })
            .then(function (response) {
                return response.ok ? response.json() : null;
            })
            .then(function (state) {
                if (state && state.authenticated !== config.authenticated) {
                    onSessionChanged(state.authenticated);
                }
            })
            .catch(function () {
                return null;
            })
            .then(function () {
                checking = false;
            });
    }

    function markActive() {
        lastActivity = Date.now();
    }

    ACTIVITY_EVENTS.forEach(function (name) {
        window.addEventListener(name, markActive, { passive: true, capture: true });
    });

    function tick() {
        if (document.visibilityState === "hidden") {
            return;
        }
        var now = Date.now();
        var active =
            config.authenticated && lastActivity > lastHeartbeat && now - lastHeartbeat >= heartbeatMs;
        if (active) {
            lastHeartbeat = now;
        }
        requestStatus(active);
    }

    window.setInterval(tick, pollMs);

    document.addEventListener("visibilitychange", function () {
        if (document.visibilityState === "visible") {
            requestStatus(false);
        }
    });

    window.addEventListener("focus", function () {
        requestStatus(false);
    });

    window.addEventListener("pageshow", function (event) {
        if (event.persisted) {
            requestStatus(false);
        }
    });
})();
