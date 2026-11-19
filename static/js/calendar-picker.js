(function () {
    "use strict";

    var MONTHS = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ];
    var WEEKDAYS = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];
    var ISO_PATTERN = /^(\d{4})-(\d{2})-(\d{2})$/;
    var YEARS_BACK = 1;
    var YEARS_AHEAD = 5;

    var root = null;
    var parts = {};
    var active = null;
    var suppressOpen = false;

    function pad(number) {
        return String(number).padStart(2, "0");
    }

    function toIso(date) {
        return date.getFullYear() + "-" + pad(date.getMonth() + 1) + "-" + pad(date.getDate());
    }

    function parseIso(value) {
        var match = ISO_PATTERN.exec(value || "");
        if (!match) {
            return null;
        }
        var date = new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
        return date.getMonth() === Number(match[2]) - 1 ? date : null;
    }

    function startOfDay(date) {
        return new Date(date.getFullYear(), date.getMonth(), date.getDate());
    }

    function addDays(date, days) {
        return new Date(date.getFullYear(), date.getMonth(), date.getDate() + days);
    }

    function sameDay(first, second) {
        return Boolean(first) && Boolean(second) && toIso(first) === toIso(second);
    }

    function element(tag, className, text) {
        var node = document.createElement(tag);
        if (className) {
            node.className = className;
        }
        if (text !== undefined) {
            node.textContent = text;
        }
        return node;
    }

    function fire(input, name) {
        input.dispatchEvent(new Event(name, { bubbles: true }));
    }

    function build() {
        root = element("div", "rf-calendar");
        root.hidden = true;
        root.setAttribute("role", "dialog");
        root.setAttribute("aria-label", "Choose a date");

        var head = element("div", "rf-calendar__head");
        parts.prev = element("button", "rf-calendar__nav", "\u2039");
        parts.prev.type = "button";
        parts.prev.setAttribute("aria-label", "Previous month");
        parts.month = element("select", "rf-calendar__select");
        parts.month.setAttribute("aria-label", "Month");
        MONTHS.forEach(function (name, index) {
            var option = element("option", "", name);
            option.value = String(index);
            parts.month.appendChild(option);
        });
        parts.year = element("select", "rf-calendar__select");
        parts.year.setAttribute("aria-label", "Year");
        parts.next = element("button", "rf-calendar__nav", "\u203a");
        parts.next.type = "button";
        parts.next.setAttribute("aria-label", "Next month");
        head.appendChild(parts.prev);
        head.appendChild(parts.month);
        head.appendChild(parts.year);
        head.appendChild(parts.next);

        var weekdays = element("div", "rf-calendar__weekdays");
        WEEKDAYS.forEach(function (name) {
            weekdays.appendChild(element("span", "rf-calendar__weekday", name));
        });

        parts.grid = element("div", "rf-calendar__grid");
        parts.grid.setAttribute("role", "grid");

        var foot = element("div", "rf-calendar__foot");
        parts.today = element("button", "rf-calendar__action", "Today");
        parts.today.type = "button";
        parts.clear = element("button", "rf-calendar__action", "Clear");
        parts.clear.type = "button";
        foot.appendChild(parts.today);
        foot.appendChild(parts.clear);

        root.appendChild(head);
        root.appendChild(weekdays);
        root.appendChild(parts.grid);
        root.appendChild(foot);
        document.body.appendChild(root);

        parts.prev.addEventListener("click", function () {
            shiftMonth(-1);
        });
        parts.next.addEventListener("click", function () {
            shiftMonth(1);
        });
        parts.month.addEventListener("change", function () {
            active.view = new Date(active.view.getFullYear(), Number(parts.month.value), 1);
            render();
        });
        parts.year.addEventListener("change", function () {
            active.view = new Date(Number(parts.year.value), active.view.getMonth(), 1);
            render();
        });
        parts.today.addEventListener("click", function () {
            var today = startOfDay(new Date());
            if (isDisabled(today)) {
                return;
            }
            choose(today);
        });
        parts.clear.addEventListener("click", function () {
            active.input.value = "";
            fire(active.input, "input");
            fire(active.input, "change");
            close(true);
        });
        parts.grid.addEventListener("click", function (event) {
            var button = event.target.closest(".rf-calendar__day");
            if (button && !button.disabled) {
                choose(parseIso(button.dataset.date));
            }
        });
        parts.grid.addEventListener("keydown", onGridKey);
        root.addEventListener("keydown", function (event) {
            if (event.key === "Escape") {
                event.preventDefault();
                close(true);
            }
        });
        document.addEventListener("mousedown", function (event) {
            if (!active || root.contains(event.target) || event.target === active.input) {
                return;
            }
            close(false);
        });
        window.addEventListener("resize", function () {
            if (active) {
                close(false);
            }
        });
    }

    function isDisabled(date) {
        if (active.min && date < active.min) {
            return true;
        }
        return Boolean(active.max) && date > active.max;
    }

    function shiftMonth(step) {
        active.view = new Date(active.view.getFullYear(), active.view.getMonth() + step, 1);
        render();
    }

    function fillYears() {
        var current = new Date().getFullYear();
        var first = Math.min(current - YEARS_BACK, active.view.getFullYear());
        var last = Math.max(current + YEARS_AHEAD, active.view.getFullYear());
        if (active.min) {
            first = Math.max(first, active.min.getFullYear());
        }
        if (active.max) {
            last = Math.min(last, active.max.getFullYear());
        }
        parts.year.textContent = "";
        for (var year = first; year <= last; year += 1) {
            var option = element("option", "", String(year));
            option.value = String(year);
            parts.year.appendChild(option);
        }
    }

    function render(focusIso) {
        var view = active.view;
        var today = startOfDay(new Date());
        fillYears();
        parts.month.value = String(view.getMonth());
        parts.year.value = String(view.getFullYear());

        var firstOfMonth = new Date(view.getFullYear(), view.getMonth(), 1);
        var start = addDays(firstOfMonth, -firstOfMonth.getDay());
        var fallbackIso = toIso(firstOfMonth);
        var selectedInView = active.selected && active.selected.getMonth() === view.getMonth()
            && active.selected.getFullYear() === view.getFullYear();
        var todayInView = today.getMonth() === view.getMonth() && today.getFullYear() === view.getFullYear();
        var tabIso = focusIso || (selectedInView ? toIso(active.selected) : todayInView ? toIso(today) : fallbackIso);

        parts.grid.textContent = "";
        for (var index = 0; index < 42; index += 1) {
            var date = addDays(start, index);
            var iso = toIso(date);
            var button = element("button", "rf-calendar__day", String(date.getDate()));
            button.type = "button";
            button.dataset.date = iso;
            button.setAttribute("aria-label", date.toDateString());
            button.tabIndex = iso === tabIso ? 0 : -1;
            if (date.getMonth() !== view.getMonth()) {
                button.classList.add("is-outside");
            }
            if (sameDay(date, today)) {
                button.classList.add("is-today");
            }
            if (sameDay(date, active.selected)) {
                button.classList.add("is-selected");
                button.setAttribute("aria-selected", "true");
            }
            button.disabled = isDisabled(date);
            parts.grid.appendChild(button);
        }

        var prevMonthEnd = addDays(firstOfMonth, -1);
        parts.prev.disabled = Boolean(active.min) && prevMonthEnd < active.min;
        var nextMonthStart = new Date(view.getFullYear(), view.getMonth() + 1, 1);
        parts.next.disabled = Boolean(active.max) && nextMonthStart > active.max;
        parts.today.disabled = isDisabled(today);

        if (focusIso) {
            var target = parts.grid.querySelector('[data-date="' + focusIso + '"]');
            if (target) {
                target.focus();
            }
        }
    }

    function onGridKey(event) {
        var current = event.target.closest(".rf-calendar__day");
        if (!current) {
            return;
        }
        var date = parseIso(current.dataset.date);
        var next = null;
        if (event.key === "ArrowLeft") {
            next = addDays(date, -1);
        } else if (event.key === "ArrowRight") {
            next = addDays(date, 1);
        } else if (event.key === "ArrowUp") {
            next = addDays(date, -7);
        } else if (event.key === "ArrowDown") {
            next = addDays(date, 7);
        } else if (event.key === "PageUp") {
            next = new Date(date.getFullYear(), date.getMonth() - 1, date.getDate());
        } else if (event.key === "PageDown") {
            next = new Date(date.getFullYear(), date.getMonth() + 1, date.getDate());
        }
        if (!next) {
            return;
        }
        event.preventDefault();
        if (next.getMonth() !== active.view.getMonth() || next.getFullYear() !== active.view.getFullYear()) {
            active.view = new Date(next.getFullYear(), next.getMonth(), 1);
        }
        render(toIso(next));
    }

    function position() {
        var rect = active.input.getBoundingClientRect();
        root.style.visibility = "hidden";
        root.hidden = false;
        var width = root.offsetWidth;
        var height = root.offsetHeight;
        var left = Math.min(Math.max(8, rect.left), Math.max(8, window.innerWidth - width - 8));
        var below = rect.bottom + 8;
        var top = below;
        if (below + height > window.innerHeight - 8 && rect.top - height - 8 > 8) {
            top = rect.top - height - 8;
        }
        root.style.left = left + window.pageXOffset + "px";
        root.style.top = top + window.pageYOffset + "px";
        root.style.visibility = "visible";
    }

    function choose(date) {
        active.input.value = toIso(date);
        fire(active.input, "input");
        fire(active.input, "change");
        close(true);
    }

    function close(returnFocus) {
        if (!root || !active) {
            return;
        }
        var input = active.input;
        root.hidden = true;
        active = null;
        if (returnFocus) {
            suppressOpen = true;
            input.focus();
            window.setTimeout(function () {
                suppressOpen = false;
            }, 0);
        }
    }

    function open(input) {
        if (!root) {
            build();
        }
        if (active && active.input === input) {
            return;
        }
        if (active) {
            close(false);
        }
        var selected = parseIso(input.value);
        var min = parseIso(input.getAttribute("min") || input.dataset.min);
        var max = parseIso(input.getAttribute("max") || input.dataset.max);
        var today = startOfDay(new Date());
        var base = selected || (min && min > today ? min : today);
        active = {
            input: input,
            selected: selected,
            min: min,
            max: max,
            view: new Date(base.getFullYear(), base.getMonth(), 1)
        };
        render();
        position();
    }

    function enhance(input) {
        if (input.dataset.calendarReady) {
            return;
        }
        input.dataset.calendarReady = "1";
        var existing = input.value;
        var min = input.getAttribute("min");
        var max = input.getAttribute("max");
        if (input.type === "date") {
            input.type = "text";
        }
        input.value = existing;
        if (min) {
            input.dataset.min = min;
        }
        if (max) {
            input.dataset.max = max;
        }
        input.setAttribute("autocomplete", "off");
        input.setAttribute("inputmode", "none");
        input.setAttribute("aria-haspopup", "dialog");
        if (!input.getAttribute("placeholder")) {
            input.setAttribute("placeholder", "Select date");
        }
        input.classList.add("rf-calendar-input");

        input.addEventListener("click", function () {
            open(input);
        });
        input.addEventListener("focus", function () {
            if (!suppressOpen) {
                open(input);
            }
        });
        input.addEventListener("keydown", function (event) {
            if (event.key === "Tab" || event.key === "Escape" || event.ctrlKey || event.metaKey) {
                return;
            }
            if (event.key === "Enter" || event.key === " " || event.key === "ArrowDown") {
                event.preventDefault();
                open(input);
                if (active) {
                    var focusable = parts.grid.querySelector('[tabindex="0"]');
                    if (focusable) {
                        focusable.focus();
                    }
                }
                return;
            }
            event.preventDefault();
            if ((event.key === "Backspace" || event.key === "Delete") && input.value) {
                input.value = "";
                fire(input, "input");
                fire(input, "change");
            }
        });
        input.addEventListener("paste", function (event) {
            event.preventDefault();
        });
        input.addEventListener("drop", function (event) {
            event.preventDefault();
        });
    }

    function init() {
        document.querySelectorAll('input[type="date"], input[data-calendar]').forEach(enhance);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }

    window.RaddiCalendar = { enhance: enhance };
})();
