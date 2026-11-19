(function () {
    "use strict";

    var instances = new WeakMap();
    var menu = null;
    var current = null;
    var openedAt = 0;
    var typed = { text: "", timer: null };
    var counter = 0;
    var SYNCED_ATTRIBUTES = ["class", "disabled", "style", "hidden", "required"];

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

    function fire(select, name) {
        select.dispatchEvent(new Event(name, { bubbles: true }));
    }

    function owningSelect(node) {
        var parent = node.parentNode;
        if (parent && parent.tagName === "OPTGROUP") {
            parent = parent.parentNode;
        }
        return parent && parent.tagName === "SELECT" ? parent : null;
    }

    function schedule(select) {
        var instance = instances.get(select);
        if (!instance || instance.pending) {
            return;
        }
        instance.pending = true;
        window.requestAnimationFrame(function () {
            instance.pending = false;
            sync(instance);
        });
    }

    function patchSetter(prototype, property, resolve) {
        var descriptor = Object.getOwnPropertyDescriptor(prototype, property);
        if (!descriptor || !descriptor.set) {
            return;
        }
        Object.defineProperty(prototype, property, {
            configurable: true,
            enumerable: descriptor.enumerable,
            get: descriptor.get,
            set: function (value) {
                descriptor.set.call(this, value);
                var select = resolve(this);
                if (select) {
                    schedule(select);
                }
            }
        });
    }

    patchSetter(HTMLSelectElement.prototype, "value", function (select) {
        return select;
    });
    patchSetter(HTMLSelectElement.prototype, "selectedIndex", function (select) {
        return select;
    });
    patchSetter(HTMLOptionElement.prototype, "selected", owningSelect);

    function triggerClasses(select) {
        var classes = select.className.replace(/\brf-select__native\b/g, "").trim();
        if (!/\bform-(select|control)\b/.test(classes)) {
            classes += " form-select";
        }
        return "rf-select__trigger " + classes.trim();
    }

    function selectedOption(select) {
        return select.selectedIndex >= 0 ? select.options[select.selectedIndex] : null;
    }

    function sync(instance) {
        var select = instance.select;
        var option = selectedOption(select);
        var text = option ? option.textContent.replace(/\s+/g, " ").trim() : "";
        instance.label.textContent = text || "\u00a0";
        instance.trigger.className = triggerClasses(select);
        instance.trigger.classList.toggle("is-placeholder", Boolean(option) && option.value === "");
        instance.trigger.classList.toggle("is-open", current === instance);
        instance.trigger.disabled = select.disabled;
        instance.wrapper.hidden = select.hidden || select.style.display === "none";
        if (current === instance) {
            renderMenu(instance);
        }
    }

    function buildMenuShell() {
        menu = element("div", "rf-select-menu");
        menu.hidden = true;
        menu.setAttribute("role", "listbox");
        document.body.appendChild(menu);

        menu.addEventListener("mousedown", function (event) {
            event.preventDefault();
        });
        menu.addEventListener("click", function (event) {
            var item = event.target.closest(".rf-select-menu__item");
            if (item && !item.classList.contains("is-disabled")) {
                choose(Number(item.dataset.index));
            }
        });
        document.addEventListener("mousedown", function (event) {
            if (current && !menu.contains(event.target) && !current.wrapper.contains(event.target)) {
                close(false);
            }
        });
        document.addEventListener(
            "scroll",
            function (event) {
                if (current && !menu.contains(event.target) && Date.now() - openedAt > 250) {
                    close(false);
                }
            },
            true
        );
        window.addEventListener("resize", function () {
            if (current) {
                close(false);
            }
        });
    }

    function renderMenu(instance) {
        var select = instance.select;
        menu.textContent = "";
        var rendered = 0;

        function addOption(option) {
            var item = element("div", "rf-select-menu__item", option.textContent.replace(/\s+/g, " ").trim() || "\u00a0");
            item.id = instance.id + "-option-" + option.index;
            item.dataset.index = String(option.index);
            item.setAttribute("role", "option");
            item.setAttribute("aria-selected", option.selected ? "true" : "false");
            if (option.selected) {
                item.classList.add("is-selected");
            }
            if (option.disabled) {
                item.classList.add("is-disabled");
                item.setAttribute("aria-disabled", "true");
            }
            if (option.value === "") {
                item.classList.add("is-placeholder");
            }
            if (instance.active === option.index) {
                item.classList.add("is-active");
            }
            menu.appendChild(item);
            rendered += 1;
        }

        Array.prototype.forEach.call(select.children, function (child) {
            if (child.tagName === "OPTGROUP") {
                menu.appendChild(element("div", "rf-select-menu__group", child.label));
                Array.prototype.forEach.call(child.children, function (option) {
                    if (option.tagName === "OPTION") {
                        addOption(option);
                    }
                });
            } else if (child.tagName === "OPTION") {
                addOption(child);
            }
        });

        if (!rendered) {
            menu.appendChild(element("div", "rf-select-menu__empty", "No options available"));
        }
    }

    function position(instance) {
        var rect = instance.trigger.getBoundingClientRect();
        menu.style.minWidth = rect.width + "px";
        menu.style.maxHeight = "280px";
        menu.style.visibility = "hidden";
        menu.hidden = false;
        var height = menu.offsetHeight;
        var width = menu.offsetWidth;
        var spaceBelow = window.innerHeight - rect.bottom - 12;
        var spaceAbove = rect.top - 12;
        var above = height > spaceBelow && spaceAbove > spaceBelow;
        var available = Math.max(120, above ? spaceAbove : spaceBelow);
        menu.style.maxHeight = Math.min(280, available) + "px";
        height = menu.offsetHeight;
        var top = above ? rect.top - height - 6 : rect.bottom + 6;
        var left = Math.min(Math.max(8, rect.left), Math.max(8, window.innerWidth - width - 8));
        menu.style.left = left + window.pageXOffset + "px";
        menu.style.top = top + window.pageYOffset + "px";
        menu.style.visibility = "visible";
    }

    function scrollToActive() {
        var item = menu.querySelector(".is-active") || menu.querySelector(".is-selected");
        if (!item) {
            return;
        }
        var top = item.offsetTop;
        var bottom = top + item.offsetHeight;
        if (top < menu.scrollTop) {
            menu.scrollTop = top - 6;
        } else if (bottom > menu.scrollTop + menu.clientHeight) {
            menu.scrollTop = bottom - menu.clientHeight + 6;
        }
    }

    function open(instance) {
        if (!menu) {
            buildMenuShell();
        }
        if (instance.select.disabled || current === instance) {
            return;
        }
        if (current) {
            close(false);
        }
        current = instance;
        openedAt = Date.now();
        instance.active = instance.select.selectedIndex;
        instance.trigger.setAttribute("aria-expanded", "true");
        instance.trigger.setAttribute("aria-controls", instance.id + "-menu");
        menu.id = instance.id + "-menu";
        renderMenu(instance);
        position(instance);
        instance.trigger.classList.add("is-open");
        scrollToActive();
    }

    function close(returnFocus) {
        if (!current) {
            return;
        }
        var instance = current;
        current = null;
        menu.hidden = true;
        instance.trigger.setAttribute("aria-expanded", "false");
        instance.trigger.classList.remove("is-open");
        if (returnFocus) {
            instance.trigger.focus();
        }
    }

    function choose(index) {
        var instance = current;
        if (!instance) {
            return;
        }
        var select = instance.select;
        var changed = select.selectedIndex !== index;
        select.selectedIndex = index;
        close(true);
        sync(instance);
        if (changed) {
            fire(select, "input");
            fire(select, "change");
        }
    }

    function moveActive(instance, step) {
        var options = instance.select.options;
        var index = instance.active;
        for (var tries = 0; tries < options.length; tries += 1) {
            index += step;
            if (index < 0 || index >= options.length) {
                return;
            }
            if (!options[index].disabled) {
                instance.active = index;
                renderMenu(instance);
                scrollToActive();
                return;
            }
        }
    }

    function jumpActive(instance, last) {
        var options = instance.select.options;
        var indexes = [];
        for (var index = 0; index < options.length; index += 1) {
            if (!options[index].disabled) {
                indexes.push(index);
            }
        }
        if (!indexes.length) {
            return;
        }
        instance.active = last ? indexes[indexes.length - 1] : indexes[0];
        renderMenu(instance);
        scrollToActive();
    }

    function typeahead(instance, character) {
        window.clearTimeout(typed.timer);
        typed.text += character.toLowerCase();
        typed.timer = window.setTimeout(function () {
            typed.text = "";
        }, 700);
        var options = instance.select.options;
        var start = instance.active >= 0 ? instance.active : 0;
        for (var offset = 0; offset < options.length; offset += 1) {
            var index = (start + offset + (typed.text.length === 1 ? 1 : 0)) % options.length;
            var option = options[index];
            if (!option.disabled && option.textContent.trim().toLowerCase().indexOf(typed.text) === 0) {
                instance.active = index;
                if (current === instance) {
                    renderMenu(instance);
                    scrollToActive();
                } else {
                    instance.select.selectedIndex = index;
                    sync(instance);
                    fire(instance.select, "input");
                    fire(instance.select, "change");
                }
                return;
            }
        }
    }

    function onKeydown(instance, event) {
        var key = event.key;
        if (!current) {
            if (key === "Enter" || key === " " || key === "ArrowDown" || key === "ArrowUp") {
                event.preventDefault();
                open(instance);
            } else if (key.length === 1 && !event.ctrlKey && !event.metaKey && !event.altKey) {
                typeahead(instance, key);
            }
            return;
        }
        if (key === "Escape") {
            event.preventDefault();
            close(true);
        } else if (key === "Tab") {
            close(false);
        } else if (key === "ArrowDown") {
            event.preventDefault();
            moveActive(instance, 1);
        } else if (key === "ArrowUp") {
            event.preventDefault();
            moveActive(instance, -1);
        } else if (key === "Home") {
            event.preventDefault();
            jumpActive(instance, false);
        } else if (key === "End") {
            event.preventDefault();
            jumpActive(instance, true);
        } else if (key === "Enter" || key === " ") {
            event.preventDefault();
            if (instance.active >= 0 && !instance.select.options[instance.active].disabled) {
                choose(instance.active);
            }
        } else if (key.length === 1 && !event.ctrlKey && !event.metaKey && !event.altKey) {
            typeahead(instance, key);
        }
    }

    function eligible(select) {
        return (
            select.tagName === "SELECT" &&
            !instances.has(select) &&
            !select.multiple &&
            !(select.size > 1) &&
            !select.hasAttribute("data-native") &&
            !select.closest(".rf-select")
        );
    }

    function enhance(select) {
        if (!eligible(select)) {
            return;
        }
        counter += 1;
        var inline = window.getComputedStyle(select).display === "inline-block";
        var wrapper = element("div", "rf-select" + (inline ? " rf-select--inline" : ""));
        var trigger = element("button", "rf-select__trigger");
        trigger.type = "button";
        trigger.setAttribute("role", "combobox");
        trigger.setAttribute("aria-haspopup", "listbox");
        trigger.setAttribute("aria-expanded", "false");
        var label = element("span", "rf-select__label");
        trigger.appendChild(label);

        select.parentNode.insertBefore(wrapper, select);
        wrapper.appendChild(trigger);
        wrapper.appendChild(select);
        select.classList.add("rf-select__native");
        select.setAttribute("tabindex", "-1");
        select.setAttribute("aria-hidden", "true");

        var instance = {
            id: "rf-select-" + counter,
            select: select,
            wrapper: wrapper,
            trigger: trigger,
            label: label,
            active: -1,
            pending: false
        };
        instances.set(select, instance);

        if (select.id) {
            var labelNode = document.querySelector('label[for="' + select.id.replace(/"/g, '\\"') + '"]');
            if (labelNode) {
                if (!labelNode.id) {
                    labelNode.id = instance.id + "-label";
                }
                trigger.setAttribute("aria-labelledby", labelNode.id);
            }
        }

        trigger.addEventListener("click", function () {
            if (current === instance) {
                close(false);
            } else {
                open(instance);
            }
        });
        trigger.addEventListener("keydown", function (event) {
            onKeydown(instance, event);
        });
        select.addEventListener("change", function () {
            sync(instance);
        });

        new MutationObserver(function () {
            schedule(select);
        }).observe(select, {
            childList: true,
            subtree: true,
            characterData: true,
            attributes: true,
            attributeFilter: SYNCED_ATTRIBUTES
        });

        sync(instance);
    }

    function enhanceWithin(root) {
        if (root.nodeType !== 1) {
            return;
        }
        if (root.tagName === "SELECT") {
            enhance(root);
        }
        Array.prototype.forEach.call(root.querySelectorAll("select"), enhance);
    }

    function focusFromLabel(event) {
        var label = event.target.closest("label[for]");
        if (!label) {
            return;
        }
        var target = document.getElementById(label.getAttribute("for"));
        var instance = target && instances.get(target);
        if (instance && !instance.select.disabled) {
            event.preventDefault();
            instance.trigger.focus();
        }
    }

    function init() {
        enhanceWithin(document.body);
        new MutationObserver(function (records) {
            records.forEach(function (record) {
                Array.prototype.forEach.call(record.addedNodes, enhanceWithin);
            });
        }).observe(document.body, { childList: true, subtree: true });
        document.addEventListener("click", focusFromLabel);
        document.addEventListener("reset", function (event) {
            window.setTimeout(function () {
                Array.prototype.forEach.call(event.target.querySelectorAll("select"), schedule);
            }, 0);
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }

    window.RaddiSelect = { enhance: enhance };
})();
